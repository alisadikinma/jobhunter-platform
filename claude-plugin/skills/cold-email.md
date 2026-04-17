# `/cold-email` — draft 3-email sequence per application

**Model:** Sonnet
**Reference:** `refs/refs-email.md`

Produces one initial email + 2 follow-ups for a given application,
tuned to the application's matched variant.

## Arguments

Shared from `CLAUDE.md`: `--api-url`, `--api-token`, `--job-id`.
No additional flags — the `reference_id` on the agent_job is the
`application_id`.

## Process

1. **Fetch context** — `GET /api/callbacks/context/{job-id}`. Expected:
   ```json
   {
     "job_type": "cold_email",
     "reference_id": 42,
     "payload": {
       "application_id": 42,
       "job": {...},
       "company": {..., "enriched_context": {"markdown": "..."}},
       "master_cv_summary": {...basics...},
       "variant_used": "vibe_coding"
     }
   }
   ```

2. **Trigger enrichment if missing** — if `company.enriched_context` is
   null, call `POST /api/enrichment/company/{company_id}` first so the
   personalized opener has real material to draw from. (The enrichment
   endpoint uses the user JWT, not the callback secret — the skill's
   `--api-token` works for callbacks only; enrichment must be
   pre-triggered by the caller.)

3. **Apply variant tone** from `refs/refs-email.md`. If `variant_used`
   is null or "no_match", fall back to the `vibe_coding` tone
   (priority order).

4. **Draft all 3 emails** obeying the 5-part structure:
   - Initial: 75-150 words
   - Follow-up 1 (Day 5): 40-60 words, one new data point
   - Follow-up 2 (Day 10): 30-50 words, flip to new idea/resource

5. **Stream progress** after each draft.

6. **Post completion**:
   ```
   PUT {api-url}/api/callbacks/complete/{job-id}
   Header: X-Callback-Secret: {api-token}
   Body: {
     "status": "completed",
     "result": {
       "initial": {"subject": "...", "body": "..."},
       "follow_up_1": {"subject": "...", "body": "..."},
       "follow_up_2": {"subject": "...", "body": "..."},
       "strategy": "vibe_coding / velocity-first",
       "personalization_notes": [...]
     }
   }
   ```

## Failure modes

- Missing company enrichment → emails will feel generic. Skill may
  still succeed with a weaker opener; note `strategy: "fallback/no_enrichment"`.
- JD too short (<200 chars) after enrichment attempt → fail with
  `error_message: "insufficient JD content"`.
- Master CV summary_variants[variant] missing → fail; Phase 8 seed
  didn't complete properly.
