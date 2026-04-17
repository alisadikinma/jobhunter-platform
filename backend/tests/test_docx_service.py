"""DOCX / PDF service tests — subprocess runner injected."""
from unittest.mock import MagicMock

import pytest

from app.services.docx_service import ConversionError, docx_to_pdf, markdown_to_docx


def test_markdown_to_docx_runs_pandoc_with_correct_args(tmp_path):
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["input"] = kwargs.get("input")
        # Simulate pandoc creating the output file.
        out_index = cmd.index("-o") + 1
        out_path = cmd[out_index]
        with open(out_path, "wb") as f:
            f.write(b"fake-docx-bytes")
        return MagicMock(returncode=0)

    out = tmp_path / "cv.docx"
    markdown_to_docx("# Hello\n\nBody.", out, runner=fake_run)

    assert out.exists()
    assert out.stat().st_size > 0
    assert captured["cmd"][0] == "pandoc"
    assert "-f" in captured["cmd"] and "markdown" in captured["cmd"]
    assert "-t" in captured["cmd"] and "docx" in captured["cmd"]
    assert captured["input"].startswith("# Hello")


def test_markdown_to_docx_uses_reference_doc_when_exists(tmp_path):
    ref = tmp_path / "ref.docx"
    ref.write_bytes(b"ref")
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        out_idx = cmd.index("-o") + 1
        with open(cmd[out_idx], "wb") as f:
            f.write(b"x")
        return MagicMock(returncode=0)

    markdown_to_docx("# x", tmp_path / "out.docx", reference_docx=ref, runner=fake_run)
    assert "--reference-doc" in captured["cmd"]
    assert str(ref) in captured["cmd"]


def test_markdown_to_docx_raises_when_pandoc_missing(tmp_path):
    def fake_run(*_a, **_k):
        raise FileNotFoundError("pandoc")

    with pytest.raises(ConversionError, match="pandoc binary"):
        markdown_to_docx("# x", tmp_path / "out.docx", runner=fake_run)


def test_markdown_to_docx_raises_when_pandoc_produces_empty(tmp_path):
    def fake_run(cmd, **_k):
        # Create the file but leave it empty.
        out_idx = cmd.index("-o") + 1
        open(cmd[out_idx], "w").close()
        return MagicMock(returncode=0)

    with pytest.raises(ConversionError, match="produced no DOCX"):
        markdown_to_docx("# x", tmp_path / "empty.docx", runner=fake_run)


def test_docx_to_pdf_invokes_libreoffice(tmp_path):
    docx = tmp_path / "in.docx"
    docx.write_bytes(b"docx")
    pdf_out = tmp_path / "out.pdf"
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        # soffice writes <stem>.pdf in the outdir:
        default = tmp_path / "in.pdf"
        default.write_bytes(b"pdf-bytes")
        return MagicMock(returncode=0)

    result = docx_to_pdf(docx, pdf_out, runner=fake_run)
    assert result == pdf_out
    assert result.read_bytes() == b"pdf-bytes"
    assert "--headless" in captured["cmd"]
    assert "--convert-to" in captured["cmd"]
    assert "pdf" in captured["cmd"]


def test_docx_to_pdf_raises_when_source_missing(tmp_path):
    def fake_run(*_a, **_k):  # should never run
        return None

    with pytest.raises(ConversionError, match="source DOCX missing"):
        docx_to_pdf(tmp_path / "nope.docx", tmp_path / "o.pdf", runner=fake_run)
