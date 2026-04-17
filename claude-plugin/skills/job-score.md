# `/job-score` — batch score scraped jobs

**Model:** Sonnet
**Reference:** `refs/refs-scoring.md`

Scores up to ~25 recently-scraped, unscored jobs in a single invocation
and returns scores + 3-variant classification.

## Arguments

Shared (from CLAUDE.md): `--api-url`, `--api-token`, `--job-id`.

## Process

1. GET `{api-url}/api/callbacks/context/{job-id}` to fetch:
   - `payload.jobs` — list of up to 25 unscored jobs
   - `payload.master_cv_summary` — CV basics (name, summary, skills)

2. If any job has `len(description) < 500`, first call the enrichment
   endpoint and re-fetch context:
   ```
   POST {api-url}/api/enrichment/job/{job_id}
   Header: Authorization: Bearer <admin JWT>  -- NOTE: enrichment uses
     the standard user auth, not the callback secret. Phase 7 does not
     wire this; skills invoked pre-enrichment should assume truncated
     JDs and score with the data provided.
   ```

3. Apply the rubric from `refs/refs-scoring.md`:
   - Compute each dimension score 0-weight
   - Sum to `relevance_score` 0-100
   - Classify variant against the 3 confidence thresholds
   - Extract top 5-10 `match_keywords`

4. Stream progress after each job via
   `PUT /api/callbacks/progress/{job-id}`.

5. POST completion:
   ```
   PUT {api-url}/api/callbacks/complete/{job-id}
   Header: X-Callback-Secret: {api-token}
   Body: {"status": "completed", "result": {"scores": [...]}}
   ```

## Output shape

See `refs/refs-scoring.md` § Output shape.

## Failure modes

- Context fetch 401 → abort with `status: failed`
- Individual job scoring error → include the job with
  `relevance_score: 0` and put the error in `score_reasons.error`
- Total failure of all jobs → `status: failed` with
  `error_message` describing the cause

## Max tokens

Sonnet ~200k input is more than enough for 25 jobs + CV summary.
No chunking needed at this batch size.
