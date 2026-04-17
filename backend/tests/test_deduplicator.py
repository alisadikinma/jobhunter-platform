from app.utils.deduplicator import content_hash


def test_hash_is_stable_across_whitespace_and_case():
    a = content_hash("Senior Engineer", "Acme", "Build great things.")
    b = content_hash("  SENIOR   engineer  ", "acme", "Build great things.")
    assert a == b


def test_hash_differs_when_company_differs():
    a = content_hash("Engineer", "Acme", "desc")
    b = content_hash("Engineer", "Zeta", "desc")
    assert a != b


def test_hash_only_considers_first_200_chars_of_description():
    base = "x" * 200
    a = content_hash("T", "C", base)
    b = content_hash("T", "C", base + "different tail content")
    assert a == b


def test_hash_handles_missing_description():
    h = content_hash("Title", "Company", None)
    assert len(h) == 64  # SHA256 hex
