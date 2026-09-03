from __future__ import annotations

from collections import defaultdict
from typing import Any

from landsearch.adapters.arcgis import DEFAULT_RECORD_CAP, ArcgisAdapter, owner_where
from landsearch.match.names import owner_group_key, score_owner
from landsearch.models import County, LookupResult, Parcel

_FIELD_SLOTS = (
    "owner",
    "pin",
    "site_address",
    "site_city",
    "site_state",
    "site_zip",
    "mailing_address",
    "mailing_city",
    "mailing_state",
    "mailing_zip",
)


def _attr(attrs: dict[str, Any], key: str | None) -> str | None:
    if not key:
        return None
    val = attrs.get(key)
    if val is None:
        return None
    text = str(val).strip()
    return text or None


def features_to_parcels(county: County, features: list[dict[str, Any]], query: str) -> list[Parcel]:
    fmap = county.fields
    parcels: list[Parcel] = []
    for feat in features:
        attrs = feat.get("attributes") or feat
        owner = _attr(attrs, fmap.get("owner")) or ""
        parcel = Parcel(
            owner=owner,
            pin=_attr(attrs, fmap.get("pin")),
            site_address=_attr(attrs, fmap.get("site_address")),
            site_city=_attr(attrs, fmap.get("site_city")),
            site_state=_attr(attrs, fmap.get("site_state")),
            site_zip=_attr(attrs, fmap.get("site_zip")),
            mailing_address=_attr(attrs, fmap.get("mailing_address")),
            mailing_city=_attr(attrs, fmap.get("mailing_city")),
            mailing_state=_attr(attrs, fmap.get("mailing_state")),
            mailing_zip=_attr(attrs, fmap.get("mailing_zip")),
            raw=dict(attrs),
            score=score_owner(query, owner),
            owner_key=owner_group_key(owner) or owner.strip().upper(),
        )
        parcels.append(parcel)
    parcels.sort(key=lambda p: (-p.score, p.owner, p.pin or ""))
    return parcels


def group_owners(parcels: list[Parcel]) -> tuple[list[dict[str, Any]], bool]:
    buckets: dict[str, list[Parcel]] = defaultdict(list)
    for p in parcels:
        buckets[p.owner_key or p.owner].append(p)
    groups: list[dict[str, Any]] = []
    for key, items in buckets.items():
        best = max(p.score for p in items)
        # Prefer the longest raw owner string as display.
        display = sorted({p.owner for p in items}, key=lambda s: (-len(s), s))[0]
        groups.append(
            {
                "owner_key": key,
                "owner": display,
                "score": best,
                "parcel_count": len(items),
                "pins": [p.pin for p in items if p.pin],
            }
        )
    groups.sort(key=lambda g: (-g["score"], g["owner"]))
    collision = len(groups) > 1
    return groups, collision


def lookup(
    query: str,
    county: County,
    *,
    adapter: ArcgisAdapter | None = None,
    record_cap: int = DEFAULT_RECORD_CAP,
) -> LookupResult:
    if not query or not query.strip():
        raise ValueError("A person or entity name is required.")
    q = query.strip()
    owner_field = county.owner_field
    assert owner_field  # coverage check already required this
    out_fields: list[str] = []
    for slot in _FIELD_SLOTS:
        name = county.fields.get(slot)
        if name and name not in out_fields:
            out_fields.append(name)
    where = owner_where(owner_field, q)
    client = adapter or ArcgisAdapter()
    payload = client.query(
        county.layer_url,
        where,
        out_fields,
        result_record_count=record_cap,
    )
    features = list(payload.get("features") or [])
    parcels = features_to_parcels(county, features, q)
    groups, collision = group_owners(parcels)
    source_url = county.layer_url.rstrip("/") + "/query"
    citation = {
        "county": county.county,
        "state": county.state,
        "fips": county.fips,
        "layer_url": county.layer_url,
        "attribution": county.attribution,
        "license": county.license,
        "last_verified": county.last_verified,
        "owner_field": owner_field,
        "where": where,
    }
    return LookupResult(
        query=q,
        county=county,
        parcels=parcels,
        owner_groups=groups,
        collision=collision,
        citation=citation,
        source_url=source_url,
    )
