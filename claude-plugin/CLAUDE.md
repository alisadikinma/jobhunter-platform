# JobHunter Plugin — Claude CLI Skills

Plugin that provides skills invoked by the FastAPI backend via
`subprocess.Popen([CLAUDE_PATH, --plugin-path, <this dir>, <skill>, ...])`.

## Conventions

### Shared arguments

Every skill in this plugin receives three common flags:

| Flag | Meaning |
|------|---------|
| `--api-url` | Base URL of the JobHunter FastAPI instance (no trailing slash) |
| `--api-token` | Shared secret for `X-Callback-Secret` header on all callbacks |
| `--job-id` | The `agent_jobs.id` row tracking this invocation |

Additional skill-specific flags are documented per-skill.

### Callback contract

Skills MUST call back to the backend — we don't parse stdout, progress
comes via HTTP.

1. Fetch context at start:
   ```
   GET {api-url}/api/callbacks/context/{job-id}
   Header: X-Callback-Secret: {api-token}
   ```

2. Stream progress while working:
   ```
   PUT {api-url}/api/callbacks/progress/{job-id}
   Header: X-Callback-Secret: {api-token}
   Body: {"progress_pct": 40, "current_step": "scoring batch 2/5", "log_message": "..."}
   ```

3. Submit final result:
   ```
   PUT {api-url}/api/callbacks/complete/{job-id}
   Header: X-Callback-Secret: {api-token}
   Body: {"status": "completed", "result": { ... skill-specific shape ... }}
   ```

On failure: `{"status": "failed", "error_message": "..."}`.

### Model choice

- **Sonnet** for classification/scoring (job_score, cold_email) —
  cheap, fast, good enough.
- **Opus** for craft-sensitive generation (cv_tailor) — rewriting human
  prose with nuance.

## Skills

| Skill | Model | Purpose |
|-------|-------|---------|
| `/job-score` | Sonnet | Score a batch of scraped jobs against master CV + 3-variant rubric |
| `/cv-tailor` | Opus | Generate a variant-specific tailored CV for an application |
| `/cold-email` | Sonnet | Draft initial + 2 follow-up cold emails per application |

## Refs

- `refs/refs-scoring.md` — 3-variant classifier rubric + scoring weights
- `refs/refs-cv.md` — variant-preset bullet ranking + ATS rules (Phase 10)
- `refs/refs-email.md` — cold email structure + follow-up cadence (Phase 13)
