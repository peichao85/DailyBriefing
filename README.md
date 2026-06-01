# Daily AI Briefing

**[https://peichao85.github.io/DailyBriefing/](https://peichao85.github.io/DailyBriefing/)**

Automated daily Tech & AI news briefing system. Researches, curates, and publishes bilingual (Chinese/English) briefings as both a polished PDF presentation and an interactive web interface — powered by Claude Code.

## How It Works

A three-stage pipeline runs daily via cron:

```
Stage 1: Research ──→ Stage 2: PDF Builder ──→ Git commit & push
                  └──→ Stage 3: Web Builder ──┘
```

1. **Research** — Scans 50+ X/Twitter accounts and major outlets, curates the top findings into a structured JSON dataset with images
2. **PDF Builder** — Selects the 10–15 most impactful items, generates a Chinese PPTX presentation, and converts to PDF (runs in parallel with Stage 3)
3. **Web Builder** — Transforms research data into web-friendly JSON, optimizes images, and updates the date manifest (runs in parallel with Stage 2)

After all stages complete, the pipeline commits and pushes changes to GitHub, where the web interface is served via GitHub Pages.

## Project Structure

```
├── index.html                  ← Web entry point (GitHub Pages root)
├── scripts/
│   ├── run-briefing.sh      ← Main pipeline orchestration script
│   └── setup-cron.sh           ← Installs daily cron job
├── skills/                     ← Claude Code skills (pipeline stages)
│   ├── ai_research/            ← Stage 1: research & data gathering
│   ├── ai_pdf_builder/         ← Stage 2: PPTX → PDF generation
│   ├── ai_web_builder/         ← Stage 3: web content generation
│   └── daily_AI_briefing/      ← Orchestrator (invokes all 3 stages)
├── pdf/AI/                     ← Generated PDFs (git-tracked)
├── web/                        ← Web assets (git-tracked)
│   ├── AI/<date>/data.json     ← Per-day web content
│   ├── manifest.json           ← Available dates registry
│   ├── css/style.css           ← Dark theme styling
│   ├── js/alpine.min.js        ← Vendored Alpine.js
│   └── fonts/                  ← Display fonts
└── research_results/           ← Temporary research data (gitignored)
```

## Tech Stack

- **Automation**: Claude Code CLI + Bash scripts
- **Web**: Vanilla HTML/CSS + Alpine.js (no build step)
- **PDF**: Python `python-pptx` → LibreOffice PDF conversion
- **Hosting**: GitHub Pages (served from `main` branch root)
- **Scheduling**: System cron

## Prerequisites

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI
- Node.js and npm
- Python 3 with `python-pptx`
- LibreOffice (for `soffice` PDF conversion)
- Chinese fonts (e.g., Noto Sans CJK) for PDF text rendering
- Git

## Usage

### Run the full pipeline manually

```bash
./scripts/run-briefing.sh
```

### Set up the daily cron job

```bash
./scripts/setup-cron.sh
```

This installs a cron entry that runs the pipeline daily at 7:36 AM UTC.

### Run individual stages via Claude Code

```bash
# Research only
claude -p "Run the ai_research skill for today"

# PDF generation only (requires research data)
claude -p "Run the ai_pdf_builder skill for today"

# Web content only (requires research data)
claude -p "Run the ai_web_builder skill for today"

# Full pipeline
claude -p "Run the daily_AI_briefing skill"
```

## Web Interface

The web interface is a single-page app with:

- **Dark theme** with a cyan accent color
- **Responsive card grid** — hero, featured, and standard card layouts
- **Date navigation** — calendar popup with arrows, highlights available dates
- **Expandable cards** — click to reveal full analysis, key quotes, and links
- **Tag-based theming** — color-coded by topic (model releases, AI coding, safety, agents, etc.)
- **PDF download** — direct link to the day's PDF briefing

## Configuration

| Setting | Value | Location |
|---------|-------|----------|
| Cron schedule | `36 07 * * *` (7:36 AM UTC daily) | `scripts/setup-cron.sh` |
| Research budget | $20 USD per run | `skills/ai_research/` |
| PDF budget | $5 USD per run | `skills/ai_pdf_builder/` |
| Web budget | $5 USD per run | `skills/ai_web_builder/` |
| Bash timeout | 10 min default / 15 min max | `scripts/run-briefing.sh` |

## License

Private project.
