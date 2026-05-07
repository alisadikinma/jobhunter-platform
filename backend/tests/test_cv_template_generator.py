"""Verify the reference-DOCX generator produces 3 distinct ATS templates."""
from __future__ import annotations

import importlib
import sys
import zipfile
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = BACKEND_DIR / "scripts"
TEMPLATES_DIR = BACKEND_DIR / "templates"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def test_generator_writes_three_distinct_templates():
    # Import lazily so the test fails on missing files rather than ImportError
    # if generate_cv_template ever moves.
    module = importlib.import_module("generate_cv_template")
    importlib.reload(module)

    assert module.main() == 0

    expected = {
        "plain": TEMPLATES_DIR / "cv-template-plain.docx",
        "classic": TEMPLATES_DIR / "cv-template-classic.docx",
        "modern": TEMPLATES_DIR / "cv-template-modern.docx",
    }

    for name, path in expected.items():
        assert path.exists(), f"file {path} does not exist"
        assert path.stat().st_size > 5000, (
            f"file {path} suspiciously small ({path.stat().st_size} bytes)"
        )

    styles_blobs = {
        name: zipfile.ZipFile(path).read("word/styles.xml")
        for name, path in expected.items()
    }

    # All three styles.xml payloads must differ — proves the spec table
    # diverges per template, not just the output filename.
    assert styles_blobs["plain"] != styles_blobs["classic"]
    assert styles_blobs["classic"] != styles_blobs["modern"]
    assert styles_blobs["plain"] != styles_blobs["modern"]
