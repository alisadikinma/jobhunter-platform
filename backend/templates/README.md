# Pandoc reference templates

This directory holds the styled DOCX reference Pandoc uses when rendering
generated CVs (`pandoc --reference-doc=cv-template.docx`).

The file `cv-template.docx` is **not** committed — it's binary, locale-dependent,
and Pandoc generates a sensible default. Two ways to populate it:

## In Docker (production)

The `backend/Dockerfile` runs Pandoc at build time:

```
pandoc --print-default-data-file=reference.docx > /app/templates/cv-template.docx
```

The image then sets `CV_REFERENCE_DOCX=/app/templates/cv-template.docx`.

## On a dev host

Pandoc must be on `PATH`. From the repo root:

```bash
python backend/scripts/generate_cv_template.py
```

Then point `CV_REFERENCE_DOCX` at the generated file in your `.env`:

```
CV_REFERENCE_DOCX=backend/templates/cv-template.docx
```

If `CV_REFERENCE_DOCX` is empty, Pandoc falls back to its built-in default
(also single-column, also ATS-safe — just unstyled).

## Customising the template

Open `cv-template.docx` in Word/LibreOffice and edit the **styles** (Heading 1,
Heading 2, Body Text, etc.) — never the body text. Pandoc only copies styles
across; body content always comes from the markdown input. Keep the layout
single-column with no tables to stay ATS-compatible.
