# Land Search 1000

Look up **owner-of-record parcels** from **official public county ArcGIS REST layers**, given a person or entity name and a US place.

Phone-friendly: install, run one command, read the table.

```
pip install -e .
landsearch lookup "Smith" --state IL --county Kane
```

## What it is

- A small Python 3.11+ library and CLI (`landsearch`)
- Name + state + county → LIKE query on the county’s published owner field
- Results include parcel id, site address when the layer has it, a match score, and a **citation** (layer URL, county attribution, last verified date)

## What it is not

- Not HTML scraping
- Not Zillow, Redfin, Google, or any login / CAPTCHA wall
- Not a people-search or skip-trace product (no enrichment, no SSN, no phone)
- Not bulk harvest or a statewide dump
- Not FCRA tenant/employee/credit screening
- Not legal advice, not a title search, not proof of current occupancy

San Diego was attempted and **not** verified from the network used for this release. It is **not** in the atlas.

## Install / run

Python 3.11+. No runtime dependencies (stdlib `urllib`).

```
git clone https://github.com/M85122/land-search-1000
cd land-search-1000
python -m pip install -e ".[dev]"
landsearch coverage
landsearch lookup "Jane Doe" --state IL --county Kane
landsearch lookup "Wake County" --state NC --county Wake --json
```

`--state` is required. `--county` is strongly preferred (required when a state has more than one atlas row). Exit code **2** if there is no coverage or the county has no owner field.

Optional live tests (off by default): `LANDSEARCH_LIVE=1 python -m pytest`

## Coverage (honest, verified 2026-09-02)

| County | State | FIPS | Owner field | Layer |
| --- | --- | --- | --- | --- |
| Kane | IL | 17089 | TaxName | https://gistech.countyofkane.org/arcgis/rest/services/KanePINList/MapServer/0 |
| Wake | NC | 37183 | OWNER | https://maps.wakegov.com/arcgis/rest/services/Property/Parcels/MapServer/0 |

Only these two. Unverified hunches are not shipped.

Sample checks used for this release:

- Kane: `UPPER(TaxName) LIKE UPPER('%SMITH%')` returned features
- Wake: `UPPER(OWNER) LIKE UPPER('%WAKE COUNTY%')` returned features

## How to add a county

1. Find the county’s **public** ArcGIS REST parcel MapServer layer (no login).
2. Confirm an owner-of-record field with a real `/query` (`f=json`, small `resultRecordCount`).
3. Drop `atlas/<slug>.json`:

```
{
  "fips": "17089",
  "state": "IL",
  "county": "Kane",
  "adapter": "arcgis",
  "layer_url": "https://example.county.gov/arcgis/rest/services/Parcels/MapServer/0",
  "owner_searchable": true,
  "fields": { "owner": "TaxName", "pin": "PIN", "site_address": "SiteAddress" },
  "license": "Public GIS / assessor parcel data.",
  "attribution": "County GIS / Assessor. Layer URL.",
  "last_verified": "2026-09-02"
}
```

4. Set `owner_searchable` to `false` (or omit owner) if the layer has no owner field — the CLI will refuse lookup.
5. Add a line to `ATTRIBUTION.md`. Do not copy third-party atlas dumps.

## Matching

Names are normalized (case, punctuation, `LAST, FIRST` vs first last, `LLC` / `TRUST` / `TR` / `ET AL`). Each owner string is scored. **If several distinct owners collide, they are all listed with scores** — the tool never silently picks one.

## Ethics

- Public **owner-of-record** only, as published by the county
- Always cite the layer
- Homonyms are common (`SMITH`); treat collisions as collisions
- Rate-limited (about 1 request/second) and capped (default 25 records)
- Do not use this for FCRA-covered screening or stalking
- Do not bulk-harvest or scrape HTML alternatives when a layer is down

## Related work

[UrbanKit/mcp-atlas](https://github.com/UrbanKit-org/mcp-atlas) maps public geospatial services. This repo does **not** copy their atlas dump; counties here are added only after a live query from this project.

## License

MIT for the code. County GIS data remains the counties’. See `LICENSE` and `ATTRIBUTION.md`.
