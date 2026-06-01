# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DailyBriefing is an automated daily Tech & AI news briefing system. It researches, curates, and publishes Simplified Chinese briefings as both a PDF presentation and an interactive web interface, running daily via cron and powered by Claude Code skills.

## Pipeline Architecture

```
Stage 1: Research ($20) ──→ Stage 2: PDF Builder ($5)  ──→ git commit & push
                         └──→ Stage 3: Web Builder ($5) ──┘
```

- **Research** must complete before builders start. PDF and Web builders run in parallel.
- Research outputs to `research_results/AI/YYYY-MM-DD/` (git-tracked).
- PDF outputs to `pdf/AI/` (git-tracked). Web outputs to `web/AI/` + `web/manifest.json` (git-tracked).
- Each stage is a Claude Code skill in `skills/`. The orchestrator is `skills/daily_AI_briefing/`.

## Commands

```bash
# Run full pipeline (research → parallel PDF+web → git push)
./scripts/run-briefing.sh

# Install daily cron job (7:36 AM UTC)
./scripts/setup-cron.sh

# Run individual stages
claude -p "Run the ai_research skill for today"
claude -p "Run the ai_pdf_builder skill for today"
claude -p "Run the ai_web_builder skill for today"
```

## Tech Stack

- **Web frontend**: Vanilla HTML/CSS + vendored Alpine.js (no build step, no CDN)
- **PDF generation**: pptxgenjs (Node.js) → LibreOffice `soffice` → PDF, with `pdftoppm` for QA
- **Hosting**: GitHub Pages from `main` branch root (`index.html` at repo root)
- **Automation**: Claude Code CLI with `--dangerously-skip-permissions` in cron

## Key Conventions

- **Language**: All user-facing content is Simplified Chinese with English proper nouns/technical terms.
- **Web is a superset of PDF**: Web includes more items and detail; PDF is condensed to 10-15 slides.
- **No external dependencies at runtime**: Alpine.js is vendored in `web/js/`, fonts in `web/fonts/`. No CDN calls.
- **Dark theme**: Background `#0A1628`, accent `#00C2FF`, body text `#CBD5E1`. Defined in `web/css/style.css` and inline in `index.html`.
- **Image optimization for web**: Max 200KB, max 800px width, JPEG quality 85%.
- **Automatic git commit message format**: `Daily AI briefing: YYYY-MM-DD` (commits `research_results/`, `web/`, and `pdf/` directories).

## Data Schemas

**`web/manifest.json`** — registry of available dates, sorted newest first. Updated by web builder.

**`web/AI/YYYY-MM-DD/data.json`** — per-day web content with items containing: `id`, `title`, `source`, `source_name`, `story_key`, `event_date`, `summary`, `detail`, `key_quotes`, `significance`, `links`, `image`, `image_type`, `tags`, `category`.

**`research_results/AI/YYYY-MM-DD/data.json`** — full research output consumed by both builders.

## Environment Requirements

- Claude Code CLI, Node.js/npm, Python 3 with `python-pptx`, LibreOffice (`soffice`), Poppler (`pdftoppm`), Chinese fonts (Noto Sans CJK or similar)
- Bash timeout env vars set in `scripts/run-briefing.sh`: `BASH_DEFAULT_TIMEOUT_MS=600000` (10min), `BASH_MAX_TIMEOUT_MS=900000` (15min)

## Skills System

Skills live in `skills/*/SKILL.md` and are invoked via Claude Code. Each skill has a defined budget and step-by-step execution guide:

| Skill | Purpose | Budget |
|-------|---------|--------|
| `ai_research` | Scan 50+ sources, curate JSON + images | $20 |
| `ai_pdf_builder` | Build PPTX, convert to PDF, QA visually | $5 |
| `ai_web_builder` | Transform to web JSON, optimize images, update manifest | $5 |
| `daily_AI_briefing` | Orchestrate all three stages in sequence | Sum of above |
| `pptx` | Dependency skill for all PPTX creation/editing | (used by pdf_builder) |
