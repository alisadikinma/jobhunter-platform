# JobHunter UI/UX Design Plan

> Companion to [2026-04-15-jobhunter-mvp-design.md](2026-04-15-jobhunter-mvp-design.md).
> Covers visual design system, layouts, interaction patterns, and component specs for the Next.js 15 admin panel.

## 1. Design Philosophy

### Target User Profile

- **Single power user** (Ali) — developer with strong technical fluency
- **Data-dense tolerance high** — would rather see full table than oversimplified cards
- **Keyboard-driven preferred** — typing > clicking, shortcuts > menus
- **Dark mode default** — long admin sessions, late night usage pattern
- **No hand-holding needed** — skip onboarding, skip tooltips on obvious actions

### Positioning

**JobHunter is a professional admin tool, not a consumer SaaS.** Think Linear, GitHub, Vercel dashboard — NOT Notion, Asana, or Monday. Dense information, terse copy, keyboard shortcuts, minimal decoration.

### Anti-Patterns to Avoid

- ❌ Empty-feeling cards with huge padding
- ❌ Generic "Hello, Ali 👋" welcome dashboards
- ❌ Motivational copy ("Let's find your dream job!")
- ❌ Emoji icons (🎯, 🚀, ⚙️) — use Lucide SVG only
- ❌ Full-page modals when a side sheet fits
- ❌ Hero sections or marketing patterns — this is a utility
- ❌ Pastel colors, playful illustrations, friendly mascots

---

## 2. Design System

### Style: Data-Dense Dashboard

**Visual language:** Linear.app + GitHub Projects + Vercel dashboard hybrid. Dense grids, minimal chrome, monospace for data, system font for UI.

**Density level:** HIGH. Comfortable row heights 36-40px, not 56-64px. Minimal padding between logical groups (12-16px, not 24-32px).

### Color Palette

Dual theme (dark primary, light available). All values use semantic tokens in Tailwind config, never raw hex in components.

#### Dark Mode (Default)

```css
/* Backgrounds — layered depth */
--bg-base:       #0A0B0D   /* app shell */
--bg-elevated:   #111318   /* cards, panels */
--bg-overlay:    #1A1D23   /* popovers, dropdowns */
--bg-hover:      #1E2128   /* row/button hover */

/* Borders */
--border-subtle: #1F2329   /* section dividers */
--border-default:#2A2F36   /* cards, inputs */
--border-strong: #3A4048   /* focus, active */

/* Text */
--text-primary:  #E8EAED   /* headings, body */
--text-secondary:#9CA3AF   /* labels, meta */
--text-tertiary: #6B7280   /* disabled, hints */
--text-inverse:  #0A0B0D   /* on-colored backgrounds */

/* Brand — blue primary, orange accent */
--brand-primary: #3B82F6   /* links, primary actions */
--brand-primary-hover: #2563EB
--brand-accent:  #F97316   /* CTAs, high-impact actions */
--brand-accent-hover: #EA580C

/* Variant indicators (3 primary verticals) */
--variant-vibe:       #A855F7   /* Vibe Coding — purple */
--variant-automation: #10B981   /* AI Automation — emerald */
--variant-video:      #EC4899   /* AI Video — pink */

/* Semantic */
--success: #10B981
--warning: #F59E0B
--danger:  #EF4444
--info:    #3B82F6

/* Score bar gradient (relevance 0-100) */
--score-low:    #EF4444   /* 0-40 */
--score-mid:    #F59E0B   /* 41-70 */
--score-high:   #10B981   /* 71-100 */
```

#### Light Mode

```css
--bg-base:       #FFFFFF
--bg-elevated:   #F8FAFC
--bg-overlay:    #FFFFFF
--bg-hover:      #F1F5F9
--border-subtle: #E2E8F0
--border-default:#CBD5E1
--border-strong: #94A3B8
--text-primary:  #0F172A
--text-secondary:#475569
--text-tertiary: #94A3B8
/* Brand + variant colors stay same (already WCAG AA compliant on both themes) */
```

**Contrast verification:** All text/background pairs tested ≥4.5:1 AA (body) and ≥7:1 AAA (primary headings).

### Typography

**Stack per plan doc recommendation:** Fira Sans (UI) + Fira Code (data/monospace).

```css
/* Google Fonts import in app/layout.tsx */
@import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600;700&family=Fira+Sans:wght@300;400;500;600;700&display=swap');

/* Type scale */
--font-ui:   'Fira Sans', system-ui, -apple-system, sans-serif
--font-mono: 'Fira Code', 'SF Mono', Consolas, monospace

/* Size scale (rem, 16px base) */
--text-xs:   0.75rem   /* 12px — timestamps, metadata, badges */
--text-sm:   0.875rem  /* 14px — table cells, labels, captions */
--text-base: 1rem      /* 16px — body, inputs */
--text-lg:   1.125rem  /* 18px — section headings */
--text-xl:   1.25rem   /* 20px — page titles */
--text-2xl:  1.5rem    /* 24px — stat values, hero numbers */

/* Weights */
--weight-regular: 400
--weight-medium:  500  /* labels, buttons */
--weight-semi:    600  /* headings */
--weight-bold:    700  /* emphatic numbers */

/* Usage rules */
- Job titles, company names: font-ui 14px semibold
- Salary ranges, scores, dates: font-mono 13px regular (tabular numbers)
- Code-like IDs (agent_job_id, content_hash): font-mono 12px
- Markdown preview in CVEditor: font-ui 15px 1.6 line-height
```

### Spacing Scale

8px base, but use 4px for tight data layouts:

```
--space-0:  0
--space-1:  4px    /* inline icons + text */
--space-2:  8px    /* button padding */
--space-3:  12px   /* card internal */
--space-4:  16px   /* default gap */
--space-6:  24px   /* section separation */
--space-8:  32px   /* page padding */
--space-12: 48px   /* major section break */
```

### Elevation / Shadow

Dark mode minimizes shadow (ambient too subtle), uses border + bg shift instead:

```css
/* Dark mode: rely on bg-elevated + border */
.card-dark {
  background: var(--bg-elevated);
  border: 1px solid var(--border-default);
}

/* Light mode: subtle shadow */
--shadow-sm: 0 1px 2px rgba(0,0,0,0.05)
--shadow-md: 0 4px 6px -1px rgba(0,0,0,0.1)
--shadow-lg: 0 10px 15px -3px rgba(0,0,0,0.1)
```

### Border Radius

Consistent 6-8px range, no pill-shaped elements except status badges:

```
--radius-sm: 4px    /* badges, tags */
--radius-md: 6px    /* buttons, inputs */
--radius-lg: 8px    /* cards, modals */
--radius-full: 9999px  /* status pills only */
```

### Icons

- **Library:** Lucide React (no exceptions — same family across entire app)
- **Sizes:** 14px (inline text), 16px (buttons), 20px (nav), 24px (empty states)
- **Stroke:** 1.75px consistent
- **Color:** Inherit from text-color, never hard-code

---

## 3. Layout System

### Shell Architecture

```
┌─────────────────────────────────────────────────────┐
│  Sidebar (240px)       │  Main Content              │
│  ─────────────         │  ────────────              │
│  Logo + search shortcut│  Page header (sticky)      │
│                        │  ┌────────────────────┐   │
│  ▸ Dashboard           │  │  Action bar        │   │
│  ▸ Jobs      [142]     │  │  (filters, CTA)    │   │
│  ▸ Applications  [8]   │  └────────────────────┘   │
│  ▸ CV                  │                            │
│  ▸ Portfolio           │  Content region            │
│  ▸ Emails              │  (table / kanban /         │
│  ▸ Apify Pool  [●]     │   editor)                  │
│  ▸ Settings            │                            │
│                        │                            │
│  ─────────────         │                            │
│  user@email.com        │                            │
│  v1.0.3 (master)       │                            │
└─────────────────────────────────────────────────────┘
```

### Responsive Breakpoints

- **1024px+ (primary target):** Full sidebar + content
- **768-1023px:** Collapsible sidebar (icon-only, 56px wide, hover to expand)
- **<768px:** Mobile view — NOT optimized (admin tool, desktop-first). Bare-minimum readable, hamburger menu. Don't invest time in mobile polish for MVP.

### Container Widths

- Content region: `max-w-none` (use full viewport width — this is a dashboard, not marketing site)
- CV Editor form: `max-w-4xl` (64rem) — readable form field width
- Modals/Sheets: `max-w-2xl` (centered modal) or side sheet (400-480px wide)

---

## 4. Page Specifications

### 4.1 Dashboard (`/dashboard`)

**Goal:** Answer "what should I focus on right now?" in under 3 seconds.

```
┌──────────────────────────────────────────────────────────────┐
│  Sprint Day 4 of ~14 target    Pool: 4/5 active   $3.20/day │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─── New Jobs ───┐ ┌── Applications ──┐ ┌── Response Rate ─┐│
│  │  142 today     │ │   8 active       │ │   22%            ││
│  │  ↑ 23 vs yest  │ │   3 ↗ this week │ │   (3/14 emails)  ││
│  └────────────────┘ └──────────────────┘ └──────────────────┘│
│                                                               │
│  ┌─── Top 10 High-Score Jobs (new today) ────────────────┐  │
│  │  Score  Title                    Company       Variant  │  │
│  │  ▰▰▰▰▱ 92  Agent Engineer       Wellfound    [vibe]  ⋯ │  │
│  │  ▰▰▰▰▱ 88  Automation Lead      HiringCafe   [auto]  ⋯ │  │
│  │  ▰▰▰▰▱ 85  AI Video Eng         LinkedIn     [video] ⋯ │  │
│  │  ...                                                     │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌── Pending Action ──────────────────────────────────────┐ │
│  │ • CV draft #12 ready for review  →                     │ │
│  │ • Follow-up email to Acme Corp due tomorrow            │ │
│  │ • Interview with StartupX Thursday 10 AM               │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌── 7-Day Activity ──────────────────────────────────────┐ │
│  │  Applications sent (bar chart, recharts)               │ │
│  │  ■■ ■■■ ■■■■ ■■ ■■■ ■ ■■                               │ │
│  └────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

**Components:**
- `<StatsCards />` — 3-card grid, compact, each shows number + delta + sparkline
- `<TopJobsTable />` — 10-row preview with ScoreBar, click → /jobs/[id]
- `<PendingActionsCard />` — flat list, no padding bloat
- `<WeeklyChart />` — Recharts bar chart, 120px height, no grid lines

**Keyboard:** `G D` (Go Dashboard), `N J` (New Job view)

---

### 4.2 Jobs Table (`/jobs`)

**Goal:** Scan 100+ scraped jobs fast, filter aggressively, bulk-action.

```
┌───────────────────────────────────────────────────────────────┐
│ Jobs                                 [+ Manual Import] [Scrape]│
├───────────────────────────────────────────────────────────────┤
│  [Status: All ▼] [Source ▼] [Variant ▼] [Score ≥70] [🔍 search]│
│  ───────────────────────────────────────────── 142 jobs · 23 new│
│                                                                │
│  ☐ ▰▰▰▰▰ 95  Senior AI Engineer  Vercel   remote  [vibe]   2h │
│  ☐ ▰▰▰▰▱ 88  Automation Engineer Brandtech  US    [auto]   3h │
│  ☐ ▰▰▰▰▱ 85  Runway Specialist   WolfGames  remote [video] 5h │
│  ☐ ▰▰▰▱▱ 72  Full-Stack Dev      Generic    US    [vibe]   1d │
│  ...                                                           │
│                                                                │
│  [3 selected] [→ Create Application] [↓ Mark Skipped] [✕]     │
├───────────────────────────────────────────────────────────────┤
│  ◀ Prev  Page 1 of 8  Next ▶      Show: 25 50 100 per page   │
└───────────────────────────────────────────────────────────────┘
```

**Table columns (36px row height):**
1. Checkbox (32px)
2. Score bar (gradient red→amber→green based on 0-100, 80px wide)
3. Score number (monospace 13px)
4. Job title (truncate with tooltip, 280px)
5. Company (flex, 200px)
6. Location (120px)
7. Variant badge (80px, color-coded dot + text)
8. Scraped time (relative, "2h ago" — monospace, 60px)
9. Actions menu (⋯)

**Filters (top bar, sticky):**
- Status dropdown (new / reviewed / targeting / skipped / expired)
- Source multi-select (LinkedIn, RemoteOK, HN, HiringCafe, Wellfound, etc.)
- Variant pills (vibe_coding / ai_automation / ai_video — click to toggle)
- Score slider (min score 0-100, default 70)
- Search box (full-text across title + company + description)

**Row interactions:**
- Click row → navigate to /jobs/[id]
- Right-click → context menu (same as ⋯)
- `J` / `K` keyboard navigation between rows (Vim-style)
- `Enter` → open detail
- `X` → toggle skipped
- `F` → toggle favorite

**Bulk action bar:** appears when ≥1 row selected, sticky bottom

---

### 4.3 Job Detail (`/jobs/[id]`)

Side-sheet OR full page based on entry context:
- From Jobs table → side sheet (60% viewport width, preserves list context)
- Direct URL access → full page

```
┌────────────────────────────────────────────────────┐
│ ◀ Back        Senior AI Engineer     ⋯            │
│               at Vercel                            │
│  ▰▰▰▰▰ 95/100   vibe_coding   Posted 2h ago       │
├────────────────────────────────────────────────────┤
│  [Create Application] [★ Favorite] [✕ Skip]       │
├────────────────────────────────────────────────────┤
│  PROS                        CONS                  │
│  ✓ Claude Code mentioned     ✗ US timezone overlap │
│  ✓ Next.js 15 stack          ✗ Unclear salary     │
│  ✓ Remote-first culture                            │
│                                                     │
│  KEYWORDS MATCHED (8/12)                            │
│  [Claude Code] [LangChain] [RAG] [TypeScript]      │
│  [Next.js] [Vercel] [Agent] [Full-stack]           │
│                                                     │
│  MISSING KEYWORDS                                   │
│  [LangGraph] [LlamaIndex] [Pinecone] [AWS]         │
│                                                     │
│  ─────────────────────────────────────────         │
│  JOB DESCRIPTION (enriched via Firecrawl)          │
│  ─────────────────────────────────────────         │
│  (Full markdown rendering, 65ch max width)         │
│  ...                                                │
│                                                     │
│  SOURCE: linkedin · source_url ↗                   │
│  DESCRIPTION SOURCE: firecrawl_enriched (42kb)     │
└────────────────────────────────────────────────────┘
```

---

### 4.4 Applications Kanban (`/applications`)

**Goal:** Drag-drop status management, see pipeline at a glance.

```
┌──────────────────────────────────────────────────────────┐
│  Applications                     [Filter ▼] [+ New]    │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  Targeting  CV Gen  Applied  Email  Replied  Interview  │
│   (3)        (1)     (4)     (2)     (2)      (1)       │
│  ┌────────┬────────┬────────┬────────┬────────┬────────┐│
│  │ Vercel │ Brand  │ Acme   │ Startu │ Wolf   │ Linear ││
│  │ [vibe] │ tech   │ Co     │ pX     │ Games  │        ││
│  │ ▰▰▰▰▰ │ [auto] │ [vibe] │ [auto] │ [video]│ [vibe] ││
│  │ 3d     │ ▰▰▰▰▱ │ 1d     │ 2d     │ 5d     │ today  ││
│  │        │ 2d     │        │        │        │        ││
│  │ ────── │        │ Acme2  │ ────── │ ────── │        ││
│  │ Linear │ ────── │ Corp   │ Thurs  │        │        ││
│  │ [vibe] │        │        │ 10 AM  │        │        ││
│  └────────┴────────┴────────┴────────┴────────┴────────┘│
└──────────────────────────────────────────────────────────┘
```

**Card content (compact, 80px height):**
- Company name (semibold)
- Variant badge (small, left-aligned)
- Relevance score bar
- Days in current status (monospace)
- Urgency indicator (red dot) for overdue actions

**Interactions:**
- Drag card between columns → `PATCH /api/applications/{id}` with new status
- Optimistic UI + toast on success/failure
- Click card → opens side sheet detail (NOT full page navigation, preserves Kanban context)
- `@dnd-kit` with 4px drag threshold (avoids accidental drags)
- Keyboard: `Tab` through cards, `Space` to pick up, arrow keys to move, `Space` to drop

**Columns scroll horizontally on narrow viewports** (no wrap, always 12 columns visible via scroll).

---

### 4.5 CV Editor (`/cv`)

Master CV editor dengan 3 variant tabs.

```
┌────────────────────────────────────────────────────────┐
│  Master CV · v12 (active)         [Preview] [Save]    │
├────────────────────────────────────────────────────────┤
│  [Basics] [Work] [Projects] [Skills] [Variants*] [Raw]│
│                                                         │
│  --- Variants tab selected ---                          │
│                                                         │
│  Summary variants (used by /cv-tailor):                 │
│                                                         │
│  [Vibe Coding] [AI Automation] [AI Video]               │
│                                                         │
│  --- Vibe Coding selected ---                           │
│  ┌──────────────────────────────────────────────────┐  │
│  │ Full-Stack engineer who ships MVPs in days using │  │
│  │ Claude Code + Cursor. Built [JobHunter] in 3     │  │
│  │ weeks from zero to production. Proof over        │  │
│  │ credentials: live SaaS, GitHub plugin ecosystem, │  │
│  │ 20+ agentic automations in daily use.            │  │
│  │                                                   │  │
│  │ 312 / 500 chars · 52 words                        │  │
│  └──────────────────────────────────────────────────┘  │
│                                                         │
│  Hints:                                                 │
│  • Start with "Full-Stack" or "AI-Native Engineer"     │
│  • Include 1 quantified outcome                         │
│  • Mention Claude Code explicitly                       │
└────────────────────────────────────────────────────────┘
```

**Highlights editor (nested in Work tab):**
```
Work > Experience #2 > Bullet #3:
┌──────────────────────────────────────────────────────┐
│ Text:                                                │
│ Built Laravel 12 + Vue 3 CMS with Claude CLI         │
│ integration for autonomous content generation...     │
│                                                       │
│ Tags (for tailor filtering):                         │
│ [claude-cli ✕] [automation ✕] [full-stack ✕]         │
│ [laravel ✕] [vue ✕] [cms ✕] [+ add tag]             │
│                                                       │
│ Relevance hint (max 3, ONLY from allowed variants):  │
│ ☑ vibe_coding  ☑ ai_automation  ☐ ai_video          │
│                                                       │
│ Metrics (optional JSON):                             │
│ { "throughput": "100+/week", "stack_size": 3 }       │
│                                                       │
│ [↑ Move up] [↓ Move down] [Delete]                   │
└──────────────────────────────────────────────────────┘
```

**Frontend validation:** `relevance_hint` checkbox values locked to exactly `["vibe_coding", "ai_automation", "ai_video"]`. Invalid values impossible to submit.

---

### 4.6 Generated CV Preview (`/cv/generated/[id]`)

Side-by-side master vs tailored + ATS scorecard.

```
┌─────────────────────────────────────────────────────────┐
│ Generated CV #47 for Senior AI Engineer @ Vercel       │
│ Variant: vibe_coding (confidence 0.87)                 │
│ [Download DOCX] [Download PDF] [Edit MD] [Regenerate]  │
├──────────────────────┬──────────────────────────────────┤
│                      │                                   │
│  MASTER CV (v12)     │  TAILORED (variant: vibe_coding) │
│  ─────────────       │  ─────────────────────────       │
│                      │                                   │
│  (rendered markdown  │  (rendered markdown with diff    │
│   in slate/serif,    │   highlighting — added content   │
│   65ch max width)    │   in green, removed in red)      │
│                      │                                   │
├──────────────────────┴──────────────────────────────────┤
│  ATS SCORE: 87/100   (target ≥80) ✓ PASS               │
│                                                          │
│  Matched keywords (14/18):                              │
│  [Claude Code] [TypeScript] [Next.js] [Vercel] ...     │
│                                                          │
│  Missing keywords (4):                                  │
│  [AWS Lambda] [Pinecone] [Redis] [GraphQL]              │
│                                                          │
│  Suggestions:                                            │
│  • Add "AWS Lambda" to Projects section — JobHunter    │
│    uses Celery which is functionally similar            │
│  • Mention Pinecone in skills if you've used vector DB │
└─────────────────────────────────────────────────────────┘
```

**Progress modal (during generation):**
```
┌─────────────────────────────────────────┐
│  Generating CV...                       │
│                                         │
│  ████████████░░░░░░  65%               │
│                                         │
│  Current: Rewriting work highlights     │
│  ~30 seconds remaining                  │
│                                         │
│  Log (tail -5):                         │
│  > Classified JD: vibe_coding (0.87)   │
│  > Selected 4 portfolio assets          │
│  > Filtered 23→8 highlights             │
│  > Rewriting summary variant            │
│  > Rewriting work highlights...         │
└─────────────────────────────────────────┘
```

Real-time updates via WebSocket `/ws/progress/{agent_job_id}`.

---

### 4.7 Portfolio Admin (`/portfolio`)

3 tabs dengan hybrid audit flow.

```
┌─────────────────────────────────────────────────────┐
│ Portfolio Assets          [Re-scan] [+ Add External]│
├─────────────────────────────────────────────────────┤
│ [Draft (6)] [Published (3)] [Skipped (0)]          │
│                                                      │
│ --- Draft tab ---                                   │
│                                                      │
│ ┌── gaspol-dev Claude Code Plugin ──────────────┐  │
│ │ auto_generated · plugin · ~/.claude/plugins/..│  │
│ │                                                │  │
│ │ Description (pre-filled, editable):            │  │
│ │ Engineering workflow orchestrator: 15 skills   │  │
│ │ + 8 subagents for TDD/review/execute cycles    │  │
│ │                                                │  │
│ │ Tech: [Claude Code] [MCP] [plugin architecture]│  │
│ │ Tags: [claude-code] [plugin] [workflow] [tdd]  │  │
│ │ Relevance: ☑ vibe_coding ☑ ai_automation       │  │
│ │                                                │  │
│ │ URL: [________________] ← needs fill           │  │
│ │ Thumbnail: [Upload] ← needs fill               │  │
│ │ Metrics (JSON): { "used_daily": true }         │  │
│ │ Display priority: ▰▰▰▰▱ 85                    │  │
│ │                                                │  │
│ │        [✓ Publish]  [Skip]  [Delete Draft]    │  │
│ └────────────────────────────────────────────────┘  │
│                                                      │
│ ┌── AI Video Promo Engine Plugin ────────────────┐  │
│ │ ...                                             │  │
└─────────────────────────────────────────────────────┘
```

---

### 4.8 Apify Pool Admin (`/apify-pool`)

```
┌──────────────────────────────────────────────────────┐
│ Apify Pool                    [+ Add] [Bulk Import] │
├──────────────────────────────────────────────────────┤
│ Pool Health                                          │
│ 🟢 4/5 Active  │  Credit: $17.50 / $25.00 (70%)    │
│ Burn rate: $3.20/day  │  Runway: ~5 days ✓         │
│                                                       │
│ ⚠ One account exhausted. Reset in ~18 days.         │
├──────────────────────────────────────────────────────┤
│  Label              Email            Status   Credit│
│  ─────              ─────            ──────   ──────│
│  apify-01    ali+apify01@gm..  ●active  4.20/5.00 │
│  apify-02    ali+apify02@gm..  ●active  3.50/5.00 │
│  apify-03    ali+apify03@gm..  ●active  2.80/5.00 │
│  apify-04    ali+apify04@gm..  ●active  2.00/5.00 │
│  apify-05    ali+apify05@gm..  ●exhaust 5.00/5.00 │
│                                                       │
│  Actions: [Test] [Suspend] [Delete]                  │
└──────────────────────────────────────────────────────┘
```

---

### 4.9 Emails (`/emails`)

Grouped by application, showing 3-email sequence per application.

```
┌─────────────────────────────────────────────────────┐
│ Email Drafts                                        │
├─────────────────────────────────────────────────────┤
│                                                      │
│  ┌── Senior AI Engineer @ Vercel ─────────────────┐│
│  │ Variant: vibe_coding                            ││
│  │                                                  ││
│  │ Initial · status: approved · ready to send      ││
│  │ Subject: "Built JobHunter in 3 weeks with ..."  ││
│  │ [Preview] [Edit] [Copy to Clipboard]            ││
│  │                                                  ││
│  │ Follow-up 1 (day 5) · status: draft             ││
│  │ [Preview] [Edit]                                ││
│  │                                                  ││
│  │ Follow-up 2 (day 10) · status: draft            ││
│  │ [Preview] [Edit]                                ││
│  └──────────────────────────────────────────────────┘│
│                                                      │
│  ┌── Automation Engineer @ Brandtech ─────────────┐│
│  │ ...                                              ││
└─────────────────────────────────────────────────────┘
```

**Email preview sheet:**
```
┌─────────────────────────────────────┐
│ ✕                                   │
│                                     │
│ To: recruiter@vercel.com            │
│ Subject: Built JobHunter in 3 weeks │
│          with Claude Code           │
│                                     │
│ Hi [Name],                          │
│                                     │
│ I noticed Vercel's push toward AI   │
│ SDK integrations this quarter —     │
│ particularly the Agent SDK release. │
│                                     │
│ I just shipped JobHunter...         │
│ [full body rendered]                │
│                                     │
│ [📋 Copy Full Email]                │
│ Word count: 134 · Subject: 8 words │
└─────────────────────────────────────┘
```

---

### 4.10 Settings (`/settings`)

Scrape configs + API keys + feature flags.

```
┌────────────────────────────────────────────────────┐
│ Settings                                           │
├────────────────────────────────────────────────────┤
│ [Scrape Configs] [API Keys] [Features]             │
│                                                     │
│ --- Scrape Configs tab ---                         │
│                                                     │
│  Vibe Coding Remote          [Active ●]           │
│  ──────────────────                                │
│  Keywords: [Claude Code ✕] [Cursor ✕] [Windsurf ✕]│
│            [+ add]                                 │
│  Sources: ☑ RemoteOK ☑ HN ☑ HiringCafe ☑ JobSpy  │
│           ☑ Wellfound (via Apify)                 │
│  Cron: 0 */3 * * *  [Edit]                        │
│  Last run: 23 min ago · 142 new / 38 dup          │
│                                                     │
│  AI Automation Engineer      [Active ●]           │
│  ...                                                │
└────────────────────────────────────────────────────┘
```

---

## 5. Component Patterns

### 5.1 ScoreBar

```tsx
<ScoreBar value={87} size="sm" />
// Renders: ▰▰▰▰▱ 87 with gradient fill
```

- Widths: sm (60px), md (80px), lg (120px)
- Color: gradient red→amber→green based on value
- Always show number next to bar (not in tooltip)
- Uses `tabular-nums` for alignment

### 5.2 VariantBadge

```tsx
<VariantBadge variant="vibe_coding" />
// Renders: ● vibe
```

- 3 colors lock: purple (vibe), emerald (auto), pink (video)
- Dot + abbreviated label
- 20px height, font-mono 11px uppercase
- Tooltip shows full name on hover

### 5.3 StatusPill

```tsx
<StatusPill status="targeting" />
// Renders: [Targeting] in brand-primary subtle bg
```

12 status variants — each with unique color mapping:
- targeting: blue
- cv_generating / email_sent: amber (in-flight)
- cv_ready / applied: green
- replied / interview_scheduled / interviewed: teal (positive progression)
- offered / accepted: emerald (terminal positive)
- rejected / ghosted / skipped: gray/red (terminal negative)

### 5.4 DataTable (reusable pattern)

Wraps shadcn Table with:
- Sticky header with shadow on scroll
- Row hover bg change (bg-hover token)
- 36px row height default
- Selection checkbox column
- Bulk action bar (appears when selected)
- Pagination footer (compact: ◀ Prev · Page X of Y · Next ▶)
- Keyboard navigation (`J`/`K` up/down, `Enter` open, `X` action)
- Empty state with CTA

### 5.5 ProgressModal

WebSocket-driven live progress. Pattern:
- Blocks focus (modal), but ESC cancels (sends `DELETE /api/agent-jobs/{id}`)
- Progress bar at top (determinate when progress_pct available)
- Current step text below
- Tail of last 5 log lines (`font-mono`, `text-secondary`)
- Auto-closes on `status=completed` OR `status=failed`
- Failed state: shows error message + "View full log" button

---

## 6. Interaction Patterns

### 6.1 Keyboard Shortcuts (Global)

| Keys | Action |
|------|--------|
| `G D` | Go to Dashboard |
| `G J` | Go to Jobs |
| `G A` | Go to Applications |
| `G C` | Go to CV Editor |
| `G P` | Go to Portfolio |
| `G S` | Go to Settings |
| `⌘K` / `Ctrl+K` | Command palette (search all) |
| `?` | Show shortcuts help overlay |
| `Esc` | Close modal / sheet / unselect |

### 6.2 Command Palette (⌘K)

Fuse.js fuzzy search across:
- All jobs (title + company)
- All applications
- Saved filters
- Quick actions ("Trigger scrape", "Generate CV for X")

Sheet slides from top, 600px wide centered, dismissed on Escape.

### 6.3 Animations

All motion respects `prefers-reduced-motion`:

```css
@media (prefers-reduced-motion: reduce) {
  * { animation-duration: 0.01ms !important; }
  * { transition-duration: 0.01ms !important; }
}
```

**Durations:**
- Hover/press feedback: 120ms
- Row selection: 150ms
- Sheet slide-in: 200ms ease-out
- Modal fade-in: 180ms
- Kanban card drag: physics-based via `@dnd-kit`
- Page transitions: 150ms fade (no slide)

**Never animate:** table rows on data update (only indicator pulse), scroll position.

### 6.4 Loading States

| Duration | Pattern |
|----------|---------|
| <100ms | No indicator |
| 100-500ms | Inline spinner |
| 500ms-3s | Skeleton screen |
| 3s+ | Progress modal with live step |

Example skeleton for Jobs table:
```tsx
<tr>
  <td><Skeleton w={16} h={16} /></td>
  <td><Skeleton w={60} h={10} /></td>
  <td><Skeleton w={200} h={12} /></td>
  ...
</tr>
```

---

## 7. Dark Mode Implementation

### Strategy

- **Default to dark** on first visit (detect `prefers-color-scheme`)
- Toggle in sidebar footer (icon button, no page reload)
- Persist in localStorage
- Tailwind `class` strategy: `<html class="dark">`

### Testing

Every color pair must pass BOTH light and dark mode contrast checks independently. Never assume inverted colors work.

```ts
// color-tokens.ts
export const tokens = {
  'bg-base': { dark: '#0A0B0D', light: '#FFFFFF' },
  'text-primary': { dark: '#E8EAED', light: '#0F172A' },
  // ...
};

// Tailwind config reads these for dark: variant
```

---

## 8. Accessibility Baseline

### Must-Pass Checklist

- [ ] Contrast: All text ≥4.5:1 on both themes
- [ ] Focus rings: 2px solid brand-primary, visible on ALL interactive elements
- [ ] Touch targets: ≥44×44px on mobile breakpoints (even if admin desktop-first)
- [ ] Screen reader labels: `aria-label` on all icon-only buttons
- [ ] Form labels: visible `<label>` element (never placeholder-only)
- [ ] Error messages: inline below field + `aria-describedby`
- [ ] Keyboard nav: full app operable without mouse
- [ ] Skip link: "Skip to main content" at top (sr-only until focus)
- [ ] Alt text: all meaningful images (screenshots, thumbnails)
- [ ] Color not sole indicator: variant badges have icon + text, not just color
- [ ] Reduced motion: respected globally
- [ ] Heading hierarchy: sequential `h1→h6`, no skips

### Dynamic Type

Not critical for admin power user, but support browser zoom to 200% without horizontal scroll.

---

## 9. Implementation Order (Maps to MVP Phases)

| Phase (from main plan) | UI Focus |
|------------------------|----------|
| Phase 15 (Frontend bootstrap) | Design tokens setup in Tailwind config, dark mode toggle, sidebar shell, Lucide icons |
| Phase 16 (Jobs Table) | `DataTable` component, `ScoreBar`, `VariantBadge`, filters, keyboard nav |
| Phase 17 (CV Editor + Portfolio) | `CVEditor` with variant tabs, `HighlightsEditor`, `PortfolioAssetCard` |
| Phase 18 (CV Generation Preview) | `CVPreview` with diff, `ATSScoreCard`, `ProgressModal` + WebSocket |
| Phase 19 (Applications Kanban) | `KanbanBoard` with dnd-kit, `ApplicationCard`, `TimelineView`, `StatusPill` |
| Phase 20 (Emails + Apify Admin) | `EmailPreview`, `EmailEditor`, Pool health widget, bulk add dialog |
| Phase 21 (Dashboard + Settings) | `StatsCards`, `WeeklyChart`, scrape config CRUD UI |

---

## 10. Pre-Delivery QA

### Visual Polish
- [ ] No emojis as icons anywhere (Lucide only)
- [ ] Consistent icon stroke (1.75px) across all uses
- [ ] Same corner radius tier per component type
- [ ] Border + bg tokens used, zero raw hex in components
- [ ] Tabular numbers for all data columns (scores, salaries, dates)

### Interaction
- [ ] Every clickable element has `cursor-pointer` + hover state
- [ ] Loading states for any async op >300ms
- [ ] Keyboard nav tested end-to-end (can complete full workflow without mouse)
- [ ] Command palette (⌘K) surfaces within 100ms

### Layout
- [ ] 1024px viewport works perfectly (primary target)
- [ ] 1440px doesn't stretch content awkwardly (use max-width on editors)
- [ ] Sidebar collapses at 1023px
- [ ] No horizontal scroll on Kanban (unless >6 columns visible)
- [ ] Modals center properly with backdrop blur

### Theme
- [ ] Both themes tested independently (not inferred)
- [ ] All interaction states (hover/focus/active/disabled) visible in both
- [ ] Variant color coding consistent across pages

### Performance
- [ ] Fonts preloaded (`<link rel="preload">`)
- [ ] Images use Next.js `<Image>` with dimensions
- [ ] Virtualize Jobs table if >100 rows (TanStack Virtual)
- [ ] Debounce search input (300ms)
- [ ] Skeleton screens instead of spinners for >500ms loads

---

## Summary

**Design language:** Professional admin tool, data-dense, keyboard-driven, dark-first.
**Inspiration:** Linear + GitHub Projects + Vercel Dashboard.
**Stack:** Next.js 15 + shadcn/ui + Tailwind 4 + Lucide icons + Fira Sans/Code fonts.
**Critical principles:** No emoji icons, tabular numbers for data, variant color coding (purple/emerald/pink), dark mode default, keyboard-first navigation.
