> **For Claude:** REQUIRED SKILL: Use gaspol-execute to implement this plan.
> **CRITICAL:** This plan specifies real integrations. During execution,
> NEVER substitute placeholders for real data sources without explicit
> user approval. If a data source doesn't exist yet, STOP and ask.

# ATS-Friendly CV Import (Multi-Page Scrape + Sonnet)

## Goal

Fix the JobHunter CV-import-from-URL flow so the resulting Master CV is ATS-friendly. Today the flow scrapes a single URL with Haiku and a generic prompt — output for `https://alisadikinma.com/en` returns 4 work entries / 5 projects / 42 noisy skills (model names like "VEO 3.1", meta-concepts like "Multi-agent Architecture") and a truncated name "Ali Sadikin Ma". After this plan: the importer scrapes all four portfolio pages in parallel (`/en`, `/en/about`, `/en/work?tab=awards`, `/en/work?tab=projects`), concatenates the markdown, and runs a Sonnet 4.6 extraction with an ATS-aware system prompt that filters skills, quantifies highlights, and forces complete capture across all sections. Hard scope: JobHunter-only changes. No Portfolio_v2 changes.

## Architecture Context

Pulled from [CLAUDE.md](../../CLAUDE.md):

- **CV import endpoint:** `POST /api/cv/master/import-url` in [backend/app/api/cv.py](../../backend/app/api/cv.py)
- **Master CV schema:** `MasterCVContent` in [backend/app/schemas/cv.py](../../backend/app/schemas/cv.py) — `basics + work + projects + education + skills`. `email` already coerces empty string → None (fixed 2026-05-02 in commit `62a0052`).
- **Firecrawl pool:** `FirecrawlService.scrape(url, opts)` in [backend/app/services/firecrawl_service.py](../../backend/app/services/firecrawl_service.py) — multi-account rotation, sync httpx, supports `waitFor` opts. Pool is reentrant per scrape call (acquires + releases an account each time).
- **CV parser:** `parse_cv_to_json_resume(raw_text)` in [backend/app/services/cv_parser.py](../../backend/app/services/cv_parser.py) — feeds raw text + system prompt to `extract_json_via_cli`. Currently truncates at 50000 chars; uses default model (`claude-haiku-4-5`).
- **LLM extractor:** `extract_json_via_cli(system_prompt, user_message, model=...)` in [backend/app/services/llm_extractor.py](../../backend/app/services/llm_extractor.py) — Claude CLI subprocess, OAuth via `CLAUDE_CODE_OAUTH_TOKEN` env (fixed 2026-05-02). Returns parsed JSON dict. Strips ``` fences.
- **Tests:** pytest in [backend/tests/](../../backend/tests/) — existing patterns in [test_cv_upload.py](../../backend/tests/test_cv_upload.py) (mocks `subprocess.run` for the CLI) and [test_portfolio_import.py](../../backend/tests/test_portfolio_import.py) (mocks Firecrawl + extractor).
- **Frontend Master CV tab:** [frontend/src/components/settings/MasterCvTab.tsx](../../frontend/src/components/settings/MasterCvTab.tsx) — URL import via `useImportMasterCVFromURL` in [frontend/src/hooks/useCV.ts](../../frontend/src/hooks/useCV.ts).

## Tech Stack

Reference existing stack from CLAUDE.md (no additions):

- **Backend:** FastAPI 0.115 + Pydantic v2 + sync SQLAlchemy + httpx (already used by FirecrawlService)
- **Concurrency:** `concurrent.futures.ThreadPoolExecutor` (stdlib, no new dep) — Firecrawl pool already thread-safe per-scrape because each `acquire_account` is row-locked
- **LLM:** Claude CLI subprocess via existing `extract_json_via_cli`. New model: `claude-sonnet-4-6` (latest Sonnet per environment context)
- **Tests:** pytest + monkeypatch (matches existing test conventions)
- **Frontend:** Next.js 15 + React 19 + TanStack Query + shadcn `Textarea` (already in repo)

## Data Integration Map

| Feature | Data Source | API/Helper | Exists? | Action |
|---|---|---|---|---|
| Single-URL scrape | Firecrawl pool | `FirecrawlService.scrape(url, opts)` | Yes | Use existing |
| Parallel multi-URL scrape | Firecrawl pool × N | `scrape_multiple_pages(urls, db)` | No | Create new helper in `multi_scraper.py` |
| URL auto-derivation | n/a (pure logic) | `derive_portfolio_urls(base)` | No | Create new helper in `multi_scraper.py` |
| LLM extraction | Claude CLI subprocess | `extract_json_via_cli(prompt, msg, model=...)` | Yes | Pass `model="claude-sonnet-4-6"` |
| ATS-aware system prompt | Inline string | `_EXTRACTION_SYSTEM_PROMPT` in `cv_parser.py` | Yes (generic) | Rewrite content with ATS rules |
| Master CV persist | Postgres `master_cv` table | `_save_new_master(db, parsed, ...)` | Yes | Use existing |
| Schema validation | Pydantic | `MasterCVContent.model_validate` | Yes | Use existing (email coercion already in place) |
| Frontend URL import hook | TanStack Query mutation | `useImportMasterCVFromURL` | Yes | Extend payload to support `urls: string[]` |
| Frontend multi-URL input | shadcn Textarea | `MasterCvTab.tsx` | Yes (Textarea) | Add toggle + textarea |
| Request schema | Pydantic | `MasterCVImportURLRequest` | Yes | Add `urls: list[str] | None` field |

## Phases

### Phase A: Backend — multi-URL parallel scraper helper

**Estimated time:** 25 minutes

**Files:**
- Create: `backend/app/services/multi_scraper.py`
- Test: `backend/tests/test_multi_scraper.py`

**Steps:**
1. Write failing test for `scrape_multiple_pages(urls, db)` returning concatenated markdown with section delimiters and skipping failed URLs. Expected error: `ImportError: cannot import name 'scrape_multiple_pages' from 'app.services.multi_scraper'`.
2. Run test, confirm it fails for the expected reason.
3. Implement `scrape_multiple_pages(urls: list[str], db: Session, *, wait_for_ms: int = 8000, max_workers: int = 4) -> str`:
   - Use `concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)`.
   - For each URL submit a task that opens its own `FirecrawlService(db=db)` context and calls `.scrape(url, opts={"waitFor": wait_for_ms})`.
   - Collect results; for each non-empty `markdown`, prepend `"\n\n=== Page: {url} ===\n\n"` separator.
   - Skip URLs returning empty markdown or error (log warning via module logger). Raise `MultiScrapeError` only if ALL urls fail.
   - Return single concatenated string (joined in input URL order).
4. Run tests, confirm all pass (1 happy path, 1 partial-failure, 1 all-fail-raises).
5. Commit: `feat(scraper): add parallel multi-page scrape helper`

**Verification:**
- [ ] `pytest backend/tests/test_multi_scraper.py -v` passes
- [ ] Helper executes scrapes in parallel (verified via test that asserts wall time < N×scrape_time using mocked sleeps)
- [ ] No placeholder/TODO comments in new code
- [ ] Module logger emits warnings for skipped URLs (visible via caplog fixture)

---

### Phase B: Backend — URL auto-derivation helper

**Estimated time:** 15 minutes

**Files:**
- Modify: `backend/app/services/multi_scraper.py`
- Modify: `backend/tests/test_multi_scraper.py`

**Steps:**
1. Write failing test for `derive_portfolio_urls("https://alisadikinma.com/en")` returning exactly 4 URLs in stable order: `[base, base+"/about", base+"/work?tab=awards", base+"/work?tab=projects"]`. Expected error: `AttributeError: module 'app.services.multi_scraper' has no attribute 'derive_portfolio_urls'`.
2. Run test, confirm it fails for the expected reason.
3. Implement `derive_portfolio_urls(base_url: str) -> list[str]`:
   - Parse via `urllib.parse.urlparse`. Strip trailing slash from path.
   - Build 4 URLs: base, `{base}/about`, `{base}/work?tab=awards`, `{base}/work?tab=projects`.
   - Dedupe while preserving order (in case base already ends with `/about` etc.).
   - Return `list[str]`.
4. Run tests, confirm all pass (1 happy path with `/en` base, 1 with `/en/` trailing slash, 1 with bare domain `https://example.com`).
5. Commit: `feat(scraper): add portfolio URL auto-derivation`

**Verification:**
- [ ] `pytest backend/tests/test_multi_scraper.py::test_derive_portfolio_urls -v` passes
- [ ] Output is deterministic (same order each call)
- [ ] Bare-domain input still produces 4 URLs (no crash on missing path segment)
- [ ] No placeholder/TODO comments in new code

---

### Phase C: Backend — ATS-aware extraction prompt + Sonnet model switch

**Estimated time:** 30 minutes

**Files:**
- Modify: `backend/app/services/cv_parser.py`
- Modify: `backend/tests/test_cv_upload.py`

**Steps:**
1. Write failing test `test_parse_cv_uses_sonnet_with_ats_prompt` that monkeypatches `subprocess.run` to capture the cmd args; asserts `"--model"` is followed by `"claude-sonnet-4-6"` and that the system-prompt-file written to disk contains the ATS-only-skills rule string `"EXCLUDE: model/product names"`. Expected error: `AssertionError: 'claude-sonnet-4-6' not in cmd args` (because current code uses default haiku).
2. Run test, confirm it fails for the expected reason.
3. Modify `cv_parser.py`:
   - Replace `_EXTRACTION_SYSTEM_PROMPT` with a rewritten ATS-aware version. Required additions:
     - "Capture EVERY distinct work entry, project, award, and certification across all provided pages — pages are concatenated in the input."
     - "Each work entry MUST have employer, title, startDate (YYYY-MM), endDate (YYYY-MM or null for present)."
     - "highlights[].text MUST start with an action verb. Include quantified outcome (numbers, %, scale, before/after) when the source mentions it."
     - "skills MUST contain ONLY concrete technical skills (programming languages, frameworks, libraries, platforms, tools, protocols). EXCLUDE: model/product names (e.g., VEO, Seedance, Kling), vendor brands, abstract concepts (e.g., 'Multi-agent Architecture', 'Hierarchical Delegation', 'Parallel Processing')."
     - "If a section is empty in the source, return an empty array. DO NOT invent."
     - One-line examples for skill filtering (good vs reject).
   - In `parse_cv_to_json_resume`, pass `model="claude-sonnet-4-6"` into `extract_json_via_cli`.
   - Bump truncation from `raw_text[:50000]` to `raw_text[:120000]` (4 pages of markdown can comfortably exceed 50k).
4. Run tests, confirm `test_parse_cv_uses_sonnet_with_ats_prompt` and existing `test_parse_handles_fenced_json` both pass.
5. Commit: `feat(cv): switch CV parser to Sonnet 4.6 with ATS-aware prompt`

**Verification:**
- [ ] `pytest backend/tests/test_cv_upload.py -v` all pass (existing 6 + 1 new)
- [ ] System prompt contains skill-filtering rule + complete-extraction rule (grep test)
- [ ] `extract_json_via_cli` is called with `model="claude-sonnet-4-6"`
- [ ] Truncation lifted to 120000 chars
- [ ] No placeholder/TODO comments in new code

---

### Phase D: Backend — wire multi-URL into `/api/cv/master/import-url`

**Estimated time:** 25 minutes

**Files:**
- Modify: `backend/app/schemas/cv.py`
- Modify: `backend/app/api/cv.py`
- Modify: `backend/tests/test_cv_upload.py`

**Steps:**
1. Write failing test `test_import_url_multi_page_fetches_all_4_urls` that monkeypatches `scrape_multiple_pages` to capture the URL list it was called with; POSTs `{"url": "https://alisadikinma.com/en"}` to `/api/cv/master/import-url`; asserts the helper was called with exactly 4 derived URLs in order. Expected error: `AssertionError: scrape_multiple_pages was not called` (because endpoint still calls single-URL `fc.scrape`).
2. Run test, confirm it fails for the expected reason.
3. Modify `MasterCVImportURLRequest` in `schemas/cv.py`: add optional `urls: list[str] | None = None` field. Keep existing `url: str` for backwards compat.
4. Modify `import_master_from_url` in `api/cv.py`:
   - If `body.urls` is non-empty list, use those URLs directly.
   - Else call `derive_portfolio_urls(body.url)` to get 4 URLs.
   - Replace single `fc.scrape(...)` call with `markdown = scrape_multiple_pages(urls, db, wait_for_ms=8000)`.
   - Wrap in try/except `MultiScrapeError` → 502 with same actionable message.
   - Source-type label: stays `f"url:{domain}"` based on the FIRST URL in the list.
5. Run tests, confirm `test_import_url_multi_page_fetches_all_4_urls` passes plus existing endpoint tests in `test_cv_upload.py` still green.
6. Commit: `feat(cv): import-url scrapes 4 portfolio pages in parallel`

**Verification:**
- [ ] `pytest backend/tests/test_cv_upload.py -v` all pass
- [ ] Schema accepts both `{"url": "..."}` (single) and `{"urls": ["...", "..."]}` (multi) payloads
- [ ] `derive_portfolio_urls` is called only when `urls` is empty/missing
- [ ] No placeholder/TODO comments in new code

---

### Phase E: Frontend — multi-URL textarea input + advanced toggle

**Estimated time:** 30 minutes

| Phase | Code Deliverable | Design Deliverable | Verification |
|---|---|---|---|
| E | Textarea input + toggle in `MasterCvTab.tsx`, hook payload extension in `useCV.ts` | Layout: existing card, add small "Advanced: enter custom URLs" toggle below single URL input. When ON, swap `Input` → `Textarea` (rows=4) with placeholder showing 4 example URLs newline-separated. Reuse existing card spacing/colors (no new tokens). | Manual UI test + tsc check |

**Files:**
- Modify: `frontend/src/components/settings/MasterCvTab.tsx`
- Modify: `frontend/src/hooks/useCV.ts`
- Test: `frontend/src/__tests__/MasterCvTab.test.tsx` (new — only if existing test infra covers this component; otherwise rely on tsc + manual)

**Steps:**
1. Write failing test `it('sends urls array when advanced mode toggled and multi-line entered')` — uses Testing Library to toggle the switch, type 2 newline-separated URLs into the Textarea, click Import, assert the mocked mutation received `{urls: ["url1", "url2"]}`. Expected error: `Unable to find role 'switch' with name /advanced/i` (because component doesn't have the toggle yet).
2. Run test, confirm it fails for the expected reason.
3. Modify `useCV.ts`:
   - Update `useImportMasterCVFromURL` mutation `variables` type to `{ url?: string; urls?: string[] }`.
   - Forward both fields to `axios.post`.
4. Modify `MasterCvTab.tsx`:
   - Add local state `advancedMode: boolean` (default false).
   - Below current URL `Input` add a `<Switch>` (shadcn) labeled "Advanced — paste custom URLs (newline-separated)".
   - When ON: swap `Input` for `Textarea` rows={4} with placeholder containing 4 example URLs from `https://alisadikinma.com/en`.
   - On submit:
     - Advanced mode: split textarea value on `\n`, trim + filter empty, send `{ urls: [...] }`.
     - Default mode: send `{ url: <input> }` (current behavior).
5. Run frontend test (if added) + `npx tsc --noEmit` from `frontend/`.
6. Commit: `feat(cv): support multi-URL portfolio import in Master CV tab`

**Verification:**
- [ ] `npx tsc --noEmit` passes from `frontend/`
- [ ] Toggle switches Input ↔ Textarea visually (manual)
- [ ] Default mode payload unchanged (`{url: ...}`) — verified via React DevTools or test
- [ ] Advanced mode payload sends `{urls: [...]}` — verified
- [ ] No placeholder/TODO comments in new code

---

### Phase F: End-to-end smoke test + CLAUDE.md sync

**Estimated time:** 15 minutes

**Files:**
- Modify: `CLAUDE.md`

**Steps:**
1. Write a manual checklist test (no automated test — this is a real-data smoke):
   - Deploy the branch to VPS (push + auto-deploy).
   - In browser: Settings → CV → click Import URL → paste `https://alisadikinma.com/en` → toggle Advanced OFF → submit.
   - Wait for response. Expected: status 201, response shows `>= 4` work entries, `>= 5` projects, skills array contains technical-only items (no "VEO 3.1", "Seedance", "Kling AI", "Multi-agent Architecture", "Hierarchical Delegation", "Parallel Processing").
   - Compare against current baseline (4/5/42-noisy) — improvement expected on all three axes.
2. Run smoke checklist, capture before/after counts.
3. Update CLAUDE.md:
   - Add a one-line gotcha to "Backend / infra" section: "CV import-from-URL scrapes 4 portfolio pages in parallel (`derive_portfolio_urls`) and uses Sonnet 4.6 with ATS-aware prompt — see `app/services/multi_scraper.py` and `app/services/cv_parser.py`."
4. Commit: `docs(claude): document multi-page CV import + ATS prompt`

**Verification:**
- [ ] End-to-end flow on production returns CV with > 4 work entries AND > 5 projects AND skills filtered (technical-only)
- [ ] CLAUDE.md gotcha added
- [ ] Plan file checked in alongside code (this file)

---

## Execution Handoff

**Option 1: Execute in this session**
> Ready to start Phase A? I'll use gaspol-execute to implement with per-phase checkpoints.

**Option 2: Parallel execution**
> Phases A and B touch the same `multi_scraper.py` file — must run sequentially. Phase E (frontend) is independent of D (backend wiring) once D's schema is in place. Could parallelize D and E, but minimal time saved (~10 min). Recommend sequential.

**Option 3: Separate session**
> Save plan for a new session? The plan file at `docs/plans/2026-05-02-ats-friendly-cv-import.md` has everything needed.

## Out of Scope

- Portfolio_v2 changes (no `/api/public/profile.json` endpoint — that was Approach B from brainstorm; user picked A only)
- SSR/Nuxt migration of Portfolio_v2 (separate longer-term project)
- Resume PDF re-upload UX nudge
- Skills taxonomy normalization (e.g., "Python 3" → "Python") — manual edit covers this
- Multilingual CV extraction (English only for now)
