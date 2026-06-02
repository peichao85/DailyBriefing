# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DailyBriefing is an automated daily Tech & AI news briefing system. It researches, curates, and publishes Simplified Chinese briefings as both a PDF presentation and an interactive web interface, running daily via cron and powered by Claude Code skills.

## Pipeline Architecture

Three independent briefings, each its own cron job and entry script. Shared bash
lives in `scripts/briefing-common.sh` (env setup, `run_stage`, `commit_and_push`
with manifest rebuild + rebase-safe push). Each script rebuilds `web/manifest.json`
from disk and commits/pushes its own outputs.

```
run-ai-briefing.sh:   Research ($20) ──→ PDF Builder ($7)  ──→ commit & push  (web/AI, pdf/AI, research_results/AI)
                                      └─→ Web Builder ($5) ──┘
run-github-trending.sh: GitHub Trending ($3) ─────────────→ commit & push  (web/GitHub, research_results/GitHub)
run-us-stocks-briefing.sh: --check-only guard → US Stocks ($15) → commit & push  (web/USStocks, research_results/USStocks)
```

- In the AI script, **Research** must finish before the PDF/Web builders, which run in parallel.
- GitHub and US-stocks are best-effort and run on their own schedules (see `scripts/setup-cron.sh`).
- The US-stocks pre-flight (`fetch_market_data.py --check-only`, exit 3) skips weekends/holidays/same-day re-runs.
- Each stage is a Claude Code skill in `skills/`.

## Commands

```bash
# Run an individual briefing end-to-end (research/build → commit & push)
./scripts/run-ai-briefing.sh
./scripts/run-github-trending.sh
./scripts/run-us-stocks-briefing.sh

# Install the daily cron jobs (AI 06:58 SH, GitHub 08:30 SH,
# US-stocks 11:00 SH Apr–Oct / 12:00 SH Nov–Mar ≈ 7h after US close)
./scripts/setup-cron.sh

# Run individual skill stages by hand
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
- **Automatic git commit messages** (one per briefing script): `Daily AI briefing: YYYY-MM-DD`, `Daily GitHub trending: YYYY-MM-DD`, `Daily US stocks recap: YYYY-MM-DD`. Each commits only its own `web/<cat>`, `research_results/<cat>`, (and `pdf/AI` for AI) plus the rebuilt `web/manifest.json`. Log files under `research_results/*/logs/` are never pushed.

## Data Schemas

**`web/manifest.json`** — registry of available dates, sorted newest first. Updated by web builder.

**`web/AI/YYYY-MM-DD/data.json`** — per-day web content with items containing: `id`, `title`, `source`, `source_name`, `story_key`, `event_date`, `summary`, `detail`, `key_quotes`, `significance`, `links`, `image`, `image_type`, `tags`, `category`.

**`research_results/AI/YYYY-MM-DD/data.json`** — full research output consumed by both builders.

## Environment Requirements

- Claude Code CLI, Node.js/npm, Python 3 with `python-pptx`, LibreOffice (`soffice`), Poppler (`pdftoppm`), Chinese fonts (Noto Sans CJK or similar)
- Bash timeout env vars set in `scripts/briefing-common.sh`: `BASH_DEFAULT_TIMEOUT_MS=600000` (10min), `BASH_MAX_TIMEOUT_MS=900000` (15min)

## Skills System

Skills live in `skills/*/SKILL.md` and are invoked via Claude Code. Each skill has a defined budget and step-by-step execution guide:

| Skill | Purpose | Budget |
|-------|---------|--------|
| `ai_research` | Scan 50+ sources, curate JSON + images | $20 |
| `ai_pdf_builder` | Build PPTX, convert to PDF, QA visually | $5 |
| `ai_web_builder` | Transform to web JSON, optimize images, update manifest | $5 |
| `daily_AI_briefing` | Orchestrate all three stages in sequence | Sum of above |
| `pptx` | Dependency skill for all PPTX creation/editing | (used by pdf_builder) |
