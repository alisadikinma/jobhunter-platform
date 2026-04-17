# `/cv-tailor` — tailor master CV for one application

**Model:** Opus (craft-sensitive rewriting)
**Reference:** `refs/refs-cv.md`

## Arguments

Shared from `CLAUDE.md`: `--api-url`, `--api-token`, `--job-id`.
No additional flags — the `reference_id` on the agent_job is the
`application_id` to tailor for.

## Process

1. **Fetch context** — `GET /api/callbacks/context/{job-id}` with the
   shared secret. Expected payload:
   ```json
   {
     "job_type": "cv_tailor",
     "reference_id": 42,
     "payload": {
       "application_id": 42,
       "master_cv": {...JSON Resume...},
       "job": {...ScrapedJob fields...},
       "portfolio_assets": [...published assets...],
       "company": {...enriched context if available...}
     }
   }
   ```

2. **Classify variant** — score the JD against the 3 variant signals
   from `refs-scoring.md`. If the top confidence is below the variant's
   threshold (see `refs-cv.md`), emit
   `{variant_used: "no_match", rejected_keywords_reason: "..."}` and
   return `status: failed`.

3. **Load the variant preset** from `refs-cv.md`:
   - Tagline for the header
   - Summary source (`summary_variants[variant]`)
   - Tag priority list
   - Skills section order
   - Portfolio filter rules

4. **Select summary** — use `basics.summary_variants[variant]` as-is,
   OR generate a fresh 2-3 sentence opener if the preset's rewrite
   instructions say so.

5. **Rank & pick bullets** — apply the bullet-ranking algorithm
   (`refs-cv.md` § Bullet ranking) per work entry. Keep top 3-5; ensure
   at least one has a quantified metric if one exists in the source.

6. **Select portfolio** — filter assets by `relevance_hint ∋ variant`,
   sort by `display_priority desc`, cap at 4. Backfill per preset rules
   if fewer than 4 match.

7. **Reorder skills** per variant preset.

8. **Apply ATS rules** — strip any accidental tables/icons, ensure
   section headers are standard names, verify keyword coverage (aim for
   70-80% of JD keywords present after rewrite).

9. **Emit markdown** — the full CV as a single markdown string, plus a
   structured `tailored_json` mirroring the JSON Resume shape.

10. **Stream progress** via `PUT /api/callbacks/progress/{job-id}`
    after each phase (classify, rank, select, emit).

11. **Post completion**:
    ```
    PUT {api-url}/api/callbacks/complete/{job-id}
    Header: X-Callback-Secret: {api-token}
    Body: {
      "status": "completed",
      "result": {
        "tailored_markdown": "...",
        "tailored_json": {...},
        "keyword_matches": [...],
        "missing_keywords": [...],
        "variant_used": "vibe_coding",
        "confidence": 0.87,
        "selected_portfolio_ids": [...]
      }
    }
    ```

## Failure modes

- Context 404/401 → `status: failed`, `error_message: "context fetch failed"`
- No variant passes threshold → `status: completed` with
  `variant_used: "no_match"` + `rejected_keywords_reason`
- Master CV missing `summary_variants` → `status: failed`,
  explain that Phase 8 seed didn't complete
