from __future__ import annotations

import json
import os
from pathlib import Path

from landsearch.models import County


class AtlasError(Exception):
    pass


class CoverageError(AtlasError):
    """No atlas entry, or the county has no searchable owner field."""


def atlas_dirs() -> list[Path]:
    dirs: list[Path] = []
    env = os.environ.get("LANDSEARCH_ATLAS")
    if env:
        dirs.append(Path(env))
    here = Path(__file__).resolve()
    dirs.append(here.parent.parent.parent / "atlas")
    dirs.append(here.parent / "atlas")
    dirs.append(Path.cwd() / "atlas")
    out: list[Path] = []
    seen: set[str] = set()
    for d in dirs:
        key = str(d.resolve()) if d.exists() else str(d)
        if key in seen:
            continue
        seen.add(key)
        out.append(d)
    return out


def load_counties() -> list[County]:
    files: list[Path] = []
    for d in atlas_dirs():
        if d.is_dir():
            files.extend(sorted(d.glob("*.json")))
    if not files:
        raise AtlasError(
            "No atlas JSON found. Expected atlas/*.json next to the project "
            "or LANDSEARCH_ATLAS pointing at that directory."
        )
    counties: list[County] = []
    seen_fips: set[str] = set()
    for path in files:
        with path.open(encoding="utf-8") as fh:
            data = json.load(fh)
        fips = str(data["fips"])
        if fips in seen_fips:
            continue
        seen_fips.add(fips)
        counties.append(
            County(
                fips=fips,
                state=str(data["state"]).upper(),
                county=str(data["county"]),
                adapter=str(data.get("adapter", "arcgis")),
                layer_url=str(data["layer_url"]),
                owner_searchable=bool(data.get("owner_searchable", False)),
                fields=dict(data.get("fields") or {}),
                license=str(data.get("license") or ""),
                attribution=str(data.get("attribution") or ""),
                last_verified=str(data.get("last_verified") or ""),
                path=str(path),
            )
        )
    return counties


def _norm_county_name(name: str) -> str:
    n = " ".join(name.strip().lower().replace(".", "").split())
    if n.endswith(" county"):
        n = n[: -len(" county")]
    return n


def resolve_county(state: str, county: str | None) -> County:
    if not state or not str(state).strip():
        raise CoverageError("State is required (two-letter USPS code, e.g. IL).")
    st = state.strip().upper()
    all_counties = load_counties()
    in_state = [c for c in all_counties if c.state == st]
    if not in_state:
        covered = ", ".join(sorted({c.state for c in all_counties})) or "(none)"
        raise CoverageError(
            f"No coverage for state {st}. Atlas states: {covered}."
        )
    if not county or not str(county).strip():
        if len(in_state) == 1:
            chosen = in_state[0]
        else:
            names = ", ".join(f"{c.county} ({c.fips})" for c in in_state)
            raise CoverageError(
                f"County is required for {st}. Covered counties: {names}."
            )
    else:
        want = _norm_county_name(county)
        matches = [c for c in in_state if _norm_county_name(c.county) == want]
        if not matches:
            names = ", ".join(f"{c.county} ({c.fips})" for c in in_state)
            raise CoverageError(
                f"No coverage for {county} County, {st}. "
                f"Covered in {st}: {names}."
            )
        chosen = matches[0]
    if not chosen.owner_searchable or not chosen.owner_field:
        raise CoverageError(
            f"{chosen.label()} has no searchable owner-of-record field "
            "in this atlas. Refusing lookup."
        )
    if chosen.adapter != "arcgis":
        raise CoverageError(
            f"{chosen.label()} adapter {chosen.adapter!r} is not supported."
        )
    return chosen
