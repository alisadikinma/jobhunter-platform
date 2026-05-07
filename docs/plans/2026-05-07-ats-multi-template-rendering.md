> **For Claude:** REQUIRED SKILL: Use gaspol-execute to implement this plan.
> **CRITICAL:** This plan specifies real integrations. During execution,
> NEVER substitute placeholders for real data sources without explicit
> user approval. If a data source doesn't exist yet, STOP and ask.

## Goal

Make the ATS CV template picker in `/settings?tab=ats-cv` produce three visually distinct, ATS-safe resumes — not three CSS skins of the same Pandoc output. When the user picks **Plain**, **Classic**, or **Modern**, the HTML preview, downloadable DOCX, and PDF must all reflect that template's font, header treatment, and section ordering. Each template is anchored to a real industry reference: Rezi-style Plain ATS (max parser safety), Harvard OCS Classic (finance / consulting / recent grads), and Jake's-Resume-inspired Modern (tech / SWE).

## Architecture Context

Pulled from [CLAUDE.md](../../CLAUDE.md) and the just-shipped CSS-only template work:

- **Renderer:** [backend/app/services/master_cv_renderer.py](../../backend/app/services/master_cv_renderer.py) already accepts `template: str` parameter (currently only varies section-header casing). Sections rendered in fixed order today: Summary → Experience → Education → Skills → Awards → Certifications → Projects.
- **API:** [backend/app/api/cv.py](../../backend/app/api/cv.py) `/api/cv/master/preview`, `/preview.html`, `/download/{fmt}` already accept `?template=` and cache artifacts as `master-cv-vN-<template>.{docx,pdf}`. Today every template uses the same single `settings.CV_REFERENCE_DOCX`.
- **Reference DOCX builder:** [backend/scripts/generate_cv_template.py](../../backend/scripts/generate_cv_template.py) builds ONE reference doc via `python-docx` (already a dep, requirements.txt: `python-docx==1.1.*`). Output: `backend/templates/cv-ats-template.docx`.
- **Pandoc plumbing:** [backend/app/services/docx_service.py](../../backend/app/services/docx_service.py) `markdown_to_docx(...)` takes optional `reference_docx: Path` — already wired, just needs per-template path lookup. PDF via `docx_to_pdf` calls LibreOffice headless.
- **Docker build:** Dockerfile runs `python scripts/generate_cv_template.py` so the template file ships in the image (no binary in git). CLAUDE.md gotcha — LaTeX engines break in slim containers, so we stay on the Pandoc reference-doc path.
- **Frontend:** [frontend/src/components/settings/AtsCvTab.tsx](../../frontend/src/components/settings/AtsCvTab.tsx) template picker + [frontend/src/hooks/useCV.ts](../../frontend/src/hooks/useCV.ts) `AtsTemplate = "plain" | "classic" | "modern"` already pass `?template=` through. Frontend needs no logic change — only the visual output changes.
- **Storage gotcha:** Existing `backend/storage/master-cv-v*-{template}.{docx,pdf}` files were rendered when all templates shared one reference doc. They MUST be deleted (or the cache key bumped) once Phase A lands so the next download re-renders against the right reference.

## Tech Stack

- **DOCX styling:** `python-docx 1.1.x` (existing dep) — programmatically authored reference docs in source control. No external CV templates downloaded (copyright + redistribution risk).
- **Markdown → DOCX:** `pandoc` subprocess via `markdown_to_docx`. `--reference-doc` is the supported style mechanism per [Pandoc manual](https://pandoc.org/MANUAL.html); inline span styles silently ignored ([pandoc#8149](https://github.com/jgm/pandoc/issues/8149)) so all styling lives at block level.
- **DOCX → PDF:** `libreoffice --headless --convert-to pdf` (CLAUDE.md gotcha: pandoc's PDF engines all break in slim containers).
- **Tests:** `pytest` + existing `tests/test_cv_render_api.py` / `test_cv_api.py` patterns.
- **Frontend:** zero new deps — template picker + hooks already wired.

## Design

### Industry research (May 2026)

| Family | Best fit | ATS-safety reason | Source |
|---|---|---|---|
| **Jake's Resume** | Tech / SWE / engineering | Single column, dense Skills + Projects, sections re-orderable | [github.com/jakegut/resume](https://github.com/jakegut/resume) |
| **Harvard OCS** | Finance / consulting / recent grads | Single column, serif, centered name, Education-first | [CandyCV breakdown](https://www.candycv.com/how-to/harvard-and-jakes-resume-templates-why-their-linkedin-like-structure-wins-recruiter-attention-11) |
| **Plain ATS / Rezi-style** | Recruiter-funnel safety | Arial 11pt, ALL-CAPS underlined headers, no color | [Rezi templates](https://www.rezi.ai/resume-templates) |
| **Deedy (excluded)** | — | Two columns → fails Workday/Greenhouse parsers ~30% of the time | [Rejectless comparison](https://www.rejectless.app/guides/jakes-resume-vs-deedy-resume) |

**Hard rule:** every shipped template is single-column. Two-column resumes interleave when ATS parsers go left-to-right top-to-bottom.

### Final 3-template spec

| Aspect | **Plain ATS** *(default)* | **Classic** *(Harvard OCS)* | **Modern** *(Jake's-inspired)* |
|---|---|---|---|
| Font | Arial 11pt | Times New Roman 11pt | Calibri 11pt |
| Margins | 0.55" | 0.7" | 0.6" |
| Name (H1) | 18pt left, plain black `#000` | 22pt centered, letter-spaced | 24pt left, navy `#141e32` |
| Section H2 | 11.5pt **ALL CAPS**, 1pt underline | 12pt Title Case, 0.75pt rule | 13pt **ALL CAPS** + 1.2px tracking, 0.75pt rule |
| Section order | Summary → Experience → Skills → Projects → Education → Awards → Certifications | Summary → **Education first** → Experience → Skills → Awards → Certifications → Projects | Summary → **Skills first** → Experience → Projects → Awards → Education → Certifications |
| Color | `#000` everywhere | Near-black `#1a1a1a`, no accents | Navy `#141e32` on H1 + H2 |
| Bullet density | Standard | Tight (Harvard convention) | Tightest (Jake's signature) |
| Use case | Recruiter-skim safety | Finance / consulting / legal / recent grads | Tech / SWE / startup |

### Why this approach (not LaTeX, not external templates)

- **LaTeX rendering ruled out** — texlive adds ~3GB to the container. CLAUDE.md gotcha explicitly notes "Pandoc's PDF engines (xelatex, wkhtmltopdf) all break in slim containers."
- **Hand-authored Word reference docs ruled out** — binary files in git, no audit trail, no diffs. Existing `python-docx` script proves the programmatic path works.
- **Downloading third-party templates ruled out** — copyright + redistribution risk on Jake's, Harvard OCS, Rezi files. We copy the *visual conventions*, not the files.

## Data Integration Map

| Feature | Data Source | Hook/API | Exists? | Action |
|---|---|---|---|---|
| Template picker UI | local React state in `AtsCvTab` | `useState<AtsTemplate>` | Yes | Use as-is, no change |
| Preview HTML per template | `GET /api/cv/master/preview.html?template=` | `useMasterCVHtmlPreview(template)` | Yes | Backend CSS retuned to mirror DOCX |
| DOCX/PDF download per template | `GET /api/cv/master/download/{fmt}?template=` | `downloadMasterCV(fmt, template)` | Yes | Backend swaps reference doc per template |
| Master CV content | `master_cv` Postgres row, JSONB | `_active_master(db)` | Yes | Read-only, no schema change |
| Section ordering per template | `SECTION_ORDER` constant in renderer | new constant | No | Create in `master_cv_renderer.py` |
| Reference DOCX per template | `backend/templates/cv-template-{name}.docx` | filesystem lookup | Partial — only one file today | Refactor `generate_cv_template.py` to build 3 |
| Reference DOCX directory setting | `settings.CV_REFERENCE_DOCX_DIR` | `app/config.py` | No | Add new setting; keep `CV_REFERENCE_DOCX` for back-compat fallback |
| Stale storage cache invalidation | filesystem `backend/storage/master-cv-v*-{template}.*` | manual delete on first request | No | Add cache-bust marker file `_template_revision` so first request after deploy regenerates |
| Pandoc subprocess | `markdown_to_docx(reference_docx=...)` | already accepts path | Yes | Just pass the right path |
| python-docx package | `requirements.txt` | `python-docx==1.1.*` | Yes | Already installed |

## Implementation Plan

### Phase A: Refactor reference-docx generator to build 3 templates

**Estimated time:** 12 minutes

**Files:**
- Modify: `backend/scripts/generate_cv_template.py` (refactor `main()` to call `_build_template(name, spec)` 3 times; spec dict per template)
- Create: `backend/templates/cv-template-plain.docx` (output)
- Create: `backend/templates/cv-template-classic.docx` (output)
- Create: `backend/templates/cv-template-modern.docx` (output)
- Test: `backend/tests/test_cv_template_generator.py`

**Steps:**
1. Write failing test `test_generates_three_template_files` in `test_cv_template_generator.py` that imports `main` from the script, runs it in a tmp dir (via monkeypatching `OUT_DIR`), and asserts all 3 expected `.docx` files exist with non-zero size. Expected error: `AssertionError: file backend/templates/cv-template-plain.docx does not exist` (or `ImportError: cannot import name 'main'` if signature changed first).
2. Run test, confirm it fails for the expected reason.
3. Refactor `main()` to:
   - Define `TEMPLATE_SPECS: dict[str, TemplateSpec]` with font, margins, H1 size, H2 styling, color tuple per template (plain/classic/modern).
   - Extract `_build_template(name: str, spec: TemplateSpec) -> Path` from current monolithic `main()`.
   - Loop over `TEMPLATE_SPECS.items()` and write to `backend/templates/cv-template-{name}.docx`.
   - Keep the legacy `cv-ats-template.docx` write commented-out OR aliased to `cv-template-modern.docx` for transitional safety (rm in Phase E).
4. Run test, confirm 3 files generated.
5. Manual smoke: open each `.docx` in Word/LibreOffice, confirm visual differences match spec table (Arial vs TNR vs Calibri, centered vs left H1, color presence).
6. Commit: `feat(cv): generate 3 ATS reference DOCX templates (plain, classic, modern)`

**Verification:**
- [ ] `pytest backend/tests/test_cv_template_generator.py -v` passes
- [ ] All 3 files in `backend/templates/cv-template-{plain,classic,modern}.docx` exist with size > 5KB
- [ ] Visual inspection: Plain = Arial all-caps headers; Classic = Times centered name; Modern = Calibri navy accents
- [ ] No placeholder/TODO comments in new code
- [ ] `tsc --noEmit` n/a (backend phase)

---

### Phase B: Per-template section ordering in renderer

**Estimated time:** 10 minutes

**Files:**
- Modify: `backend/app/services/master_cv_renderer.py` (add `SECTION_ORDER` map; refactor `render_master_cv_to_markdown` to iterate)
- Test: `backend/tests/test_master_cv_renderer_ordering.py` (new)

**Steps:**
1. Write failing test `test_section_ordering_per_template` that calls `render_master_cv_to_markdown(sample_content, template="classic")` and asserts the index of `"## Education"` is less than the index of `"## Experience"` (Harvard convention). Add parallel assertions for plain (Experience before Education) and modern (Skills before Experience). Expected error: `AssertionError: Education at index N > Experience at index M`.
2. Run test, confirm it fails — current renderer always emits Experience before Education.
3. Add `SECTION_ORDER: dict[str, tuple[str, ...]]` keyed by template, listing section keys: `("summary", "experience", "skills", "projects", "education", "awards", "certifications")` for plain, etc.
4. Refactor body of `render_master_cv_to_markdown` to build a `section_renderers` dict mapping each key to a callable that returns its block, then iterate `SECTION_ORDER[template]` in order.
5. Run test, confirm pass.
6. Run existing `pytest backend/tests/test_cv_render_api.py backend/tests/test_cv_api.py backend/tests/test_html_strip.py` — confirm no regression.
7. Commit: `feat(cv): per-template section ordering in master CV renderer`

**Verification:**
- [ ] `pytest backend/tests/test_master_cv_renderer_ordering.py -v` passes
- [ ] Existing CV test suite still 28/28 green
- [ ] No placeholder/TODO comments
- [ ] `SECTION_ORDER` keys exactly equal `SUPPORTED_TEMPLATES`

---

### Phase C: Wire per-template reference DOCX in API + config

**Estimated time:** 10 minutes

**Files:**
- Modify: `backend/app/config.py` (add `CV_REFERENCE_DOCX_DIR` setting)
- Modify: `backend/app/api/cv.py` (`_resolve_reference_docx(template)` helper; `download_master_cv` uses it)
- Test: `backend/tests/test_cv_render_api.py` (extend with template→reference-doc assertion)

**Steps:**
1. Write failing test `test_download_uses_template_specific_reference` that monkeypatches `markdown_to_docx` to capture the `reference_docx` kwarg, hits `GET /api/cv/master/download/docx?template=classic` via `TestClient`, and asserts captured path basename is `cv-template-classic.docx`. Expected error: `AssertionError: expected 'cv-template-classic.docx', got 'cv-ats-template.docx'`.
2. Run test, confirm fail.
3. Add `CV_REFERENCE_DOCX_DIR: str = "backend/templates"` to `app/config.py` Settings (with env override `CV_REFERENCE_DOCX_DIR`).
4. Add `_resolve_reference_docx(template: str) -> Path | None` in `cv.py` that returns `Path(settings.CV_REFERENCE_DOCX_DIR) / f"cv-template-{template}.docx"` if exists, else falls back to `settings.CV_REFERENCE_DOCX` (backward compat).
5. Replace the `ref = Path(settings.CV_REFERENCE_DOCX) ...` line in `download_master_cv` with `ref = _resolve_reference_docx(tpl)`.
6. Run test, confirm pass.
7. Run full backend suite `pytest -q` — no regressions.
8. Commit: `feat(cv): pick reference DOCX per ATS template at download time`

**Verification:**
- [ ] New test passes for all 3 templates (parametrize)
- [ ] Backward-compat: setting only `CV_REFERENCE_DOCX` (no dir) still works for the "modern" template (legacy alias)
- [ ] No placeholder/TODO comments
- [ ] `pytest -q` full suite green

---

### Phase D: Tighten preview CSS to mirror DOCX fonts + bust stale cache

**Estimated time:** 8 minutes

**Files:**
- Modify: `backend/app/api/cv.py` (`_PLAIN_CSS`, `_CLASSIC_CSS`, `_MODERN_CSS` font declarations + sizes match the spec table exactly)
- Modify: `backend/app/api/cv.py` (`_master_artifact_paths` add a `_REFERENCE_REVISION` suffix or marker so cached files from before Phase A get bypassed)

**Steps:**
1. Write failing test `test_preview_css_matches_template_spec` that GETs `/api/cv/master/preview.html?template=classic` and asserts the response body contains `Times New Roman` AND `text-align: center` (for the H1). Expected error: `AssertionError: 'text-align: center' not found in response`.
2. Run test, confirm fail.
3. Update `_CLASSIC_CSS` so H1 has `text-align: center` and `letter-spacing: 1px` per spec; ensure `font: 11pt/1.5 'Times New Roman', Times, serif;` on body.
4. Update `_PLAIN_CSS` Arial spec; `_MODERN_CSS` Calibri navy spec — all match the design spec table.
5. Add module-level `_REFERENCE_REVISION = "v2"` const; update `_master_artifact_paths` to include it: `f"master-cv-v{version}-{template}-{_REFERENCE_REVISION}.{ext}"`. Old cached files become orphaned, next request re-renders against the right reference doc. (Cleanup of orphans is out of scope — will get GC'd next storage volume rotation.)
6. Run test, confirm pass.
7. Manual: hit `/settings?tab=ats-cv`, switch through all 3 templates, confirm each preview visibly reflects font + ordering changes.
8. Commit: `feat(cv): align ATS preview CSS to per-template DOCX spec; bust stale cache`

**Verification:**
- [ ] New CSS test passes for all 3 templates
- [ ] Manual: preview iframe in 3 templates shows Arial / Times-centered / Calibri-navy respectively
- [ ] Cache key includes `_REFERENCE_REVISION` — verified via filename pattern in storage dir after fresh download
- [ ] No placeholder/TODO comments

---

### Phase E: Dockerfile build step generates all 3 reference docs + drop legacy alias

**Estimated time:** 6 minutes

**Files:**
- Modify: `backend/Dockerfile` (run new generator script invocation)
- Modify: `backend/scripts/generate_cv_template.py` (remove transitional `cv-ats-template.docx` alias from Phase A)
- Modify: `.dockerignore` if any reference docs were accidentally tracked

**Steps:**
1. Write failing test (manual / CI shell) that builds the Docker image and runs `docker run --rm <img> ls /app/backend/templates/` — confirm 3 files present. Expected: only `cv-ats-template.docx` exists (legacy state).
2. Run, confirm fail.
3. Update Dockerfile's CV-template generation step to use the refactored script (no command change if `python scripts/generate_cv_template.py` still does the right thing — verify args).
4. Remove the legacy `cv-ats-template.docx` write from the script (now safe — Phase C handles fallback to the modern template).
5. Update `.dockerignore` if needed so `backend/templates/*.docx` is not excluded (template files must reach the image).
6. Build image locally: `docker compose build api`. Confirm `docker compose run --rm api ls /app/backend/templates/` shows all 3 files.
7. Commit: `chore(docker): generate 3 ATS reference DOCXs in image build`

**Verification:**
- [ ] `docker compose build api` succeeds without warnings
- [ ] `docker compose run --rm api ls backend/templates/` lists exactly `cv-template-plain.docx`, `cv-template-classic.docx`, `cv-template-modern.docx`
- [ ] No placeholder/TODO comments
- [ ] Legacy `cv-ats-template.docx` no longer appears anywhere

---

### Phase F: End-to-end integration test + production smoke

**Estimated time:** 8 minutes

**Files:**
- Create: `backend/tests/test_cv_template_e2e.py` (parametrized over 3 templates, asserts download endpoint returns a non-empty DOCX whose underlying XML differs per template)
- Modify: `CLAUDE.md` (note the per-template reference doc lookup + `CV_REFERENCE_DOCX_DIR` setting)

**Steps:**
1. Write failing test `test_download_returns_distinct_docx_per_template` that downloads DOCX for each of plain/classic/modern via `TestClient`, hashes the bytes, asserts all 3 hashes differ. Expected fail before all phases land OR if cache files weren't busted.
2. Run, confirm pass (all prior phases must be in).
3. Add a CLAUDE.md "Conventions" entry documenting `CV_REFERENCE_DOCX_DIR` and the `cv-template-{plain,classic,modern}.docx` file convention.
4. Add a CLAUDE.md "Debugging Checklist" entry: "If two ATS templates produce identical DOCX, check `_REFERENCE_REVISION` in `cv.py` — the storage cache was likely keyed on stale revision."
5. Manual production smoke (after deploy): pull `https://jobs.alisadikinma.com/api/cv/master/download/pdf?template=classic` and `?template=modern`, diff with `pdfdiff` or visual — confirm visibly different.
6. Commit: `test(cv): e2e per-template DOCX divergence + CLAUDE.md notes`

**Verification:**
- [ ] `pytest backend/tests/test_cv_template_e2e.py -v` passes
- [ ] CLAUDE.md updated under both "Conventions" and "Debugging Checklist"
- [ ] No placeholder/TODO comments
- [ ] Production smoke: 3 downloaded PDFs visibly differ in font + section ordering

---

## Phase summary

| Phase | What | Files | Time | Independent? |
|---|---|---|---|---|
| A | Build 3 reference DOCXs | `generate_cv_template.py`, `templates/*.docx`, test | 12m | Yes |
| B | Per-template section ordering | `master_cv_renderer.py`, test | 10m | Yes (independent of A) |
| C | API picks right reference doc | `config.py`, `cv.py`, test | 10m | Depends on A |
| D | Tighten preview CSS + bust cache | `cv.py`, test | 8m | Depends on B (uses ordering) |
| E | Dockerfile generates 3 docs | `Dockerfile`, `generate_cv_template.py` cleanup | 6m | Depends on A |
| F | E2E test + CLAUDE.md | new test, `CLAUDE.md` | 8m | Depends on all |

**Total estimated:** ~54 min serial. Phases A + B are independent — runnable in parallel via `gaspol-parallel` mode `plan-phases`, saving ~10 min.

## Red-flag self-check

- ✅ Data Integration Map present
- ✅ Every phase has TDD step 1 in `Write failing test for X. Expected error: Y` format
- ✅ Every phase has Verification block
- ✅ References CLAUDE.md by file path with line context
- ✅ All data sources concrete (no "wire it up later")
- ✅ No phase exceeds 15 min estimated
- ✅ No placeholder language

## Execution handoff

Three options:

**Option 1: Execute in this session**
Ready to start Phase A? I'll use gaspol-execute to implement with per-phase checkpoints.

**Option 2: Parallel execution**
Phases A and B are independent — `gaspol-parallel` (mode `plan-phases`) can run them concurrently in two worktrees, then merge before Phase C. Saves ~10 min.

**Option 3: Separate session**
Save plan for a new session — this file at [docs/plans/2026-05-07-ats-multi-template-rendering.md](docs/plans/2026-05-07-ats-multi-template-rendering.md) has everything needed to resume.
