---
name: daily_AI_briefing
description: "Generate a daily Tech & AI briefing by running the full pipeline: research, PDF builder, and web builder. This is the orchestrator skill that coordinates all three stages. Use this skill when the user asks for a daily AI briefing, tech news summary, AI news deck, or morning briefing."
---

# Daily Tech & AI Briefing — Orchestrator

Run the full daily AI briefing pipeline. This skill coordinates three stages in sequence:

## Pipeline

### Stage 1: Research
Run the `ai_research` skill to gather and curate today's AI news from 50+ sources.
- Output: `research_results/AI/YYYY-MM-DD/data.json` + images

### Stage 2: PDF Builder
Run the `ai_pdf_builder` skill to create the presentation PDF.
- Input: `research_results/AI/YYYY-MM-DD/`
- Output: `pdf/AI/daily-tech-ai-briefing-YYYY-MM-DD-cn.pdf`

### Stage 3: Web Builder
Run the `ai_web_builder` skill to generate web content.
- Input: `research_results/AI/YYYY-MM-DD/`
- Output: `web/AI/YYYY-MM-DD/data.json` + images, updated `web/manifest.json`

## Execution

Run the stages in order. If any stage fails, stop and report the error.

1. Execute the `ai_research` skill for today's date
2. Execute the `ai_pdf_builder` skill for today's date
3. Execute the `ai_web_builder` skill for today's date

After all stages complete, report what was generated.

## Notes

- Do NOT delete `research_results/` — it is managed manually
- The PDF and web content are both committed to git
- The web content is a superset of the PDF content
