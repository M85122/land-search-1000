from __future__ import annotations

import re
import unicodedata

# Dropped after punctuation split; order-independent.
_LEGAL = {
    "LLC",
    "LLP",
    "LP",
    "INC",
    "INCORPORATED",
    "CORP",
    "CORPORATION",
    "CO",
    "LTD",
    "LIMITED",
    "PLC",
    "PC",
    "PA",
    "TRUST",
    "TRUSTS",
    "TRUSTEE",
    "TRUSTEES",
    "TR",
    "ET",
    "AL",
    "ETAL",
    "A",
    "AKA",
    "FKA",
    "NKA",
    "C/O",
    "CO",
    "THE",
    "AND",
    "&",
    "OF",
    "FOR",
}

_PUNCT = re.compile(r"[^\w\s,]+", re.UNICODE)
_WS = re.compile(r"\s+")


def _fold(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text.upper()


def normalize_name(name: str) -> str:
    """Uppercase, strip punctuation (keep comma for LAST, FIRST), collapse space."""
    if not name:
        return ""
    folded = _fold(name).replace("&", " AND ")
    folded = _PUNCT.sub(" ", folded)
    folded = _WS.sub(" ", folded).strip(" ,")
    return folded


def _tokens_no_legal(parts: list[str]) -> list[str]:
    out: list[str] = []
    for p in parts:
        if not p or p in _LEGAL:
            continue
        out.append(p)
    return out


def canonical_tokens(name: str) -> list[str]:
    """Tokens used for matching: legal suffixes stripped; LAST, FIRST reordered."""
    norm = normalize_name(name)
    if not norm:
        return []
    if "," in norm:
        last, _, rest = norm.partition(",")
        last_tokens = _tokens_no_legal(last.split())
        given = _tokens_no_legal(rest.split())
        return last_tokens + given
    return _tokens_no_legal(norm.split())


def owner_group_key(name: str) -> str:
    # Order-insensitive so "DOE, JANE" and "Jane Doe" share a group.
    return " ".join(sorted(canonical_tokens(name)))


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def score_owner(query: str, owner: str) -> float:
    """
    0..1 similarity of a person/entity query to an owner-of-record string.
    LAST, FIRST vs first last and LLC/TRUST/TR/ET AL are normalized away.
    """
    q = canonical_tokens(query)
    o = canonical_tokens(owner)
    if not q or not o:
        return 0.0
    if q == o:
        return 1.0
    qs, os_ = set(q), set(o)
    if qs == os_:
        return 1.0
    if len(q) == 1:
        token = q[0]
        if o[0] == token:
            return 1.0 if len(o) == 1 else 0.5
        if token in os_:
            return 0.35
        return 0.0
    # All query tokens appear in owner (query "JANE DOE" in "DOE JANE M").
    if qs <= os_:
        extra = len(os_ - qs)
        return round(0.92 - min(extra, 4) * 0.03, 4)
    # Owner tokens all appear in query (rare).
    if os_ <= qs:
        return 0.85
    jac = _jaccard(qs, os_)
    # Shared last-name-ish token (first canonical token after comma-reorder).
    last_hit = q[0] == o[0]
    if last_hit and jac >= 0.3:
        return round(0.55 + 0.4 * jac, 4)
    if last_hit:
        return 0.4
    if jac >= 0.5:
        return round(0.35 + 0.4 * jac, 4)
    return round(jac * 0.5, 4)
