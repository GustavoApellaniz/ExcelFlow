from harmonize_xl.schema import match_header, match_row, normalize_header


def test_normalize_header_removes_accents_and_punctuation():
    assert normalize_header("Quantité (kg)") == "quantite kg"
    assert normalize_header("  Prix unitaire (€) ") == "prix unitaire"


def test_exact_match_in_three_languages():
    assert match_header("Date livraison").field == "delivery_date"
    assert match_header("Fornecedor").field == "supplier"
    assert match_header("Unit Price EUR").field == "unit_price_eur"
    assert match_header("Date livraison").method == "exact"


def test_fuzzy_match_accepts_typos():
    match = match_header("Quantitiy kg")
    assert match.field == "quantity_kg" and match.method == "fuzzy" and match.score >= 0.8


def test_unrelated_header_is_not_mapped():
    assert match_header("Notes") is None
    assert match_header("Coopérative Normandie - Relevé des livraisons") is None
    assert match_header("") is None


def test_two_columns_for_same_field_keep_best_score():
    mapping = match_row(["Date", "Delivry date", "Supplier"])
    fields = [m.field for m in mapping.values()]
    assert fields.count("delivery_date") == 1
    assert mapping[0].method == "exact"      # the exact 'Date' beats the typo
