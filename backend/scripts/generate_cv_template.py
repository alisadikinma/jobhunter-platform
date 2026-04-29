"""Generate the Pandoc reference DOCX used to style tailored CVs.

Pandoc ships a built-in single-column reference that's already ATS-safe.
This script just dumps it to `backend/templates/cv-template.docx` so
`docx_service.markdown_to_docx(..., reference_docx=...)` can pick it up.

Usage (from repo root):

    python backend/scripts/generate_cv_template.py

Re-run any time you want to reset the styles to Pandoc defaults. To
customise, open the resulting .docx in Word/LibreOffice and edit the
*styles* (Heading 1, Body Text, etc.) — Pandoc only copies styles across.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

OUT_PATH = Path(__file__).resolve().parents[1] / "templates" / "cv-template.docx"


def main() -> int:
    if shutil.which("pandoc") is None:
        print("error: pandoc not on PATH. Install it from https://pandoc.org/installing.html", file=sys.stderr)
        return 1

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("wb") as fh:
        proc = subprocess.run(
            ["pandoc", "--print-default-data-file=reference.docx"],
            stdout=fh,
            stderr=subprocess.PIPE,
            check=False,
        )
    if proc.returncode != 0:
        print(f"pandoc failed (exit {proc.returncode}): {proc.stderr.decode(errors='replace')}", file=sys.stderr)
        return proc.returncode
    if OUT_PATH.stat().st_size == 0:
        print(f"error: pandoc produced empty file at {OUT_PATH}", file=sys.stderr)
        return 1
    print(f"wrote {OUT_PATH} ({OUT_PATH.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
