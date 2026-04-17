# Cold Email — Structure + 3-Variant Tone Adjustments

## 5-part structure (all emails)

1. **Subject line** — under 10 words. Curious > generic ("Quick note on
   your Q3 Claude CLI work" > "Interested in your AI role"). NO clickbait.
2. **Personalized opener** — 1-2 sentences. Reference something specific
   to the company from its About page or recent news (that's why Phase
   5.5 enrichment matters). Never "I noticed your company..."
3. **Value prop with quantified result** — one bullet or sentence: what
   you built, for whom, measurable outcome. Always include a number.
4. **Social proof** — short link or one-liner: portfolio, GitHub, prior
   client logo. No long list.
5. **CTA asking for conversation, not a job** — "15-min chat to swap
   notes on [X]?" outperforms "Would you consider me for the role?"

## Word count

**Initial: 75-150 words.** Anything longer gets skimmed.

## Variant tone

### vibe_coding

Velocity narrative. Mention specific time-to-ship numbers. Reference
Claude Code / Cursor / rapid prototyping. Lead with "I ship fast" angle.

> Example opener: "Saw your founding-engineer post — curious about your
> Claude Code setup. Shipped a similar agent-orchestration tool in 11
> days at my last agency (one solo sprint)."

### ai_automation

Operational impact narrative. Lead with quantified ops wins (hours
saved, processes replaced, $/mo cost reductions). Reference pipelines,
MCP servers, n8n.

> Example opener: "Read your post on the automation engineer role.
> Your team sounds like the workflow-first crowd. Last quarter I
> replaced a 40h/week manual ops cycle with an n8n + Claude CLI
> pipeline — happy to walk you through it."

### ai_video

Pipeline-infrastructure angle (NOT creative-first). Talk about
throughput, cost-per-clip, reproducibility. Reference Runway / Veo /
Nano Banana.

> Example opener: "Noticed your team is scaling AI video production.
> I run a Veo + Runway pipeline producing 40 branded clips/month at
> <$2/clip — would love to compare notes on the pipeline side."

## Follow-up sequence

### Follow-up 1 — Day 5

Short. 40-60 words. Same thread (same subject). ONE new data point
the initial didn't include. End with: "Still open to that quick chat?"

### Follow-up 2 — Day 10

Short. 30-50 words. Flip the approach: drop a new concrete idea or
resource relevant to their stack. Close with a soft "happy to park
this if timing is off — no hard feelings."

After follow-up 2 with no reply → application moves to `ghosted`.

## Output shape (callback payload)

```json
{
  "initial": {
    "subject": "Quick note on your Claude CLI work",
    "body": "..."
  },
  "follow_up_1": { "subject": "...", "body": "..." },
  "follow_up_2": { "subject": "...", "body": "..." },
  "strategy": "vibe_coding / velocity-first",
  "personalization_notes": [
    "referenced: recent LinkedIn post about Claude Code migration",
    "referenced: their team's agent-orchestration repo on GitHub"
  ]
}
```
