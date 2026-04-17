# CV Tailoring — 3 Variant Presets + ATS Rules

## ATS rules (apply to all variants)

- **Single column** — no tables, no sidebars. ATS parsers still trip on them.
- **Standard section headers** — `Summary`, `Experience`, `Education`,
  `Skills`, `Projects`. No creative renames.
- **Keyword coverage** — target 70-80% overlap with JD keywords; include
  BOTH acronym and full term on first use (e.g. "Large Language Models (LLMs)").
- **Fonts** — resolved at DOCX-render time by Pandoc template. Don't
  emit inline styling in the markdown.
- **No graphics / icons / emoji.** Bullet characters only.
- **Dates** — consistent `YYYY-MM` or `Month YYYY` across the doc.
- **Length** — one page for ≤8 years exp, two pages for ≥10 years;
  never three.

## Bullet ranking algorithm

For each highlight in `master_cv.work[*].highlights[]`, compute:

```
score = 3 * keyword_overlap(highlight, jd)
      + 2 * relevance_hint_match(highlight, variant)
      + 1 * metric_presence(highlight)
      + 0.5 * recency_factor(work_entry)
```

Pick top **3-5 bullets per work entry** after ranking. Always keep at
least one bullet with a quantified metric if available.

## Confidence thresholds

Classification confidence must exceed these before a variant is chosen;
otherwise return `variant_used: "no_match"` and surface a clear reason:

| Variant | Min confidence |
|---------|----------------|
| vibe_coding | 0.40 |
| ai_automation | 0.55 |
| ai_video | 0.60 |

## Variant 1 — `vibe_coding` (priority 1)

### Header tagline

`"{name} — Senior AI-Era Full-Stack Engineer · Ships in days, not months"`

### Summary source

Use `basics.summary_variants.vibe_coding` verbatim unless JD demands a
tighter rewrite (≤3 sentences).

### Tag priority (highlights with these tags float to top)

`claude-code`, `rapid-build`, `full-stack`, `saas`, `0-to-1`,
`founding-engineer`, `mvp-builder`, `product-minded`

### Skills section order

1. AI Tooling (Claude Code, Cursor, MCP)
2. Full-Stack (TypeScript, Next.js, FastAPI)
3. Automation (n8n, pipelines)
4. Generative Media (if relevant)

### Portfolio filter rules

Prefer assets with `relevance_hint` containing `vibe_coding`. Cap at 4
items. If fewer than 4 match, backfill with generic `full-stack` assets.

## Variant 2 — `ai_automation` (priority 2)

### Header tagline

`"{name} — AI Automation Engineer · Claude CLI + MCP + n8n"`

### Summary source

`basics.summary_variants.ai_automation`.

### Tag priority

`automation`, `claude-cli`, `pipeline`, `mcp`, `n8n`, `langchain`,
`agents`, `ops-impact`

### Skills section order

1. Automation (n8n, LangChain, LangGraph, APScheduler)
2. AI Tooling (Claude CLI, MCP servers, agents)
3. Infrastructure (Docker, PostgreSQL, Redis)
4. Full-Stack

### Portfolio filter rules

Assets with `relevance_hint` containing `ai_automation`. Prioritize
pieces with quantified ops impact (`40h/week saved`, `$8k/mo`, etc).

## Variant 3 — `ai_video` (priority 3)

### Header tagline

`"{name} — AI Video Pipeline Architect · Runway · Veo · Nano Banana"`

### Summary source

`basics.summary_variants.ai_video`.

### Tag priority

`video`, `image-generation`, `runway`, `veo`, `pipeline`,
`generative-media`, `creative-automation`

### Skills section order

1. Generative Media (Runway, Veo, Nano Banana, SDXL-video)
2. Automation (pipeline orchestration)
3. AI Tooling
4. Full-Stack

### Portfolio filter rules

Assets with `relevance_hint` containing `ai_video`. Max 4, featured
first.

## Output shape (callback payload)

```json
{
  "tailored_markdown": "...full CV markdown...",
  "tailored_json": { "basics": {...}, "work": [...], ... },
  "keyword_matches": ["claude-code", "fastapi", "..."],
  "missing_keywords": ["kubernetes", "..."],
  "variant_used": "vibe_coding",
  "confidence": 0.87,
  "selected_portfolio_ids": [3, 7, 9, 11],
  "rejected_keywords_reason": null
}
```

If `variant_used: "no_match"`, also include `rejected_keywords_reason`
explaining why all three variants fell below threshold.
