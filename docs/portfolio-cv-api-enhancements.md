# Portfolio CV API — Enhancement Spec

> **Audience:** the agent maintaining `alisadikinma.com/api/cv/*` endpoints.
> **Consumer:** [jobhunter](https://github.com/alisadikinma/jobhunter) — the
> CV import flow at `/settings?tab=cv` calls `GET /api/cv/master.md` and
> currently has to run a full LLM parse on every import to fill schema gaps.
> This document lists what to add/change so the consumer can drop the LLM
> pass entirely (target: `requests.get → JSON validate → save`, ~1s round-trip).
>
> **Authoritative consumer schema:** `MasterCVContent` in
> [`backend/app/schemas/cv.py`](https://github.com/alisadikinma/jobhunter/blob/master/backend/app/schemas/cv.py).
> If you implement everything in this doc, every field below validates
> directly against that schema with no transformation.

---

## TL;DR

| Priority | Change | Why |
|---|---|---|
| **P0** | Add `basics.summary_variants` | Required by consumer schema, no fallback possible. |
| **P0** | Populate `work[]` separately from `projects[]` | ATS scoring needs employment dates/positions. |
| **P0** | Add categorized `skills{}` object | Jaccard keyword matcher reads exact shape. |
| **P0** | Add `education[]` | Section is blank without it. |
| **P1** | Strip HTML from `summary` fields | Saves ~30% LLM prompt tokens downstream. |
| **P1** | Fix UTF-8 mojibake (`�` characters) | Round-trip encoding bug somewhere in the stack. |
| **P1** | Populate `projects[].highlights[]` + `metrics{}` | Currently empty across all 56 projects. |
| **P2** | Split `relevance_hint` into strict `variant_hint` + freeform `tags` | Consumer rejects values outside `vibe_coding`/`ai_automation`/`ai_video`. |
| **P2** | Add `tech_stack[]` (separate from category `tags`) | Doc claims it exists; response only has category tags. |
| **P2** | Document the `{success, data}` envelope OR drop the wrapper for `/cv/export` | Doc currently misleading. |

---

## P0 — Schema-blockers (consumer cannot work around)

### 1. `basics.summary_variants` — three hand-crafted opening paragraphs

**Current:** `basics.summary` is a single HTML blob.

**Add:**

```json
{
  "basics": {
    "summary": "<p>17 years in enterprise...</p>",
    "summary_text": "17 years in enterprise...",
    "summary_variants": {
      "vibe_coding": "Full-stack vibe coder shipping production AI apps from prompt → deploy in days. INDUSIA.ai stack: Next.js 15 + FastAPI + Claude Sonnet 4.6. Demo Day Champion #1 — Outskill AI Generalist Fellowship. Batam, working globally.",
      "ai_automation": "AI Visual Inspection live on production lines at Evident Scientific (Olympus successor) and Novanta (NASDAQ:NOVT). Replacing $24K Keyence rigs with $19,950 deploys. 17 years enterprise → solo AI studio. Specialty: industrial CV + workflow automation that survives factory-floor reality.",
      "ai_video": "AI video generation pipeline operator — VEO 3, Sora, Runway, Kling. Built 7-beat narrative-arc engine with 4-stage validation (script → image → video → reference consistency). Champion of Outskill Demo Day with Sparkfluence: AI-Powered Platform for Viral Content Creation."
    }
  }
}
```

**Why three:** jobhunter scores each scraped job against all 3 variants and
picks the strongest match. The opening paragraph is the first thing the
hiring agent reads — generic openings tank conversion.

**Implementation:** add 3 textarea fields to the portfolio admin CMS (one
per variant). Cache the values; serve verbatim. No LLM at API time.

---

### 2. `work[]` — employment history, separate from `projects[]`

**Current:** `data.work` is absent. All 56 entries live in `data.projects`.

**Problem:** ATS scoring computes years-of-experience by summing
`work[].end_date - work[].start_date`. With `work` empty, it falls back
to `projects[]` and double-counts (one project per month inflates YoE
to ~50 years). The LLM parser currently has to re-bucket employment
out of project descriptions and frequently hallucinates (e.g. invents
"Senior AI Engineer at Outskill" because Outskill appears in 3 project
descriptions).

**Add:**

```json
{
  "work": [
    {
      "company": "INDUSIA.ai",
      "position": "Founder / Solo AI Engineer",
      "start_date": "2024-01",
      "end_date": null,
      "location": "Batam, Indonesia (remote-global)",
      "summary": "AI Visual Inspection deployments for industrial QC. Customers: Evident Scientific, Novanta.",
      "highlights": [
        {
          "text": "Replaced $24K Keyence rigs with $19,950 INDUSIA deploys at Evident Scientific (Olympus industrial successor)",
          "metrics": {"cost_saved_usd": 4050, "deployments": 1},
          "tags": ["industrial", "computer_vision", "qc"],
          "variant_hint": ["ai_automation"]
        }
      ],
      "tech_stack": ["Python", "PyTorch", "ONNX", "FastAPI", "Docker"]
    },
    {
      "company": "Evident Scientific (Olympus industrial successor)",
      "position": "AI Visual Inspection Vendor",
      "start_date": "2025-03",
      "end_date": null,
      "summary": "Production deployment of INDUSIA AI Visual Inspection on Evident assembly lines."
    }
    // ... actual employment history (PT roles before INDUSIA, etc.)
  ]
}
```

**Field requirements:**
- `company` (required, string)
- `position` (required, string)
- `start_date` (required, `YYYY-MM` or `YYYY-MM-DD`)
- `end_date` (`null` for current, otherwise same format)
- `summary` (required, plain text — 1-2 sentences)
- `highlights[]` (recommended, see schema below)
- `tech_stack[]` (recommended, list of concrete tools)

---

### 3. `skills{}` — categorized object, not flat tags

**Current:** Per-project `tags[]` exist (e.g. `["Computer Vision",
"Quality Control"]`) but no top-level `skills` object.

**Problem:** Consumer's ATS scorer at
[`backend/app/services/scorer_service.py`](https://github.com/alisadikinma/jobhunter/blob/master/backend/app/services/scorer_service.py)
keyword-matches the JD against `skills{}` directly. With `skills` absent,
LLM has to aggregate project tags + invent categories, which produces
non-deterministic groupings on every import.

**Add (top level of `data`):**

```json
{
  "skills": {
    "languages":     ["Python", "TypeScript", "JavaScript", "Go", "PHP", "SQL"],
    "frameworks":    ["FastAPI", "Next.js 15", "React 19", "Laravel", "PyTorch"],
    "ai_tools":      ["Claude Sonnet 4.6", "GPT-4", "VEO 3", "Sora", "Runway", "Kling", "n8n", "LangChain"],
    "cloud":         ["AWS", "GCP", "DigitalOcean", "Hostinger VPS", "Cloudflare"],
    "databases":     ["PostgreSQL", "MySQL", "Redis", "SQLite", "ChromaDB"],
    "infrastructure": ["Docker", "Docker Compose", "Traefik", "GitHub Actions", "Alembic"],
    "domain":        ["Computer Vision", "Industrial QC", "RAG", "AI Agents", "Vibe Coding", "Workflow Automation"]
  }
}
```

**Schema constraint:** `dict[str, list[str]]`. Categories are freeform but
should be stable across responses (don't rename `ai_tools` to `ai` between
calls — that breaks consumer caching).

---

### 4. `education[]` — currently absent

**Add:**

```json
{
  "education": [
    {
      "institution": "<your university>",
      "area": "Computer Science",
      "study_type": "Bachelor",
      "start_date": "2003",
      "end_date": "2007",
      "score": null,
      "courses": []
    }
  ]
}
```

If the answer is "self-taught + 17 years industry," return `education: []`
(empty list, not omitted) and the consumer renders nothing — no error.

---

## P1 — Data quality (LLM rescues but at cost)

### 5. Strip HTML from `summary` fields

**Current:**
```json
"summary": "<p>17 years in enterprise. Then AI rewrote the math...</p><p>I run <strong>INDUSIA.ai</strong> solo...</p>"
```

**Problem:** Consumer pipes this straight into the Claude prompt. HTML
markup eats ~30% of the token budget for zero semantic value.

**Fix — pick one:**

**Option A (preferred):** Add a parallel plain-text field, keep HTML for
rendering consumers:
```json
"summary":      "<p>17 years in enterprise...</p>",
"summary_text": "17 years in enterprise. Then AI rewrote the math on what one builder can ship..."
```

**Option B:** Strip HTML in `summary` directly and rename to
`summary_html` if the rendering consumers need it. Cleaner but breaks
existing API contract.

**Apply to:** `basics.summary`, `awards[].summary`, any future
`work[].summary` and `projects[].description` if HTML creeps in there.

---

### 6. Fix UTF-8 mojibake

**Current evidence (multiple fields):**
```json
"label":   "AI Solopreneur Studio � Founder of INDUSIA.ai",
"title":   "1st Place Winner � Global AI Demo Day 2026 (...)",
"summary": "Sparkfluence � AI-Powered Platform...",
"summary": "<p>...kompetisi AI startup<br>internasional..."
```

The `�` (U+FFFD REPLACEMENT CHARACTER) means a UTF-8 byte sequence got
decoded as cp1252 (or latin1) somewhere, then re-encoded as UTF-8.
Originals were probably `★`, `•`, `—`, `→`, or `·`.

**Likely culprits:**
- DB connection charset not `utf8mb4` (MySQL default `utf8` only handles
  3-byte sequences).
- PHP `json_encode()` without `JSON_UNESCAPED_UNICODE` flag.
- File read with `file_get_contents()` then implicit decode.
- Migration from one stack to another with charset mismatch.

**Fix:**
- DB: `ALTER DATABASE alisadikinma CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;` and same per `ALTER TABLE`.
- PDO DSN: `mysql:host=...;dbname=...;charset=utf8mb4`.
- Laravel: ensure `config/database.php` `'charset' => 'utf8mb4'` and
  `'collation' => 'utf8mb4_unicode_ci'`.
- JSON output: `json_encode($data, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES)`.
- Run a one-off cleanup migration on existing rows: replace `?` and `\xEF\xBF\xBD` with the originals (best done by hand, ~30 known instances).

---

### 7. Populate `projects[].highlights[]` and `metrics{}`

**Current:** All 56 projects return:
```json
{
  "highlights": [],
  "metrics": []
}
```

**Problem:** The consumer's CV tailor + cold-email skills rank
achievements by `metrics` strength (numbers > qualifiers > vague
claims). With both empty, the LLM has to invent achievements from the
`description` field — which produces generic "improved efficiency"
filler that hurts conversion.

**Target shape:**

```json
{
  "name": "Production AI-Powered Metal Walk-Through Monitoring CCTV",
  "highlights": [
    {
      "text": "Detects 12 defect classes in real-time on 24fps 4K CCTV streams",
      "metrics": {"defect_classes": 12, "fps": 24, "resolution": "4K"},
      "tags": ["computer_vision", "real_time"],
      "variant_hint": ["ai_automation"]
    },
    {
      "text": "Reduced manual QC inspection time by 90% across 3 production lines",
      "metrics": {"time_reduction_pct": 90, "lines_deployed": 3},
      "tags": ["roi", "qc"],
      "variant_hint": ["ai_automation"]
    },
    {
      "text": "Replaced $24K Keyence rig at $19,950 — $4,050 savings per deploy + 18-month support",
      "metrics": {"cost_saved_usd": 4050, "competitor_price_usd": 24000, "support_months": 18},
      "tags": ["roi", "competitive"],
      "variant_hint": ["ai_automation"]
    }
  ],
  "metrics": {
    "total_deployments": 4,
    "uptime_pct": 99.7,
    "first_deploy_date": "2025-03-15"
  }
}
```

**Per-highlight schema:**
- `text` (required, string, plain — no HTML)
- `metrics` (object, freeform `{key: number|string}`)
- `tags` (list of freeform strings)
- `variant_hint` (list, see #8 below — strict to 3 values)

**Project-level `metrics`:** aggregate numbers that apply to the project
as a whole (deploy count, total revenue, customer count, etc.).

---

## P2 — Cosmetic / consistency

### 8. Split `relevance_hint` → strict `variant_hint` + freeform `tags`

**Current:**
```json
"relevance_hint": ["ai_automation", "ai_agents"]
```

**Problem:** `ai_agents` is not a valid jobhunter variant. The schema
hard-locks `relevance_hint` to `Literal["vibe_coding", "ai_automation",
"ai_video"]`. Consumer LLM currently filters out invalid values, but
this means hint info is silently dropped.

**Fix:**

```json
{
  "variant_hint": ["ai_automation"],
  "tags": ["ai_agents", "computer_vision", "industrial"]
}
```

- `variant_hint` — strict list, values MUST be in
  `{"vibe_coding", "ai_automation", "ai_video"}`. Empty list allowed.
  Validate server-side before persisting.
- `tags` — freeform taxonomy (technology, domain, vertical). Anything
  goes.

This decouples "which jobhunter variant should bid on this" from
"what topics does this touch."

---

### 9. Add `tech_stack[]` per project (separate from `tags`)

**Current:** Per-project `tags` mixes categories ("Computer Vision",
"Quality Control") with what could be tech stack — but it's not actually
stack info, just topic labels.

**Doc claims** (contradicting reality):
```json
"tech_stack": ["Python", "LangChain", "n8n"]
```

**Add the field for real:**

```json
{
  "name": "...",
  "tags":       ["computer_vision", "industrial_qc", "real_time"],
  "tech_stack": ["Python", "PyTorch", "ONNX Runtime", "OpenCV", "FastAPI", "Docker"]
}
```

**Distinction:**
- `tags` = "what is this project about" (semantic categories — used by
  filters/search)
- `tech_stack` = "what was actually used to build it" (concrete tools —
  used by ATS keyword matching)

ATS scorers care intensely about the second, not the first.

---

### 10. Document or fix the `{success, data}` envelope

**Current API doc says:**
> JSON Resume v1.0.0 envelope. Use when the consumer parses fields
> programmatically...
> ```json
> {
>   "$schema": "https://jsonresume.org/schema/1.0.0/resume.json",
>   "basics": {...},
>   "work": [...]
> }
> ```

**Actual response:**
```json
{
  "success": true,
  "data": {
    "schema_version": "1.0.0",
    "generated_at": "2026-05-06T07:19:01Z",
    "basics": {...},
    "projects": [...],
    "awards": [...],
    "thought_leadership": [...]
  }
}
```

**Fix — pick one:**

**Option A (preferred):** Drop the `{success, data}` wrapper for
`/api/cv/export` and `/api/cv/master.md` (status code already conveys
success/failure). These endpoints are content-bearing, not action
endpoints. Keep the wrapper for POST/PUT/DELETE responses where it
makes sense.

**Option B:** Update the doc to match reality and add `data.` prefix to
all field references in the integration recipe.

---

## Final shape — what `/api/cv/export` should return

After all enhancements, this is the target response (drop wrapper per
#10, all P0+P1+P2 applied):

```json
{
  "schema_version": "2.0.0",
  "generated_at": "2026-05-06T07:19:01Z",
  "basics": {
    "name": "Ali Sadikin Ma",
    "label": "AI Solopreneur Studio · Founder of INDUSIA.ai",
    "email": null,
    "phone": null,
    "url": "https://alisadikinma.com",
    "summary":      "<p>17 years in enterprise...</p>",
    "summary_text": "17 years in enterprise...",
    "summary_variants": {
      "vibe_coding":   "...",
      "ai_automation": "...",
      "ai_video":      "..."
    },
    "location": {"city": null, "country": "Indonesia", "remote": true},
    "profiles": [
      {"network": "github",   "url": "https://github.com/alisadikinma"},
      {"network": "linkedin", "url": "https://linkedin.com/in/alisadikin"},
      {"network": "twitter",  "url": "https://twitter.com/alisadikinma"}
    ]
  },
  "work": [
    {
      "company": "INDUSIA.ai",
      "position": "Founder / Solo AI Engineer",
      "start_date": "2024-01",
      "end_date": null,
      "summary": "...",
      "highlights": [
        {
          "text": "Replaced $24K Keyence rigs with $19,950 INDUSIA deploys",
          "metrics": {"cost_saved_usd": 4050, "deployments": 1},
          "tags": ["industrial", "computer_vision"],
          "variant_hint": ["ai_automation"]
        }
      ],
      "tech_stack": ["Python", "PyTorch", "FastAPI"]
    }
  ],
  "education": [],
  "skills": {
    "languages":  ["Python", "TypeScript", "PHP"],
    "frameworks": ["FastAPI", "Next.js 15", "Laravel"],
    "ai_tools":   ["Claude Sonnet 4.6", "VEO 3", "Sora"],
    "cloud":      ["AWS", "Hostinger VPS"],
    "databases":  ["PostgreSQL", "MySQL"],
    "domain":     ["Computer Vision", "Industrial QC", "RAG"]
  },
  "projects": [
    {
      "name": "...",
      "description": "...",
      "url": "...",
      "industry": "AI",
      "tags":       ["computer_vision", "industrial_qc"],
      "tech_stack": ["Python", "PyTorch", "ONNX", "OpenCV"],
      "variant_hint": ["ai_automation"],
      "highlights": [
        {"text": "...", "metrics": {...}, "tags": [...], "variant_hint": [...]}
      ],
      "metrics": {"total_deployments": 4, "uptime_pct": 99.7},
      "start_date": "2025-03",
      "end_date": null
    }
  ],
  "awards": [
    {
      "title":        "1st Place Winner · Global AI Demo Day 2026 (Outskill AI Generalist Fellowship)",
      "awarder":      "OUTSKILL - INDIA",
      "date":         "2026-01-17",
      "summary":      "<p>...</p>",
      "summary_text": "Memenangkan 1st Place di Global AI Demo Day 2026...",
      "tags":         ["competition", "international"],
      "is_featured":  true
    }
  ],
  "thought_leadership": [
    {
      "title":        "Claude AI Jailbreak Gaslighting: Bagaimana Bom Bocor?",
      "url":          "https://alisadikinma.com/blog/...",
      "published_at": "2026-05-06",
      "topics":       ["technology", "ai_safety"],
      "excerpt":      "Plain-text excerpt..."
    }
  ]
}
```

---

## Validation contract

Once the above lands, the consumer can validate every response with
this minimal Pydantic model (excerpted from `MasterCVContent`):

```python
from typing import Literal
from pydantic import BaseModel, Field

Variant = Literal["vibe_coding", "ai_automation", "ai_video"]

class SummaryVariants(BaseModel):
    vibe_coding: str
    ai_automation: str
    ai_video: str

class Highlight(BaseModel):
    text: str = Field(min_length=1)
    metrics: dict | None = None
    tags: list[str] = Field(default_factory=list)
    variant_hint: list[Variant] = Field(default_factory=list)

class WorkEntry(BaseModel):
    company: str
    position: str
    start_date: str
    end_date: str | None = None
    summary: str
    highlights: list[Highlight] = Field(default_factory=list)
    tech_stack: list[str] = Field(default_factory=list)

class ApiCvExport(BaseModel):
    schema_version: str
    generated_at: str
    basics: dict  # see Basics model
    work: list[WorkEntry]
    education: list[dict]
    skills: dict[str, list[str]]
    projects: list[dict]
    awards: list[dict]
    thought_leadership: list[dict]
```

If `ApiCvExport.model_validate(response.json())` passes, the consumer
imports in <1s with zero LLM cost. If it fails, the error message points
at the exact field that needs fixing on the API side.

---

## Out of scope (for now)

- Pagination — 56 projects fits in one ~50KB response. Revisit at 200+.
- Field-level locale (`summary_id`, `summary_en`) — the markdown endpoint
  already does English with silent ID fallback, that's fine.
- Webhook on CV update — consumer polls with ETag, ETag stays fresh, no
  need for push.
- `cv:read-pii` token scope for email/phone — jobhunter sources email
  from `MAIL_FROM_ADDRESS` env, no need yet.

---

## Migration order (suggested)

1. **Schema additions** — add empty `work[]`, `skills{}`, `education[]`
   fields to the response. Existing consumers ignore unknown fields.
   (No-op for jobhunter since the LLM parser already produces these.)
2. **`summary_variants`** — add 3 textareas to admin CMS, populate, ship.
   This alone removes the LLM dependency for `basics`.
3. **Populate `work[]`** from existing project records. Most projects
   probably belong under one of 3-4 employment buckets.
4. **HTML strip + mojibake fix** — server-side, one PR.
5. **Per-project `highlights` + `metrics`** — ongoing data entry. Build
   it into the project edit form.
6. **`variant_hint` / `tech_stack` split** — schema cleanup, one PR.
7. **Drop envelope** OR update doc — final consistency pass.
