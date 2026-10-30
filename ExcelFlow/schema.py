"""Canonical schema and header recognition (exact and fuzzy matching)."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher, get_close_matches

FIELDS = (
    "delivery_date",
    "supplier",
    "product_code",
    "product_name",
    "quantity_kg",
    "unit_price_eur",
)

REQUIRED_FIELDS = (
    "delivery_date",
    "supplier",
    "product_code",
    "quantity_kg",
    "unit_price_eur",
)

# Known header spellings (already normalised: lower case, no accents/punctuation).
ALIASES: dict[str, list[str]] = {
    "delivery_date": ["date", "delivery date", "date livraison", "date de livraison",
                      "data entrega", "data de entrega", "data", "fecha"],
    "supplier": ["supplier", "vendor", "fournisseur", "fornecedor", "proveedor"],
    "product_code": ["product code", "code produit", "codigo produto", "cod produto",
                     "sku", "code"],
    "product_name": ["product", "product name", "produit", "designation", "produto",
                     "nome produto"],
    "quantity_kg": ["quantity kg", "quantity", "qty kg", "qty", "quantite kg", "quantite",
                    "qte kg", "quantidade kg", "quantidade", "weight kg"],
    "unit_price_eur": ["unit price eur", "unit price", "price eur", "price", "prix unitaire",
                       "prix", "preco unitario", "preco"],
}


def normalize_header(text: object) -> str:
    """'Quantité (kg)' -> 'quantite kg'."""
    decomposed = unicodedata.normalize("NFKD", str(text))
    no_accents = "".join(c for c in decomposed if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", no_accents.lower()).strip()


ALIAS_LOOKUP: dict[str, str] = {
    alias: field for field, aliases in ALIASES.items() for alias in aliases
}


@dataclass(frozen=True)
class HeaderMatch:
    field: str
    score: float
    method: str       # "exact" or "fuzzy"
    original: str


def match_header(text: object, cutoff: float = 0.8) -> HeaderMatch | None:
    """Map one header cell to a canonical field, or None if it is not recognised."""
    norm = normalize_header(text)
    if not norm:
        return None
    if norm in ALIAS_LOOKUP:
        return HeaderMatch(ALIAS_LOOKUP[norm], 1.0, "exact", str(text))
    close = get_close_matches(norm, list(ALIAS_LOOKUP), n=1, cutoff=cutoff)
    if close:
        score = round(SequenceMatcher(None, norm, close[0]).ratio(), 2)
        return HeaderMatch(ALIAS_LOOKUP[close[0]], score, "fuzzy", str(text))
    return None


def match_row(cells: list, cutoff: float = 0.8) -> dict[int, HeaderMatch]:
    """Match every text cell of a row; if two columns claim the same field, the best score wins."""
    best: dict[str, tuple[int, HeaderMatch]] = {}
    for index, cell in enumerate(cells):
        if not isinstance(cell, str):
            continue
        match = match_header(cell, cutoff)
        if match and (match.field not in best or match.score > best[match.field][1].score):
            best[match.field] = (index, match)
    return {index: match for index, match in best.values()}
