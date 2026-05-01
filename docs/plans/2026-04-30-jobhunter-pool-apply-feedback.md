# LinkedIn-style Easy Apply — North Star Redesign

**Date:** 2026-04-30
**Status:** Brainstorm — needs final user confirmation on send mechanism, then ready for `gaspol-plan`.
**Source:** User feedback after seeing current 8-menu sidebar — "tiru UI/UX LinkedIn, segampang pencet easy apply".

## North Star

> **"Browse jobs → click Easy Apply → review draft → click Send. Done."**

Setiap perubahan dievaluasi dari satu lensa: **apakah ini mempercepat path "lihat job → email terkirim"?** Kalau jawabannya tidak, di-defer atau dihilangkan.

---

## Sidebar simplification — 8 items → 3 items

### Current (overengineered for admin tasks)
```
Dashboard · Jobs · Applications · CV · Emails · Portfolio · Credentials · Settings
```
8 menu items. CV/Emails/Portfolio/Credentials are admin pages cluttering the main nav.

### Proposed (LinkedIn-tier simplicity)
```
Jobs · Applications · Settings
```

3 menu items. Itu saja. Itu adalah yang user butuhkan.

| Menu | Purpose |
|---|---|
| **Jobs** | Browse + filter + Easy Apply CTA (the main UX) |
| **Applications** | Kanban tracker — what you've applied to + status |
| **Settings** | Tabs: Master CV, Portfolio, Credentials, Schedules |

Apa yang hilang vs current:
- ❌ `Dashboard` — user belum pernah pakai stats; di-merge ke `/jobs` header (count + filter pills sudah cukup)
- ❌ `CV` (master CV editor) — pindah ke `/settings?tab=cv`
- ❌ `Emails` (draft list standalone) — pindah ke `/applications/[id]` (drafts tampil per-application, bukan global list)
- ❌ `Portfolio` — pindah ke `/settings?tab=portfolio`
- ❌ `Credentials` — pindah ke `/settings?tab=credentials`

Generated artifacts (tailored CV per app, cold email drafts per app) tetap bisa diakses tapi kontekstual — **dari application detail, bukan menu sendiri**.

---

## Easy Apply flow — the only feature that matters

### UX (mirror LinkedIn)

**Job detail page `/jobs/[id]`:**
```
┌─────────────────────────────────────────────────┐
│ [Logo] Crossing Hurdles — verified              │
│ Product Manager · Remote · $40-80/hr · 5d ago   │
│                                                  │
│ [⚡ Easy Apply]  [☆ Save]  [✕ Not relevant]     │
│                                                  │
│ ─── About the job ───                           │
│ Position: Product Manager                        │
│ Type: Contractor (Part-time)                    │
│ ...                                              │
└─────────────────────────────────────────────────┘
```

### One-click orchestration (behind the Easy Apply button)

Clicking **⚡ Easy Apply** triggers a single backend orchestration that:

1. **Auto-creates `application` row** (status: `targeting`)
2. **Spawns Claude CLI subprocess** dengan skill `cv-tailor`:
   - Reads master CV + JD + portfolio assets
   - Opus rewrites summary + ranks experience bullets per JD
   - Renders DOCX + PDF via Pandoc
3. **Spawns Claude CLI subprocess** dengan skill `cold-email`:
   - Reads tailored CV + JD + company context
   - Sonnet drafts initial email + 2 follow-ups
   - Appends to IMAP `INBOX.Drafts`
4. **Returns to UI:** modal with progress (WebSocket via existing `ProgressModal`), then:
   ```
   ✅ Draft ready
   ┌──────────────────────────────────────┐
   │ Subject: Excited about the PM role…  │
   │ ─────────────────────────────────────│
   │ [Email body — fully editable]        │
   │ ─────────────────────────────────────│
   │ Attachments: ali_sadikin_PM_v2.pdf   │
   └──────────────────────────────────────┘

   [📤 Send now]  [📝 Open in mail client]  [🗑 Discard]
   ```

### Send mechanism — TWO options for user choice

User said "**Saya tinggal pencet Sent button semua beres**". Ada dua interpretasi:

#### Option A: In-app Send Now button (auto SMTP)
- Tombol **Send now** di modal langsung trigger SMTP send via mailbox config (`smtp.hostinger.com:465`)
- Email keluar dari `aiagent@alisadikinma.com` ke recipient
- Application status auto-update ke `applied`
- **Tidak ada review di mail client** — fully autonomous
- **Risiko:** kalau Claude bikin email yang awkward atau salah info, sudah terkirim

#### Option B: Open in mail client (review-first)
- Tombol **Open in mail client** buka link ke Hostinger webmail / Outlook
- User lihat draft di IMAP Drafts, review, click Send dari sana
- Application status update ke `applied` saat user manual mark via webhook (atau polling IMAP `\Sent` flag)
- **Lebih lambat 30 detik** untuk review tapi safer

#### Option C: Hybrid (recommended)
- Modal show **inline preview** (subject + body editable in JobHunter UI)
- Tombol **Send now** di modal → SMTP send langsung
- Tombol **Save draft** → IMAP append untuk review nanti
- User pilih per-job: cepat atau hati-hati

---

## Wave structure (revised — Easy Apply is Wave 1 now)

### Wave 1: LinkedIn Easy Apply flow (PRIMARY, ~2-3 hari kerja)

1. **Sidebar reduction** 8 → 3 items
   - Hapus menu CV, Emails, Portfolio, Credentials, Dashboard dari nav
   - Buat `/settings` jadi tabbed page (Master CV / Portfolio / Credentials / Schedules)
2. **Job detail redesign** — LinkedIn-clone hero + sidebar
   - Company logo (use favicon API atau Firecrawl-enriched)
   - Hero with company name, role, salary, location, posted date
   - **⚡ Easy Apply** primary CTA + **☆ Save** secondary + **✕ Not relevant** ghost
3. **Easy Apply orchestration endpoint**
   - `POST /api/applications/easy-apply` — body `{job_id}`
   - Creates application + spawns CV tailor + cold email in parallel
   - Returns `{application_id, agent_jobs: [cv_id, email_id]}`
4. **Easy Apply modal** — WebSocket progress + inline draft preview + Send mechanism (per Option C)

### Wave 2: Sources analytics + Feedback loop (DEFERRED)

After Easy Apply ships and user confirms it works, then iterate:
- ✕ Not relevant button → hides job + flag as irrelevant + feeds title_filter learning
- Source analytics: per-source job count + relevance % + tech badge
- Cron status visibility (next-run countdown + per-source breakdown)

### Wave 3: Quick wins (LOWEST priority)

Yang sebelumnya saya labeli "Wave 1 quick wins" — di-defer karena tidak menggerakkan north star:
- Pool sequential failover (sudah works dengan round-robin, pure cosmetic improvement)
- Firecrawl table column rename (cosmetic)

User tidak akan notice perbedaan ini saat browsing job — defer.

---

## Decision: Send mechanism — IN-APP REVIEW + SEND

User confirmed: **"saya mau manual review dulu baru email boleh kirim"**.

Final flow:
1. Click ⚡ Easy Apply
2. Modal shows progress (WebSocket — CV tailor + cold email running in parallel)
3. When ready, modal switches to **review mode**:
   ```
   ┌────────────────────────────────────────────┐
   │ Tailored CV ready                          │
   │ 📎 ali_sadikin_PM_crossing-hurdles.pdf    │
   │    [Preview] [Download]                    │
   ├────────────────────────────────────────────┤
   │ Subject:  [editable input]                 │
   │ ──────────────────────────────────────────│
   │ Body:                                      │
   │ ┌────────────────────────────────────────┐ │
   │ │ Hi <hiring_manager>,                   │ │
   │ │                                        │ │
   │ │ I'm reaching out about your Product…   │ │
   │ │ [fully editable textarea]              │ │
   │ └────────────────────────────────────────┘ │
   │                                            │
   │ Follow-ups (auto-scheduled):               │
   │ - Day 5: [preview]                         │
   │ - Day 10: [preview]                        │
   │                                            │
   │ [📤 Send now]  [💾 Save draft]  [✕ Cancel]│
   └────────────────────────────────────────────┘
   ```
4. User edits if needed, clicks **📤 Send now**
5. SMTP send via existing `mailer_service.send()` → application status → `applied`
6. Follow-ups auto-scheduled at +5d / +10d (cron-driven, already exists in scheduler)

**Why not auto-send:** Claude-generated email could have wrong details (typo'd company name, misquoted JD) — user wants final review.

**Why not draft-only-for-mail-client:** roundtrip ke webmail tambah 30 detik per-job + breaks single-tab flow + user kerja di JobHunter, bukan di mail client.

Modal review tab adalah review surface — fastest path while keeping safety.

---

## Data Integration Map

| Component | Data Source | Existing? | Notes |
|---|---|---|---|
| Sidebar reduction | `Sidebar.tsx` (frontend layout) | ✅ | Just remove items + add Settings tabs router |
| Job detail hero | `companies.logo_url` | ⚠️ | Needs Firecrawl enrichment to populate; fallback to favicon API |
| Job detail company name | `scraped_jobs.company_name` (existing) | ✅ | Already populated |
| Easy Apply CTA orchestration | `cv-tailor` + `cold-email` skills | ✅ | Already in plugin, spawned via `claude_service` |
| Inline email preview | `email_drafts.subject`/`body` | ✅ | Already saved per application |
| In-app Send Now | `mailer_service.send()` | ✅ | Already implemented |
| Open in mail client | Hostinger webmail URL | ✅ | Just a `<a href>` |
| Not-relevant flag | new column `scraped_jobs.user_irrelevant` | ❌ | New migration needed (small) |

**No major schema changes for Wave 1.** Easy Apply orchestration uses existing services/skills.

---

## Acceptance criteria (Wave 1)

- [ ] Sidebar shows only 3 items: Jobs / Applications / Settings
- [ ] /settings has tabs: Master CV / Portfolio / Credentials / Schedules
- [ ] /jobs/[id] hero shows company name + logo + role + salary + location
- [ ] Single ⚡ Easy Apply button kicks off CV tailor + cold email in one go
- [ ] Modal shows inline editable draft preview (subject + body)
- [ ] Send mechanism per user's choice (A/B/C)
- [ ] Application auto-created with status="applied" (after send) or "targeting" (after draft only)
- [ ] User flow: 1 click on Easy Apply → 1 click on Send = email out

---

## Phase 4 — Feasibility

**All building blocks already exist:**
- `cv-tailor` skill — works, ships DOCX/PDF
- `cold-email` skill — works, IMAP draft append
- `ProgressModal` + WebSocket `/ws/progress/{job_id}` — works
- `mailer_service.send()` — works (SMTPS direct)
- Application + activities tables — exist

**What's NEW:**
- Orchestration endpoint that spawns BOTH skills sequentially/parallel and aggregates result
- Sidebar refactor + Settings tabbed page
- Job detail redesign with hero
- Inline editable email preview component (editable textarea wired to `email_drafts.body`)

**No placeholders required.** Real integrations only.

---

## Implementation order (concrete)

Saya eksekusi dalam 5 PR berurutan agar tiap step bisa di-deploy + test sebelum yang berikut:

### PR 1 — Sidebar reduction & Settings tabs (~1 jam)
- Edit `frontend/src/components/Sidebar.tsx` (atau equivalent layout) → 8 → 3 items
- Refactor `/settings` jadi tabbed: `?tab=cv|portfolio|credentials|schedules`
- Pindah konten dari `/cv`, `/portfolio`, `/settings/credentials` jadi tab content
- Hapus pages standalone (`/cv`, `/portfolio`, `/emails`, `/settings/credentials`)
- Add redirects dari old paths ke new tabs (kalau ada bookmark)
- **Deploy + verify** sidebar berkurang + settings tabs work

### PR 2 — Job detail LinkedIn-clone hero (~1.5 jam)
- Redesign `/jobs/[id]/page.tsx`:
  - Hero: company logo + name + role + meta chips (salary, location, posted)
  - Score sidebar: per-variant breakdown
  - Description with `prose-jh` typography
  - 3 buttons: ⚡ Easy Apply / ☆ Save / ✕ Not relevant
- Company logo: try favicon API (`https://www.google.com/s2/favicons?domain=X&sz=64`) sebagai fallback bila `companies.logo_url` kosong
- **Deploy + verify** UI baru bagus

### PR 3 — Easy Apply orchestration backend (~2 jam)
- New endpoint `POST /api/applications/easy-apply` body `{job_id}`
- Logic:
  1. `application = create_application(job_id, user)` → `status="targeting"`
  2. Spawn `cv_tailor_job = claude_service.spawn(skill="cv-tailor", application_id)`
  3. Spawn `email_job = claude_service.spawn(skill="cold-email", application_id)`
  4. Return `{application_id, cv_agent_job_id, email_agent_job_id, generated_cv_id}`
- Existing `cv-tailor` + `cold-email` skills udah handle callback ke FastAPI (confirmed di plugin)
- **Deploy + verify** endpoint via curl

### PR 4 — Easy Apply review modal (~2.5 jam)
- New component `EasyApplyModal` di `frontend/src/components/`
- WebSocket progress UI (reuse `ProgressModal` logic untuk dual job)
- Setelah BOTH jobs done:
  - Fetch tailored CV download link
  - Fetch email drafts (initial + 2 follow-ups)
  - Render review surface (subject + body editable, attachments info)
- Wire **📤 Send now** button → `POST /api/emails/{id}/send`
- Wire **💾 Save draft** → `POST /api/emails/{id}/append-imap` (existing IMAP append)
- After send: redirect to `/applications/{id}` dengan timeline activity tampil
- **Deploy + verify** end-to-end flow: click Easy Apply on a job → wait → review → send → email actually arrived

### PR 5 — Polish + edge cases (~1 jam)
- Empty states (no master CV — block Easy Apply with hint)
- Error states (Claude CLI fails — show error + retry)
- Cancel mid-progress (kill agent_jobs)
- Follow-up auto-scheduling (verify scheduler picks up after `email_sent_at`)
- ✕ Not relevant button → simple `PATCH /api/jobs/{id}` `{user_irrelevant: true}` + hide from list (full feedback loop di Wave 2)

**Total estimate:** ~8 jam fokus = 1 hari kerja.

## Next action

Saya invoke `gaspol-plan` untuk turn this into formal step-by-step plan dengan task breakdown, atau langsung start PR 1?

---

## Implementation Plan

> **For Claude:** REQUIRED SKILL: Use `gaspol-execute` to implement this plan.
> **CRITICAL:** This plan specifies real integrations. During execution, NEVER substitute placeholders for real data sources without explicit user approval. If a data source doesn't exist yet (only `scraped_jobs.user_irrelevant` column for PR 5 + `POST /api/emails/{id}/send` endpoint for PR 4), STOP and ask before stubbing.

### Goal

Ship a LinkedIn-style "Easy Apply" flow that compresses **browse → tailored CV + ATS-clean → email draft → review → SMTP send** into a single button click + one review modal. Sidebar reduced from 8 menu items to 3. All other admin pages move to tabbed Settings.

### Architecture Context (from CLAUDE.md + verified file reads)

| Concern | Existing | Path |
|---|---|---|
| Sidebar (single component, used by `(authed)` layout) | ✅ | [frontend/src/components/shared/Sidebar.tsx](../../frontend/src/components/shared/Sidebar.tsx) |
| Progress modal (WebSocket-driven) | ✅ | [frontend/src/components/shared/ProgressModal.tsx](../../frontend/src/components/shared/ProgressModal.tsx) |
| `useProgress(agent_job_id)` hook | ✅ | [frontend/src/hooks/useProgress.ts](../../frontend/src/hooks/useProgress.ts) |
| CV gen (spawns Claude CLI `cv-tailor`) | ✅ | [backend/app/services/cv_generator.py](../../backend/app/services/cv_generator.py) — `generate_cv(db, app_id) → (GeneratedCV, agent_job_id)` |
| Email gen (spawns Claude CLI `cold-email`) | ✅ | [backend/app/services/email_generator.py](../../backend/app/services/email_generator.py) — `generate_emails(db, app_id) → agent_job_id` |
| ATS rules baked into cv-tailor | ✅ | [`refs/refs-cv.md` ATS rules section](D:/Projects/claude-plugin/jobhunter-plugin/refs/refs-cv.md) — single column, std headers, 70-80% keyword overlap |
| SMTP send (mailer_service.send) | ✅ | [backend/app/services/mailer_service.py:180-195](../../backend/app/services/mailer_service.py#L180-L195) |
| Application + activity log + status transition | ✅ | [backend/app/services/application_service.py](../../backend/app/services/application_service.py) — `log_activity`, `transition_status` |
| `email_drafts.recipient_email` / `recipient_name` | ✅ | [backend/app/models/email_draft.py](../../backend/app/models/email_draft.py) |
| Existing `POST /api/emails/{id}/sent` (mark only, no SMTP) | ✅ | [backend/app/api/emails.py:120-133](../../backend/app/api/emails.py#L120-L133) |

### Tech Stack

- **Frontend:** Next.js 15 App Router, TanStack Query 5, Tailwind 3 (NOT v4), Lucide icons
- **Backend:** FastAPI 0.115, SQLAlchemy 2.0 sync, PyJWT, APScheduler in-process
- **Plugin invocations:** subprocess.Popen of Claude CLI v2 with `--plugin-dir` + `--api-token <CALLBACK_SECRET>`
- **Migrations:** Alembic head currently at `012_firecrawl_credits` (pre-existing)

### Data Integration Map

| Feature | Data Source | Hook/API | Exists? | Action |
|---------|-----------|----------|---------|--------|
| Sidebar nav (3 items) | hardcoded `NAV` array | `<Sidebar />` | ✅ | Trim 8 → 3 entries |
| Settings tab routing | `useSearchParams().get("tab")` | shadcn Tabs or custom | ✅ | Add `?tab=` query state |
| Master CV editor (now in Settings tab) | `/api/cv/master` | `useMasterCV()` | ✅ | Move existing `/cv` page content |
| Portfolio editor (now in Settings tab) | `/api/portfolio` | `usePortfolio()` | ✅ | Move existing `/portfolio` page content |
| Credentials editor (now in Settings tab) | mailbox + apify + firecrawl | existing hooks | ✅ | Move existing `/settings/credentials` page content |
| Schedules tab | `/api/scheduler/status` + scrape configs | `useScrapeConfigs()` + new `useSchedulerStatus()` | ✅ existing endpoint | Reuse existing settings page content (just rename to "Schedules" tab) |
| Job detail company logo | `companies.logo_url` OR favicon API | `useJob(id)` | ⚠️ may be empty | Fallback chain: companies.logo_url → `https://www.google.com/s2/favicons?domain=<host>&sz=64` |
| Easy Apply CTA | new `POST /api/applications/easy-apply` | new `useEasyApply()` mutation | ❌ | Create new endpoint + hook |
| Easy Apply modal progress | `agent_jobs` (CV + email) | `useProgress(cv_id)` + `useProgress(email_id)` | ✅ | Use existing hook twice |
| Email draft preview/edit | `/api/emails?application_id=X` | `useEmails(app_id)` | ✅ | Existing list endpoint |
| Inline edit subject/body | `PUT /api/emails/{id}` | new `useUpdateEmail()` | ⚠️ endpoint exists, no hook | Create hook wrapper |
| **In-app SMTP send** | `mailer_service.send()` | new `POST /api/emails/{id}/send` | ❌ | **Create new endpoint** that actually invokes SMTP (existing `/sent` only marks flag) |
| ✕ Not relevant flag | `scraped_jobs.user_irrelevant: bool` | new `PATCH /api/jobs/{id}` field | ❌ migration needed | Migration 013 + extend existing PATCH route |

**3 new things only:** `POST /api/applications/easy-apply`, `POST /api/emails/{id}/send`, `scraped_jobs.user_irrelevant` migration. Everything else is glue + UI.

---

### Phase 1: Sidebar 8→3 + Settings tabs (~60 min)

**Files:**
- Modify: [frontend/src/components/shared/Sidebar.tsx](../../frontend/src/components/shared/Sidebar.tsx) — trim NAV to 3 items
- Modify: [frontend/src/app/(authed)/settings/page.tsx](../../frontend/src/app/(authed)/settings/page.tsx) — add tabs router (CV / Portfolio / Credentials / Schedules)
- Move content: [frontend/src/app/(authed)/cv/page.tsx](../../frontend/src/app/(authed)/cv/page.tsx) → `settings/page.tsx` MasterCvTab
- Move content: [frontend/src/app/(authed)/portfolio/page.tsx](../../frontend/src/app/(authed)/portfolio/page.tsx) → `settings/page.tsx` PortfolioTab
- Move content: [frontend/src/app/(authed)/settings/credentials/page.tsx](../../frontend/src/app/(authed)/settings/credentials/page.tsx) → `settings/page.tsx` CredentialsTab (full file)
- Keep: existing `settings/page.tsx` content becomes SchedulesTab
- Delete-via-redirect: `/cv`, `/portfolio`, `/emails`, `/dashboard`, `/settings/credentials` all redirect to canonical destinations
- Test: [frontend/src/__tests__/Sidebar.test.tsx](../../frontend/src/__tests__/Sidebar.test.tsx) (new)

**Steps:**
1. Write failing test asserting Sidebar renders exactly 3 nav links: Jobs / Applications / Settings. Expected error: `Found 8 links, expected 3`.
2. Run test, confirm failure.
3. Trim `Sidebar.tsx` NAV array to `[{ jobs }, { applications }, { settings }]`. Default redirect for "/" → "/jobs" (was /dashboard).
4. Run test, confirm pass.
5. Add `useSearchParams` to `settings/page.tsx`. Read `?tab=cv|portfolio|credentials|schedules` (default `schedules`).
6. Render `<Tabs>` with 4 panels. Each panel imports the moved component.
7. Move `cv/page.tsx` body → `MasterCvTab` component inside `settings/page.tsx`.
8. Move `portfolio/page.tsx` body → `PortfolioTab` component.
9. Move `settings/credentials/page.tsx` body → `CredentialsTab` component (this is biggest — 800+ lines).
10. Take existing `settings/page.tsx` scrape-config content → `SchedulesTab` component.
11. Add `redirect()` shims at old paths: `cv/page.tsx`, `portfolio/page.tsx`, `dashboard/page.tsx`, `emails/page.tsx`, `settings/credentials/page.tsx` → `redirect("/settings?tab=...")`.
12. Run `npm run build` to verify no Next.js routing errors.
13. Run `tsc --noEmit`.
14. Commit: `refactor(nav): collapse sidebar 8→3, settings tabbed`.

**Risk flag:**
- Bookmarks/external links to `/cv`, `/portfolio` must keep working → redirect shims, not 404s.
- The CredentialsTab is huge (~800 lines including pool tables); during the move, **don't refactor inline** — copy verbatim, then iterate later.
- Tabs state must be URL-driven (not local state) so deep links work: `https://jobs.alisadikinma.com/settings?tab=credentials`.

**Verification:**
- [ ] `tsc --noEmit` passes
- [ ] Sidebar renders 3 items; logo "JobHunter" links to `/jobs`
- [ ] `/settings` defaults to `?tab=schedules`
- [ ] `/cv`, `/portfolio`, `/dashboard`, `/emails` redirect to `/settings?tab=...`
- [ ] All previous functionality (scrape config save, master CV save, portfolio audit, mailbox test, apify pool, firecrawl pool) still works after migration
- [ ] No placeholder/TODO comments in new code

---

### Phase 2: Job detail LinkedIn-clone hero (~90 min)

**Files:**
- Modify: [frontend/src/app/(authed)/jobs/[id]/page.tsx](../../frontend/src/app/(authed)/jobs/[id]/page.tsx) — full rewrite of layout
- Create: [frontend/src/components/shared/CompanyLogo.tsx](../../frontend/src/components/shared/CompanyLogo.tsx) — favicon-fallback component
- Test: [frontend/src/__tests__/CompanyLogo.test.tsx](../../frontend/src/__tests__/CompanyLogo.test.tsx) (new)

**Steps:**
1. Write failing test: CompanyLogo renders `<img src={logo_url}>` when `logo_url` provided; falls back to `https://www.google.com/s2/favicons?domain=...&sz=64` when only `domain` provided; renders building icon when both null. Expected error: `ReferenceError: CompanyLogo is not defined`.
2. Run test, confirm failure.
3. Implement CompanyLogo with prop fallback chain. No `next/image` — use `<img>` with `loading="lazy"` (favicon API is small).
4. Run test, confirm pass.
5. Rewrite `jobs/[id]/page.tsx` with hero layout:
   - Top row: CompanyLogo (64px) + Company name (xl bold) + verified badge if `companies.is_verified`
   - Title row: Job title (2xl) + meta chips (salary, location, posted ago, source badge)
   - Action row: 3 buttons — `⚡ Easy Apply` primary / `☆ Save` ghost / `✕ Not relevant` ghost-red
   - 2-col grid: description (2/3) + sidebar (1/3 with score breakdown per variant)
   - Use `prose-jh` utility for description typography
6. Wire `☆ Save` to existing `POST /api/jobs/{id}/favorite`.
7. Stub `⚡ Easy Apply` button (handler = no-op alert "next phase wires this") — don't implement orchestration yet.
8. Stub `✕ Not relevant` button (no-op alert) — wired in Phase 5.
9. Run `npm run build`.
10. Manual browser test: visit `/jobs/113` (the job from user's screenshot) — verify company name appears, layout matches mockup.
11. Commit: `feat(jobs): LinkedIn-style detail hero with company logo`.

**Risk flag:**
- `companies.logo_url` likely empty for most jobs — favicon fallback MUST work; verify with a real domain like `crossinghurdles.com`.
- Don't make Easy Apply a real flow yet — just visual button. Phase 3 wires backend.

**Verification:**
- [ ] `tsc --noEmit` passes
- [ ] CompanyLogo test passes (3 cases: explicit URL, domain-only, both null)
- [ ] `/jobs/113` shows company name from `scraped_jobs.company_name`
- [ ] Easy Apply button visible but is a stub (no orchestration yet)
- [ ] No placeholder comments in production code (stub handlers OK in this phase, removed Phase 3)

---

### Phase 3: Easy Apply orchestration backend (~120 min)

**Files:**
- Modify: [backend/app/api/applications.py](../../backend/app/api/applications.py) — add `easy_apply` route
- Create: [backend/app/schemas/application.py](../../backend/app/schemas/application.py) — add `EasyApplyRequest`, `EasyApplyResponse`
- Create: [backend/tests/test_easy_apply.py](../../backend/tests/test_easy_apply.py) — integration test

**Steps:**
1. Write failing test: `POST /api/applications/easy-apply {"job_id": 113}` returns 201 with `{application_id, cv_agent_job_id, email_agent_job_id, generated_cv_id}`. Expected error: `404 Not Found` (route doesn't exist yet).
2. Run test, confirm failure.
3. Add Pydantic schemas:
   ```python
   class EasyApplyRequest(BaseModel):
       job_id: int

   class EasyApplyResponse(BaseModel):
       application_id: int
       cv_agent_job_id: int
       email_agent_job_id: int
       generated_cv_id: int
   ```
4. Add route handler `easy_apply` in `applications.py`:
   ```python
   @router.post("/easy-apply", response_model=EasyApplyResponse, status_code=201)
   def easy_apply(body: EasyApplyRequest, db: Session = Depends(get_db),
                  _u: User = Depends(get_current_user)):
       job = db.get(ScrapedJob, body.job_id)
       if job is None: raise HTTPException(404, "Job not found")

       # 1. Create application (or fetch existing for this job_id)
       existing = db.execute(
           select(Application).where(Application.job_id == job.id)
       ).scalar_one_or_none()
       if existing:
           application = existing
       else:
           application = Application(job_id=job.id, company_id=job.company_id,
                                     status="targeting", targeted_at=datetime.now(UTC))
           db.add(application)
           db.flush()
           log_activity(db, application_id=application.id,
                        activity_type="created", description=f"Easy Apply: {job.title}")

       # 2. Spawn CV tailor
       generated_cv, cv_aj_id = generate_cv(db, application.id)

       # 3. Spawn cold email
       email_aj_id = generate_emails(db, application.id)

       db.commit()
       return EasyApplyResponse(
           application_id=application.id,
           cv_agent_job_id=cv_aj_id,
           email_agent_job_id=email_aj_id,
           generated_cv_id=generated_cv.id,
       )
   ```
5. Run test, confirm pass (mock `spawn_claude` to return fake agent_job ids).
6. Add second test: idempotency — calling easy-apply twice on same job_id returns SAME application_id but new agent_job_ids. Confirm pass.
7. Add NEW endpoint `POST /api/emails/{email_id}/send` in `api/emails.py`:
   ```python
   @router.post("/{email_id}/send", response_model=EmailDraftResponse)
   def send_email(email_id: int, db: Session = Depends(get_db),
                  _u: User = Depends(get_current_user)):
       row = db.get(EmailDraft, email_id)
       if row is None: raise HTTPException(404, "Email draft not found")
       if not row.recipient_email:
           raise HTTPException(422, "Email draft has no recipient_email — edit before sending")

       msg = MailMessage(
           to_email=row.recipient_email,
           to_name=row.recipient_name,
           subject=row.subject or "",
           body_text=row.body,
       )
       try:
           result = mailer_service.send(msg, db=db)
       except mailer_service.MailerError as e:
           raise HTTPException(502, f"SMTP send failed: {e}")

       row.status = "sent"
       row.sent_at = datetime.now(UTC)

       # Transition application to "applied" + log activity
       application = db.get(Application, row.application_id)
       if application:
           transition_status(db, application, "applied")
           application.email_sent_at = datetime.now(UTC)

       db.commit()
       db.refresh(row)
       return EmailDraftResponse.model_validate(row)
   ```
8. Test the send endpoint with a mock SMTP (use `pytest-smtpd` or monkeypatch `smtplib.SMTP_SSL`).
9. Run `pytest backend/tests/test_easy_apply.py -v`.
10. Commit: `feat(api): easy-apply orchestration + emails/{id}/send endpoint`.

**Risk flag:**
- Idempotency: double-clicks must not create duplicate applications. Test verifies fetch-or-create.
- `mailer_service.send` requires DB-resolved or env-fallback config — if mailbox not active, returns `MailerDisabled` → 502 to client.
- `recipient_email` may be empty if cold-email skill couldn't find it. UI must handle this gracefully (Phase 4 — modal shows recipient field empty + warns user).

**Verification:**
- [ ] `pytest backend/tests/test_easy_apply.py` passes (2 tests: happy path + idempotency)
- [ ] `pytest backend/tests/test_emails.py::test_send` passes
- [ ] `curl -X POST localhost:8000/api/applications/easy-apply -H 'Authorization: Bearer X' -d '{"job_id":113}'` returns 201 + valid IDs
- [ ] No placeholder code in new endpoints
- [ ] Existing tests still pass (`pytest backend/tests`)

---

### Phase 4: Easy Apply review modal (~150 min)

**Files:**
- Create: [frontend/src/components/easy-apply/EasyApplyModal.tsx](../../frontend/src/components/easy-apply/EasyApplyModal.tsx) — main modal
- Create: [frontend/src/components/easy-apply/DraftReviewPane.tsx](../../frontend/src/components/easy-apply/DraftReviewPane.tsx) — editable preview
- Create: [frontend/src/hooks/useEasyApply.ts](../../frontend/src/hooks/useEasyApply.ts) — orchestration mutation
- Modify: [frontend/src/hooks/useEmails.ts](../../frontend/src/hooks/useEmails.ts) — add `useUpdateEmail` + `useSendEmail`
- Modify: [frontend/src/app/(authed)/jobs/[id]/page.tsx](../../frontend/src/app/(authed)/jobs/[id]/page.tsx) — wire Easy Apply button to modal
- Test: [frontend/src/__tests__/EasyApplyModal.test.tsx](../../frontend/src/__tests__/EasyApplyModal.test.tsx)

**Steps:**
1. Write failing test: EasyApplyModal renders progress bars while both CV + email jobs running; switches to review pane when both `completed`. Expected error: `EasyApplyModal is not defined`.
2. Run test, confirm failure.
3. Implement `useEasyApply()` hook — wraps the new endpoint:
   ```ts
   export function useEasyApply() {
     return useMutation({
       mutationFn: async (jobId: number) =>
         (await api.post<EasyApplyResponse>("/api/applications/easy-apply", { job_id: jobId })).data,
     });
   }
   ```
4. Implement `useUpdateEmail` (`PUT /api/emails/{id}`) and `useSendEmail` (`POST /api/emails/{id}/send`).
5. Implement `EasyApplyModal`:
   - Props: `{ jobId, open, onClose }`
   - On mount, calls `useEasyApply().mutate(jobId)`. Stores returned `cv_agent_job_id`, `email_agent_job_id`, `application_id`, `generated_cv_id`.
   - Two `useProgress(cv_aj_id)` + `useProgress(email_aj_id)` — render dual progress bars.
   - When BOTH `status === "completed"`, fetch:
     - CV download URL: `/api/cv/{generated_cv_id}/download/pdf`
     - Email drafts: `/api/emails?application_id={id}` — pick the one with `email_type === "initial"`
   - Switch to `DraftReviewPane`.
6. Implement `DraftReviewPane`:
   - Header: "Tailored CV ready · 📎 link to PDF download · [Preview] [Download]"
   - Subject input (controlled, syncs to local state)
   - Body textarea (8 rows, controlled, monospace)
   - Recipient email input (REQUIRED — show warning if empty)
   - Follow-ups read-only preview (collapsible — Day 5 / Day 10 subjects + first 200 chars body)
   - 3 buttons: `📤 Send now` (primary) / `💾 Save draft` (ghost — calls `useUpdateEmail`) / `✕ Cancel`
   - On `Send now`: call `useUpdateEmail` first to persist edits, then `useSendEmail`. After success → show "Email sent ✓" + redirect to `/applications/{application_id}` after 2s.
7. Wire Easy Apply button in `jobs/[id]/page.tsx`:
   ```tsx
   const [easyApplyOpen, setEasyApplyOpen] = useState(false);
   ...
   <button onClick={() => setEasyApplyOpen(true)} className="btn-cta">
     <Zap className="h-4 w-4" /> Easy Apply
   </button>
   {easyApplyOpen && (
     <EasyApplyModal jobId={Number(id)} onClose={() => setEasyApplyOpen(false)} />
   )}
   ```
8. Run test, confirm pass.
9. End-to-end manual test: visit `/jobs/113`, click Easy Apply → wait for both progress bars → review modal → edit subject → click Send now → verify:
   - email arrived at recipient inbox
   - application appears in `/applications` with status `applied`
   - email_drafts.status = "sent"
10. Commit: `feat(easy-apply): one-click orchestration + review modal`.

**Risk flag:**
- Both Claude CLI subprocesses run in parallel → could spike CPU. Subprocess.Popen returns immediately so this is fine, but if VPS RAM is tight, monitor.
- WebSocket disconnect during long generation — `useProgress` should auto-reconnect. Verify before shipping.
- Empty `recipient_email` is a real edge case: cold-email skill might not find a hiring manager email. UI shows input field with warning; user can paste manually.
- 30-second total wait may feel long — show ETA based on past runs (`agent_jobs.duration_ms` average) as a polish for Phase 5.

**Verification:**
- [ ] `tsc --noEmit` passes
- [ ] Modal test passes (3 states: pending, completed, sent)
- [ ] Real end-to-end: click → wait → review → send → email arrives in target inbox
- [ ] After send, application status = `applied`, redirect to `/applications/{id}` works
- [ ] `Save draft` button persists edits (verify via `GET /api/emails/{id}` after click)
- [ ] No placeholder code

---

### Phase 5: Polish + Not-relevant flag (~60 min)

**Files:**
- Create: [backend/alembic/versions/013_user_irrelevant.py](../../backend/alembic/versions/013_user_irrelevant.py) — add `scraped_jobs.user_irrelevant: bool`
- Modify: [backend/app/models/job.py](../../backend/app/models/job.py) — add column
- Modify: [backend/app/api/jobs.py](../../backend/app/api/jobs.py) — extend PATCH + filter from list
- Modify: [frontend/src/app/(authed)/jobs/[id]/page.tsx](../../frontend/src/app/(authed)/jobs/[id]/page.tsx) — wire ✕ Not relevant
- Modify: [frontend/src/app/(authed)/jobs/page.tsx](../../frontend/src/app/(authed)/jobs/page.tsx) — filter out user_irrelevant by default
- Test: [backend/tests/test_jobs_irrelevant.py](../../backend/tests/test_jobs_irrelevant.py)

**Steps:**
1. Write failing test: `PATCH /api/jobs/{id} {"user_irrelevant": true}` flips flag; subsequent `GET /api/jobs` excludes it (unless `?include_irrelevant=true`). Expected error: `Pydantic validation: extra field user_irrelevant`.
2. Run test, confirm failure.
3. Migration 013: add `user_irrelevant BOOLEAN NOT NULL DEFAULT false` + index.
4. Add column to `models/job.py`.
5. Extend `JobUpdate` schema with `user_irrelevant: bool | None`.
6. Update list endpoint: default filter `where user_irrelevant = false`, add query param `?include_irrelevant=true` to override.
7. Run test, confirm pass.
8. Wire ✕ Not relevant button in detail page: `useUpdateJob().mutate({ id, user_irrelevant: true })` → toast "Marked as not relevant" → `router.push("/jobs")`.
9. Manual test: mark a job as irrelevant → verify it disappears from `/jobs` list.
10. Add CV-required guard in EasyApplyModal: if `useMasterCV()` returns no active version → block Send and show inline alert "Save your master CV first → /settings?tab=cv".
11. Add error states in EasyApplyModal: agent_job `failed` → show error + retry button.
12. Commit: `feat(jobs): user_irrelevant flag + easy-apply guards`.

**Risk flag:**
- Migration 013 on existing 99+ rows — `DEFAULT false` + `NOT NULL` requires Alembic to add column safely. Use `server_default="false"` + nullable=False.
- After flagging, if user wants to UN-flag, they need an `?include_irrelevant=true` toggle in jobs list. Add a checkbox: "Show hidden". (Not blocking for ship — can be Phase 6.)

**Verification:**
- [ ] Migration 013 runs cleanly on dev DB (`alembic upgrade head`)
- [ ] Existing jobs queries still work
- [ ] `pytest backend/tests/test_jobs_irrelevant.py` passes
- [ ] ✕ Not relevant button in UI → job disappears from list
- [ ] EasyApplyModal blocks if no master CV exists
- [ ] No placeholder code

---

### Implementation tracking

When starting execution, populate TodoWrite:
- [ ] Phase 1: Sidebar 8→3 + Settings tabs
- [ ] Phase 2: Job detail LinkedIn hero + CompanyLogo
- [ ] Phase 3: Easy Apply orchestration endpoint + send endpoint
- [ ] Phase 4: Easy Apply review modal (the centerpiece)
- [ ] Phase 5: Not-relevant flag + polish

Each phase ends with `git push` → GitHub Actions auto-deploy → verify on production before next phase.

### Total estimate

~8 hours focused execution. Phases 1-2 visual changes (deploy + verify takes ~5min after each push), Phases 3-4 the core flow, Phase 5 polish.

### Execution handoff

Three options for next step:
1. **Execute in this session** — invoke `gaspol-execute` to run Phase 1 with hard-gate TDD checkpoints
2. **Parallel execution** — Phases 1 + 3 are independent (frontend nav refactor vs backend API), `gaspol-parallel` could run them in worktree-isolated subagents
3. **Save plan, resume next session** — plan complete, all paths verified, can pick up later
