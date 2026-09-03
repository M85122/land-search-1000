from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from landsearch import __version__
from landsearch.adapters.arcgis import DEFAULT_RECORD_CAP, ArcgisError
from landsearch.atlas import AtlasError, CoverageError, load_counties, resolve_county
from landsearch.lookup import lookup
from landsearch.models import LookupResult


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="landsearch",
        description=(
            "Land Search 1000: query official public county ArcGIS parcel layers "
            "for owner-of-record matches. Not a people-search product."
        ),
    )
    p.add_argument("--version", action="version", version=f"landsearch {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    look = sub.add_parser("lookup", help="Look up parcels by owner name in one county")
    look.add_argument("name", help='Person or entity name, e.g. "Jane Doe"')
    look.add_argument("--state", required=True, help="Two-letter state (required)")
    look.add_argument(
        "--county",
        help="County name (strongly preferred; required when a state has several atlas rows)",
    )
    look.add_argument("--json", action="store_true", dest="as_json", help="JSON output")
    look.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_RECORD_CAP,
        help=f"Max ArcGIS records (default {DEFAULT_RECORD_CAP}, max 100)",
    )

    cov = sub.add_parser("coverage", help="List verified atlas counties")
    cov.add_argument("--json", action="store_true", dest="as_json")
    return p


def _result_dict(result: LookupResult) -> dict[str, Any]:
    return {
        "query": result.query,
        "collision": result.collision,
        "warning": (
            "Multiple distinct owners matched. None is selected silently."
            if result.collision
            else None
        ),
        "county": {
            "name": result.county.county,
            "state": result.county.state,
            "fips": result.county.fips,
        },
        "citation": result.citation,
        "owner_groups": result.owner_groups,
        "parcels": [
            {
                "owner": p.owner,
                "score": p.score,
                "pin": p.pin,
                "site_address": p.site_address,
                "site_city": p.site_city,
                "site_state": p.site_state,
                "site_zip": p.site_zip,
                "mailing_address": p.mailing_address,
                "mailing_city": p.mailing_city,
                "mailing_state": p.mailing_state,
                "mailing_zip": p.mailing_zip,
            }
            for p in result.parcels
        ],
    }


def _print_table(result: LookupResult) -> None:
    c = result.county
    print(f"Land Search 1000 — {c.label()}")
    print(f"Query: {result.query}")
    print(f"Source: {c.layer_url}")
    print(f"Attribution: {c.attribution}")
    print(f"Verified: {c.last_verified}")
    if result.collision:
        print()
        print(
            "WARNING: several distinct owners matched this name. "
            "Listing all scored groups — no single match is assumed."
        )
        print("Owner groups:")
        for g in result.owner_groups:
            print(
                f"  {g['score']:.2f}  {g['owner']}  "
                f"({g['parcel_count']} parcel(s))"
            )
    print()
    if not result.parcels:
        print("No owner-of-record parcels returned (cap or no LIKE hits).")
        return
    cols = ("score", "owner", "pin", "site")
    rows = []
    for p in result.parcels:
        site = " ".join(
            x for x in (p.site_address, p.site_city, p.site_state, p.site_zip) if x
        )
        rows.append((f"{p.score:.2f}", p.owner, p.pin or "", site))
    widths = [len(h) for h in cols]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))
    fmt = "  ".join(f"{{:{w}}}" for w in widths)
    print(fmt.format(*cols))
    print(fmt.format(*("-" * w for w in widths)))
    for row in rows:
        print(fmt.format(*row))
    print()
    print("Owner-of-record only. Not FCRA screening. Homonyms are common.")


def cmd_lookup(args: argparse.Namespace) -> int:
    try:
        county = resolve_county(args.state, args.county)
    except CoverageError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except AtlasError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    try:
        result = lookup(args.name, county, record_cap=args.limit)
    except (ArcgisError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if args.as_json:
        print(json.dumps(_result_dict(result), indent=2))
    else:
        _print_table(result)
    return 0


def cmd_coverage(args: argparse.Namespace) -> int:
    try:
        counties = load_counties()
    except AtlasError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    rows = [
        {
            "fips": c.fips,
            "state": c.state,
            "county": c.county,
            "owner_searchable": c.owner_searchable,
            "owner_field": c.owner_field,
            "layer_url": c.layer_url,
            "last_verified": c.last_verified,
            "attribution": c.attribution,
        }
        for c in counties
    ]
    if args.as_json:
        print(json.dumps(rows, indent=2))
        return 0
    print("Verified coverage (live-checked for this release):")
    for r in rows:
        flag = "owner-searchable" if r["owner_searchable"] else "NO OWNER FIELD"
        print(
            f"  {r['county']} County, {r['state']}  FIPS {r['fips']}  "
            f"{flag}  verified {r['last_verified']}"
        )
        print(f"    {r['layer_url']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.cmd == "lookup":
        return cmd_lookup(args)
    if args.cmd == "coverage":
        return cmd_coverage(args)
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
