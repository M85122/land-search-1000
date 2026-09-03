import json
from urllib.request import Request

from landsearch.adapters.arcgis import ArcgisAdapter
from landsearch.atlas import resolve_county
from landsearch.lookup import features_to_parcels, group_owners, lookup


KANE_FEATURES = {
    "features": [
        {
            "attributes": {
                "PIN": "1",
                "TaxName": "SMITH, JOHN A",
                "SiteAddress": "1 MAIN ST",
                "SiteCity": "ELGIN",
                "SiteState": "IL",
                "SiteZip": "60120",
            }
        },
        {
            "attributes": {
                "PIN": "2",
                "TaxName": "SMITH, MARY L TRUST",
                "SiteAddress": "2 OAK AVE",
                "SiteCity": "AURORA",
                "SiteState": "IL",
                "SiteZip": "60505",
            }
        },
        {
            "attributes": {
                "PIN": "3",
                "TaxName": "SMITH, JOHN A",
                "SiteAddress": "3 MAIN ST",
                "SiteCity": "ELGIN",
                "SiteState": "IL",
                "SiteZip": "60120",
            }
        },
    ]
}


class _FakeResp:
    def __init__(self, payload: dict):
        self._raw = json.dumps(payload).encode("utf-8")

    def read(self):
        return self._raw

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_collision_lists_multiple_owners():
    county = resolve_county("IL", "Kane")
    parcels = features_to_parcels(county, KANE_FEATURES["features"], "Smith")
    groups, collision = group_owners(parcels)
    assert collision is True
    owners = {g["owner"] for g in groups}
    assert any("JOHN" in o for o in owners)
    assert any("MARY" in o for o in owners)
    assert len(groups) == 2


def test_lookup_uses_mocked_json(monkeypatch):
    seen = {}

    def fake_open(req: Request, timeout=0):
        seen["url"] = req.full_url
        return _FakeResp(KANE_FEATURES)

    county = resolve_county("IL", "Kane")
    adapter = ArcgisAdapter(opener=fake_open, min_interval=0)
    result = lookup("Smith", county, adapter=adapter, record_cap=25)
    assert "TaxName" in seen["url"]
    assert "f=json" in seen["url"]
    assert result.collision is True
    assert len(result.parcels) == 3
    assert result.citation["layer_url"] == county.layer_url
    assert result.citation["fips"] == "17089"
