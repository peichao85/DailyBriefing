# Daily Briefing Web Page — Design Spec

## Context

The DailyBriefing project generates daily AI news briefings as PDF presentations via a cron job. Currently the research and PDF generation are coupled in one skill, and there is no web presence beyond a placeholder `index.html`. We want to:

1. Build a GitHub Pages website that displays daily briefings as an interactive web page
2. Restructure the project so research, PDF, and web are independent stages sharing a common data source
3. Start with the AI category only; tabs for other categories (finance, politics) will be added later

## Architecture

### Three-Stage Pipeline

```
ai_research skill
    │
    ▼
research_results/AI/YYYY-MM-DD/    (temporary, gitignored, manual cleanup)
    │
    ├──► ai_pdf_builder skill  ──►  pdf/AI/*.pdf
    │
    └──► ai_web_builder skill  ──►  web/AI/YYYY-MM-DD/data.json + img/
                                    web/manifest.json
```

### Directory Structure

```
DailyBriefing.git/
├── index.html                     ← entry point at repo root, served by GitHub Pages
│
├── research_results/              ← gitignored, manual cleanup
│   └── AI/
│       └── YYYY-MM-DD/
│           ├── data.json          ← full research data
│           └── img/
│
├── web/                           ← web assets (CSS, JS, data), in git
│   ├── js/
│   │   └── alpine.min.js         ← vendored locally (~43KB)
│   ├── css/
│   │   └── style.css
│   ├── manifest.json
│   └── AI/
│       └── YYYY-MM-DD/
│           ├── data.json          ← web-friendly curated subset
│           └── img/               ← optimized images
│
├── pdf/                           ← in git
│   └── AI/
│       └── daily-tech-ai-briefing-YYYY-MM-DD-cn.pdf
│
├── scripts/
├── skills/
├── docs/
└── .gitignore                     ← includes research_results/
```

## Web Page Design

### Technology

- Vanilla HTML/CSS with Alpine.js (vendored locally, no CDN)
- No build step — works directly with GitHub Pages
- All UI text in Simplified Chinese

### Color Scheme (Dark Theme)

- Background: `#0A1628`
- Card background: `#132340`
- Accent: `#00C2FF`
- Body text: `#CBD5E1`
- Secondary text: `#94A3B8`
- Headings: `#FFFFFF`

### Layout

**Header:**
- Title: "每日简报"
- Date picker: left/right arrows for prev/next day + clicking the date text opens a mini calendar popup
- Calendar popup highlights available dates, greys out unavailable ones

**Content area:**
- Responsive card grid: 2-3 columns on desktop, 1 on mobile
- Each card shows: title, source, brief summary, optional image
- Clicking a card expands it in-place (pushes other cards down) with smooth animation
- Expanded view shows: full detail, key quotes, significance, source links
- Expanded card gets a brighter border/background; other cards fade slightly
- Smooth-scroll expanded card to top of viewport
- Click again or close button to collapse

**Footer:**
- Simple copyright line

## Data Schemas

### web/manifest.json

```json
{
  "categories": {
    "AI": {
      "label": "AI 科技",
      "dates": ["2026-04-09", "2026-04-08"]
    }
  }
}
```

### web/AI/YYYY-MM-DD/data.json

```json
{
  "date": "2026-04-08",
  "category": "AI",
  "title": "今日最大看点：OpenAI 发布 GPT-5",
  "items": [
    {
      "id": "1",
      "title": "代码手写时代正式终结",
      "source": "@karpathy",
      "source_name": "Andrej Karpathy",
      "summary": "简短摘要，显示在卡片上...",
      "detail": "展开后的详细内容，可以是多段...",
      "key_quotes": ["原文引用..."],
      "significance": "为什么这条消息重要...",
      "links": ["https://..."],
      "image": "img/karpathy-post.png",
      "tags": ["frontier_leaders", "coding"]
    }
  ]
}
```

## Skill Refactoring

### Current: `daily_AI_briefing` (skills/daily_AI_briefing/SKILL.md)

Split into three skills:

### 1. `ai_research` (new)
- Steps 1 & 2 of the current skill: web search across 50 accounts + curation
- Output: `research_results/AI/YYYY-MM-DD/data.json` + `research_results/AI/YYYY-MM-DD/img/`
- Contains the richest data — full investigation notes, all quotes, raw images

### 2. `ai_pdf_builder` (refactored from current)
- Steps 3 & 4 of the current skill: PPTX creation + PDF conversion
- Input: reads from `research_results/AI/YYYY-MM-DD/`
- Output: `pdf/AI/daily-tech-ai-briefing-YYYY-MM-DD-cn.pdf`
- Most condensed version — 10-15 slides, curated highlights only

### 3. `ai_web_builder` (new)
- Reads from `research_results/AI/YYYY-MM-DD/`
- Transforms into web-friendly JSON + optimized/compressed images
- Output: `web/AI/YYYY-MM-DD/data.json` + `web/AI/YYYY-MM-DD/img/`
- Updates `web/manifest.json` to include the new date
- Web is a superset of PDF — more detail, more items

## GitHub Pages Deployment

GitHub Pages serves directly from the `main` branch root.

- `index.html` at repo root is the entry point
- All other web assets under `web/` are referenced with relative paths (e.g., `web/css/style.css`)
- No separate branch or deploy step needed — push to `main` and it's live

## Cron Job Update

`scripts/run-ai-briefing.sh` updated to run:

```
ai_research  →  ai_pdf_builder
             →  ai_web_builder
             →  git add + commit + push (web/ and pdf/ only)
```

No auto-cleanup of `research_results/`.

## Implementation Scope

1. Restructure directories: move `daily_briefing/AI/pdf/` to `pdf/AI/`, create `web/` structure, update `.gitignore`
2. Build the web page: `web/index.html`, `web/css/style.css`, vendor Alpine.js to `web/js/`
3. Create `ai_web_builder` skill
4. Refactor `daily_AI_briefing` into `ai_research` + `ai_pdf_builder`
5. Update `scripts/run-ai-briefing.sh` for the new three-stage pipeline
6. Configure GitHub Pages to serve from `main` branch root (index.html at root, assets under web/)

## Verification

1. Create a sample `research_results/AI/2026-04-08/data.json` with test data
2. Run the `ai_web_builder` skill manually to generate `web/AI/2026-04-08/`
3. Open `web/index.html` in a browser and verify:
   - Date picker shows 2026-04-08 as the latest date
   - Card grid renders with correct content
   - Clicking a card expands in-place with detail view
   - Left/right arrows work (disabled when no more dates)
   - Calendar popup shows available dates
   - Responsive layout works on mobile viewport
4. Verify `ai_research` and `ai_pdf_builder` skills work independently
5. Run the full cron pipeline end-to-end
