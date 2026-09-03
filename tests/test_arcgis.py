from urllib.parse import parse_qs, urlparse

from landsearch.adapters.arcgis import build_query_url, owner_where


def test_owner_where_like_upper():
    assert owner_where("TaxName", "Smith") == "UPPER(TaxName) LIKE UPPER('%Smith%')"


def test_owner_where_escapes_quote():
    assert "O''BRIEN" in owner_where("OWNER", "O'BRIEN")


def test_build_query_url_params():
    url = build_query_url(
        "https://maps.example.gov/arcgis/rest/services/Parcels/MapServer/0",
        "UPPER(OWNER) LIKE UPPER('%DOE%')",
        ["OWNER", "PIN_NUM"],
        result_record_count=25,
    )
    parsed = urlparse(url)
    assert parsed.path.endswith("/query")
    q = parse_qs(parsed.query)
    assert q["f"] == ["json"]
    assert q["outFields"] == ["OWNER,PIN_NUM"]
    assert q["resultRecordCount"] == ["25"]
    assert q["returnGeometry"] == ["false"]
    assert q["where"] == ["UPPER(OWNER) LIKE UPPER('%DOE%')"]


def test_record_cap_clamped():
    url = build_query_url(
        "https://example.gov/MapServer/0",
        "1=1",
        "OWNER",
        result_record_count=9999,
    )
    q = parse_qs(urlparse(url).query)
    assert q["resultRecordCount"] == ["100"]
