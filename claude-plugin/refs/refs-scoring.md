# Scoring Rubric — 3-Variant Classifier

## Scoring weights (0–100 total)

| Dimension | Weight | Notes |
|-----------|--------|-------|
| Skill match | 40 | Overlap between JD tech_stack/keywords and master_cv.skills/highlights. |
| Role fit | 25 | Seniority + responsibilities alignment (e.g. reject "junior" for a staff-level CV). |
| Remote / location | 15 | Remote > hybrid > onsite unless a target region matches. |
| Salary | 10 | 100 if mid-salary ≥ target; linear scale down to 0 at 60% of target. |
| Company signal | 10 | Funded startup, known brand, or clear product beats anonymous agencies. |

Score each dimension separately, weight-sum to 0–100. Populate
`score_reasons` with the per-dimension breakdown in the callback result.

## Variant classification

After scoring, assign the most-likely variant (or `null` if none passes
its threshold):

### vibe_coding (threshold: 0.40 confidence)

Signal keywords — presence boosts confidence:

`claude code`, `claude cli`, `cursor`, `rapid prototyping`,
`ship fast`, `founding engineer`, `full-stack AI`, `mvp builder`,
`vibe coding`, `0 to 1`, `solo engineer`, `product-minded`

### ai_automation (threshold: 0.55 confidence)

Signal keywords:

`automation engineer`, `workflow automation`, `n8n`, `zapier`,
`MCP server`, `langchain`, `langgraph`, `llm pipeline`,
`agents`, `agentic workflow`, `claude cli`, `pipeline orchestration`

### ai_video (threshold: 0.60 confidence)

Signal keywords:

`runway`, `veo`, `pika`, `nano banana`, `generative video`,
`ai video`, `video pipeline`, `stable diffusion video`,
`ai creative`, `synthetic media`

## Tie-breaker

Priority order when multiple variants tie on confidence:
`vibe_coding > ai_automation > ai_video` (per brainstorm decision #4).

## Match keywords

Return the top 5-10 JD keywords that also appear (case-insensitive) in
master CV. These power the "missing keywords" UI later.

## Output shape

```json
{
  "scores": [
    {
      "job_id": 123,
      "relevance_score": 87,
      "suggested_variant": "vibe_coding",
      "score_reasons": {
        "skill_match": 36,
        "role_fit": 22,
        "remote": 15,
        "salary": 8,
        "company": 6
      },
      "match_keywords": ["claude code", "fastapi", "next.js", "typescript"]
    }
  ]
}
```
