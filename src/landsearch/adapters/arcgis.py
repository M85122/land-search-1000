from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable

DEFAULT_RECORD_CAP = 25
DEFAULT_TIMEOUT = 30
DEFAULT_MIN_INTERVAL = 1.0


def escape_like_value(value: str) -> str:
    """Escape single quotes for an ArcGIS SQL WHERE literal."""
    return value.replace("'", "''")


def owner_where(owner_field: str, name: str) -> str:
    if not owner_field or not owner_field.replace("_", "").isalnum():
        raise ValueError(f"Refusing unsafe owner field name: {owner_field!r}")
    needle = escape_like_value(name.strip())
    return f"UPPER({owner_field}) LIKE UPPER('%{needle}%')"


def build_query_url(
    layer_url: str,
    where: str,
    out_fields: list[str] | str,
    result_record_count: int = DEFAULT_RECORD_CAP,
    return_geometry: bool = False,
) -> str:
    base = layer_url.rstrip("/")
    if not base.endswith("/query"):
        base = base + "/query"
    if isinstance(out_fields, str):
        fields = out_fields
    else:
        fields = ",".join(out_fields)
    cap = max(1, min(int(result_record_count), 100))
    params = {
        "where": where,
        "outFields": fields or "*",
        "f": "json",
        "resultRecordCount": str(cap),
        "returnGeometry": "true" if return_geometry else "false",
    }
    return base + "?" + urllib.parse.urlencode(params)


class ArcgisError(Exception):
    pass


class ArcgisAdapter:
    def __init__(
        self,
        timeout: float = DEFAULT_TIMEOUT,
        min_interval: float = DEFAULT_MIN_INTERVAL,
        opener: Callable[..., Any] | None = None,
    ) -> None:
        self.timeout = timeout
        self.min_interval = min_interval
        self._last_request = 0.0
        self._opener = opener or urllib.request.urlopen

    def _rate_limit(self) -> None:
        if self.min_interval <= 0:
            return
        now = time.monotonic()
        wait = self.min_interval - (now - self._last_request)
        if wait > 0:
            time.sleep(wait)
        self._last_request = time.monotonic()

    def query(
        self,
        layer_url: str,
        where: str,
        out_fields: list[str],
        result_record_count: int = DEFAULT_RECORD_CAP,
    ) -> dict[str, Any]:
        url = build_query_url(
            layer_url,
            where,
            out_fields,
            result_record_count=result_record_count,
        )
        self._rate_limit()
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "landsearch/1.0 (Land Search 1000; public GIS lookup)"},
            method="GET",
        )
        try:
            with self._opener(req, timeout=self.timeout) as resp:
                raw = resp.read()
        except urllib.error.URLError as exc:
            raise ArcgisError(f"ArcGIS request failed: {exc}") from exc
        try:
            data = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ArcgisError("ArcGIS response was not JSON") from exc
        if isinstance(data, dict) and data.get("error"):
            raise ArcgisError(f"ArcGIS error: {data['error']}")
        return data
