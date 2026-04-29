# JobHunter — Day-1 user guide

The single-admin onboarding walkthrough. Total time: ~30 minutes if your
master CV is already in JSON Resume shape; ~90 minutes if you're writing
the three variant summaries from scratch.

> All screenshots refer to the dev frontend at `http://localhost:3000`
> after `make dev-frontend`. Production is identical except for the
> hostname (`https://jobs.alisadikinma.com`).

---

## 0. Pre-flight

You'll need:

- The dev stack running (`make db-up`, `make dev-backend`, `make dev-frontend`).
- An admin login — credentials come from `ADMIN_EMAIL` / `ADMIN_PASSWORD`
  in `.env`. The password is hashed and seeded by `scripts/seed_admin.py`
  (also run automatically on container boot).
- Claude CLI on your `PATH` (`claude --version` works).
- A residential proxy URL if you plan to scrape LinkedIn / Indeed
  (LinkedIn datacenter IPs get a 999 captcha within minutes).
- An Apify API token if you plan to scrape Wellfound — free tier is
  enough for ~5 runs/month per account; the pool supports up to 5.

Sign in once at [/login](http://localhost:3000/login) before starting
the steps below.

---

## Step 1 — Add Apify accounts (5 min, optional)

Wellfound and the LinkedIn fallback both go through Apify. From
**Settings → Apify Pool**:

1. Click **Add account** and paste your Apify API token. Tokens are
   encrypted with `APIFY_FERNET_KEY` before being persisted.
2. Click **Test** — green checkmark confirms the token can list actors.
3. Repeat for up to 5 accounts to spread free-tier quota.

Skip this step entirely if you only want JobSpy + the API-first
scrapers (RemoteOK, HN Algolia, Arbeitnow, Adzuna, HiringCafe). Wellfound
will be silently disabled until at least one account is healthy.

---

## Step 2 — Seed / edit the master CV (10 min)

Your master CV is the source-of-truth that `/cv-tailor` rewrites per
job. From **CV → Master**:

1. The first time you land here you'll see an empty JSON template —
   either paste your existing JSON Resume content, or run
   `python backend/scripts/seed_master_cv.py` first to bootstrap from
   `docs/seed/master-cv.template.json`.
2. Fill out **all three** `summary_variants` keys
   (`vibe_coding`, `ai_automation`, `ai_video`) — `/cv-tailor` picks
   one per generated CV based on the job's `suggested_variant`. An
   empty value forces a `no_match` rejection.
3. Tag every `relevance_hint` on `work[]` and `projects[]` items with
   one of the three variant keys. The tailor uses these to pick which
   experience to surface for each job.
4. Click **Save** — version is bumped, the previous row is set
   `is_active=false` (no data is destroyed).

The right panel shows a live JSON-Resume validator. If the editor
flags red, the API will reject the save with a 422 — fix and resave.

---

## Step 3 — Publish portfolio assets (5 min)

The portfolio section is what `/cv-tailor` cherry-picks from when
adding a "Selected projects" block to the tailored CV. From
**Portfolio**:

1. The auditor scans `PORTFOLIO_SCAN_PATHS` (see `.env`) and creates
   draft assets for every directory with a `CLAUDE.md` file. Drafts
   are not visible to the tailor.
2. Review each draft, fill in the title / description / `tech_stack`
   / `relevance_hint` (same three variant keys), and click **Publish**.
   Skip drafts that don't represent shippable work — they stay as
   `status='draft'` and never enter the tailor's context.
3. Use **+ Add manual asset** for projects that don't live under a
   scanned path (e.g. paid client work hosted elsewhere).

Aim for 10–15 published assets covering all three variants. Fewer is
fine, but the tailor needs at least 2–3 hits per variant to write
distinctive CVs.

---

## Step 4 — Trigger the first scrape (2 min, then ~3 min wait)

From **Jobs → Configs** (or directly via the API):

1. Three configs are seeded by migration `004_seed_scrape_configs` —
   one per variant. Confirm the keywords look right (edit in
   **Settings → Scrape configs** if not).
2. From the **Jobs** page header, click **Run config #1** (or
   `make scrape-run CONFIG=1`).
3. The aggregator hits all 5 API-first sources concurrently, then
   JobSpy via residential proxy, then Wellfound via Apify if a healthy
   account is available. Expect 50–150 deduplicated jobs in the table
   within 2–3 minutes.

While the scrape runs, the **APScheduler** card on the dashboard
shows the next scheduled run. The default cron is every 3 hours per
config — adjust in `Settings → Scrape configs` if too noisy.

---

## Step 5 — Review high-score jobs (5 min)

After scraping, `/job-score` is auto-dispatched in batches of 25 to
score every new row.

1. Open **Dashboard** — the **Recent High-Score Jobs** table at the
   bottom shows every job ≥80, ranked. The bar chart shows scoring
   activity over the last 14 days.
2. Click any title to open the job detail panel. Read the
   `score_reasons` JSON — Claude tells you *why* it gave that score
   and which keywords it matched.
3. Click **Target** on any job you want to apply to. This creates an
   `Application` row with `status='targeting'` and adds a
   `created` activity to the timeline.

Targeted applications appear in the **Applications** kanban under
the **Targeting** column.

---

## Step 6 — Generate your first CV (3 min)

From the **Application detail** page:

1. Click **Generate CV**. The button stays disabled and a progress
   modal opens — the modal subscribes to
   `/ws/progress/{agent_job_id}` and shows live progress from the
   `/cv-tailor` skill running in subprocess.
2. When the bar hits 100%, you're auto-redirected to the
   **CV preview** page showing the tailored markdown side-by-side
   with the original master, plus an **ATS Score Card** (matched +
   missing keywords).
3. Click **Download DOCX** or **Download PDF** — the first download
   triggers Pandoc + LibreOffice rendering on the API container,
   subsequent downloads are cached at `cv.docx_path` / `cv.pdf_path`.

If `variant_used == 'no_match'`, the application is auto-marked
`rejected` with the rejection reason in `suggestions.rejected_reason` —
this is the tailor refusing to fake a fit.

---

## Step 7 — Send the first cold email (3 min)

From the same application detail:

1. Click **Generate Emails** → progress modal again. `/cold-email`
   produces three drafts: an `initial` plus two `follow_up_1` /
   `follow_up_2` variants gated on no-reply.
2. Open the initial draft. Edit the subject / body until it reads in
   your voice (the skill gets you ~80% there but voice is yours to
   add).
3. Copy the body into your real email client (Gmail / Fastmail / etc).
   The system intentionally does not send — too easy to spam.
4. Back on the application, click **Mark email sent** to update
   `email_sent_at`. The follow-up drafts auto-surface 5 and 10 days
   later in the dashboard if no reply timestamp is set.

---

## What runs unattended after Day 1

Once the master CV + portfolio + scrape configs are in place, the
system runs itself:

- **Every 3 hours** APScheduler triggers each active scrape config.
- **After each scrape**, `/job-score` auto-batches new rows.
- **Daily 3 AM** (post-MVP, see `Phase 2` of the plan): Portfolio_v2
  sync if the integration is enabled.

You only need to come back when you see a high-score job — review it,
target it, generate CV + email, send it. Estimated daily touch time
once the bootstrap is done: **15 minutes**.

---

## Troubleshooting first-run issues

See `CLAUDE.md` → **Debugging Checklist** for the full list. The
three most common Day-1 stumbles:

- **`/cv-tailor` immediately fails with "no master CV"** — you skipped
  Step 2 or saved an inactive version. Re-open `CV → Master`, click
  Save once.
- **Wellfound jobs never appear** — every Apify account is exhausted
  for the month. Add another in **Settings → Apify Pool** or wait
  for the calendar reset.
- **CV download returns 502** — Pandoc / LibreOffice missing from the
  API container. Confirm with `docker exec <api> pandoc --version`
  and `docker exec <api> soffice --version`. The Dockerfile installs
  both — rebuild without cache if you skipped a layer.
