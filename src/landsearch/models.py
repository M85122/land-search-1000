from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class County:
    fips: str
    state: str
    county: str
    adapter: str
    layer_url: str
    owner_searchable: bool
    fields: dict[str, str]
    license: str
    attribution: str
    last_verified: str
    path: str = ""

    @property
    def owner_field(self) -> str | None:
        return self.fields.get("owner")

    def label(self) -> str:
        return f"{self.county} County, {self.state} (FIPS {self.fips})"


@dataclass
class Parcel:
    owner: str
    pin: str | None
    site_address: str | None
    site_city: str | None
    site_state: str | None
    site_zip: str | None
    mailing_address: str | None
    mailing_city: str | None
    mailing_state: str | None
    mailing_zip: str | None
    raw: dict[str, Any] = field(default_factory=dict)
    score: float = 0.0
    owner_key: str = ""


@dataclass
class LookupResult:
    query: str
    county: County
    parcels: list[Parcel]
    owner_groups: list[dict[str, Any]]
    collision: bool
    citation: dict[str, str]
    source_url: str
