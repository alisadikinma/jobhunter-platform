"""Pandoc-based markdown → DOCX / PDF conversion.

Pandoc is assumed to be on PATH inside the container (installed via
apt-get in Phase 22's Dockerfile). Tests inject a fake runner.
"""
import logging
import shutil
import subprocess
from pathlib import Path

log = logging.getLogger(__name__)


class ConversionError(RuntimeError):
    pass


def _resolve_runner(runner):
    return runner or subprocess.run


def markdown_to_docx(
    markdown: str,
    output_path: Path,
    *,
    reference_docx: Path | None = None,
    runner=None,
) -> Path:
    """Render `markdown` to a DOCX file via Pandoc.

    If `reference_docx` is provided, Pandoc uses it as the style template
    (single-column layout, ATS-safe fonts). Otherwise defaults to Pandoc's
    built-in template.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "pandoc",
        "-f", "markdown",
        "-t", "docx",
        "-o", str(output_path),
    ]
    if reference_docx and reference_docx.exists():
        cmd.extend(["--reference-doc", str(reference_docx)])

    try:
        _resolve_runner(runner)(
            cmd,
            input=markdown,
            text=True,
            check=True,
            capture_output=True,
            timeout=60,
        )
    except FileNotFoundError as e:
        raise ConversionError("pandoc binary not on PATH") from e
    except subprocess.CalledProcessError as e:
        raise ConversionError(
            f"pandoc failed (exit {e.returncode}): {e.stderr or e.stdout}"
        ) from e

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise ConversionError("pandoc ran but produced no DOCX output")

    return output_path


def docx_to_pdf(
    docx_path: Path,
    output_path: Path,
    *,
    runner=None,
) -> Path:
    """Convert DOCX → PDF via LibreOffice headless (more reliable than
    pandoc's PDF engines on Linux containers)."""
    if not docx_path.exists():
        raise ConversionError(f"source DOCX missing: {docx_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if soffice is None and runner is None:
        raise ConversionError("libreoffice/soffice not on PATH")

    cmd = [
        soffice or "soffice",
        "--headless", "--convert-to", "pdf",
        "--outdir", str(output_path.parent),
        str(docx_path),
    ]
    try:
        _resolve_runner(runner)(
            cmd,
            check=True,
            capture_output=True,
            timeout=120,
        )
    except FileNotFoundError as e:
        raise ConversionError("libreoffice binary not on PATH") from e
    except subprocess.CalledProcessError as e:
        raise ConversionError(
            f"libreoffice failed (exit {e.returncode}): {e.stderr}"
        ) from e

    # soffice writes <stem>.pdf in the outdir — rename to desired output_path.
    default_out = output_path.parent / (docx_path.stem + ".pdf")
    if default_out != output_path and default_out.exists():
        default_out.replace(output_path)
    if not output_path.exists() or output_path.stat().st_size == 0:
        raise ConversionError("libreoffice ran but produced no PDF output")
    return output_path
