import os

import pytest

from landsearch.adapters.arcgis import ArcgisAdapter
from landsearch.atlas import resolve_county
from landsearch.lookup import lookup

pytestmark = pytest.mark.skipif(
    os.environ.get("LANDSEARCH_LIVE") != "1",
    reason="Live ArcGIS tests off (set LANDSEARCH_LIVE=1)",
)


def test_live_kane_smith():
    county = resolve_county("IL", "Kane")
    result = lookup("Smith", county, adapter=ArcgisAdapter(min_interval=0), record_cap=3)
    assert result.parcels
    assert result.parcels[0].owner
    assert "SMITH" in result.parcels[0].owner.upper()


def test_live_wake_county():
    county = resolve_county("NC", "Wake")
    result = lookup(
        "Wake County", county, adapter=ArcgisAdapter(min_interval=0), record_cap=3
    )
    assert result.parcels
    assert result.parcels[0].owner
