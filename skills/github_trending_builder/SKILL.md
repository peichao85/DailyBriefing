---
name: github_trending_builder
description: "Build the GitHub Trending daily briefing. Runs a Python helper that queries the official GitHub REST API for hot and rising AI/dev-tool repos, then generates Chinese summaries and writes the web data file. Use this skill when the user asks to refresh GitHub trending, build the GitHub trending web data, or run the GitHub trending phase of the daily pipeline."
---

# GitHub Trending Builder — Daily Briefing Web Content

Build `web/GitHub/<date>/data.json` for the **GitHub 趋势** tab of the Daily Briefing web page. Uses only the official GitHub REST API (stateless) plus one Claude pass for Chinese summarization.

The tab shows two sections:
- **新晋热门** — 10 repos *created in the last 7 days*, ranked by absolute stars.
- **上升之星** — 10 *existing* repos ranked by stars gained in the last 7 days (computed via the stargazers endpoint with `Accept: application/vnd.github.star+json`).

Scoped to AI/ML + developer-tool topics.

## Input

`$DATE` in YYYY-MM-DD (the date argument passed by the user or orchestrator). Default: today UTC.

## Step 1: Run the Python fetcher

Execute the helper script with the project root set so output paths resolve correctly. The script handles auth resolution (`gh auth token` → `$GITHUB_TOKEN` → unauth), the API dance, the stargazers-pagination delta math, owner-avatar downloads (written directly to `web/GitHub/<date>/img/`), and writing `research_results/GitHub/<date>/raw.json`.

```bash
cd <project_root>
python3 skills/github_trending_builder/scripts/fetch_github_trending.py --date <date>
```

**Expect:**
- `research_results/GitHub/<date>/raw.json` created
- `web/GitHub/<date>/img/*.jpg` populated (one per selected repo; may be fewer if some downloads fail)
- Log output showing `new_hot=10 rising=10` (or fewer if filtering left too few candidates)

**If the script fails:**
- Network/auth issue → the skill should log and exit non-zero (but the orchestrator runs this stage as non-fatal, so the overall pipeline still succeeds).
- If fewer than 5 repos in either section → log a warning but continue; the UI renders whatever we have.

## Step 2: Read the raw data

Read `research_results/GitHub/<date>/raw.json`. It has the shape:

```json
{
  "date": "2026-04-10",
  "sections": [
    {
      "id": "new_hot",
      "label": "新晋热门",
      "subtitle": "过去 7 天新建仓库按星数排序",
      "repos": [
        {
          "owner": "...", "repo": "...", "full_name": "owner/repo",
          "html_url": "...", "description": "...",
          "topics": ["ai", "llm"], "stars": 12345, "forks": 567,
          "language": "Python", "created_at": "...", "pushed_at": "...",
          "avatar_url": "...", "readme_excerpt": "first 800 chars...",
          "stars_gained": null, "avatar_path": "img/owner-repo.jpg"
        }
      ]
    },
    { "id": "rising_stars", "label": "上升之星", ... }
  ]
}
```

## Step 3: Generate Chinese content (single pass)

For each repo in both sections, write Chinese content based on the English `description` + `readme_excerpt` + `topics`. Output fields:

- **`title`** — Short Chinese title (12-25 chars). Should convey what the repo *does*, not just its name. Example: `OpenClaw：开源法律 AI 助手突破 10K stars`. Include the repo name (Latin letters OK) so readers can find it.
- **`summary`** — One Chinese sentence (~50-80 chars). What problem the repo solves, who it's for.
- **`detail`** — 2-3 Chinese sentences (~150-250 chars). Capabilities, tech stack, notable features. Ground every statement in the README excerpt or description — do not invent features.
- **`significance`** — One Chinese sentence explaining why it's trending this week. For `new_hot`: reference total stars (e.g., `发布一周即收获 8,230 stars，位列本周新晋第一`). For `rising_stars`: reference the `stars_gained` value (e.g., `本周新增 2,340 stars，发布 8 个月后突然爆红`).
- **`tags`** — 3-5 short tags, Chinese or English as appropriate. Always include the `language` field as one tag. Derive the others from `topics` mapped to user-friendly Chinese labels: `ai`/`llm` → `AI`, `machine-learning` → `机器学习`, `agent` → `Agent`, `cli` → `命令行`, `developer-tools` → `开发工具`, `rag` → `RAG`, `vscode` → `VSCode`. Include `开源` as a tag for every GitHub repo.

**Translation rules:**
- Preserve proper nouns (product names, model names, company names) in their original form.
- If the description is already in Chinese, lightly edit for flow; don't translate back.
- Never exaggerate or add marketing language.

## Step 4: Write `web/GitHub/<date>/data.json`

Shape:

```json
{
  "date": "2026-04-10",
  "category": "GitHub",
  "title": "GitHub 趋势 · 2026-04-10",
  "sections": [
    {
      "id": "new_hot",
      "label": "新晋热门",
      "subtitle": "过去 7 天新建仓库按星数排序",
      "items": [ /* Item */ ]
    },
    {
      "id": "rising_stars",
      "label": "上升之星",
      "subtitle": "过去 7 天星数增长最快",
      "items": [ /* Item */ ]
    }
  ]
}
```

**Item** schema (extends the existing AI item schema — the frontend card template will hide GitHub-only fields on AI items and vice versa):

```json
{
  "id": "new_hot-1",
  "title": "Chinese title",
  "source": "@owner",
  "source_name": "GitHub",
  "summary": "Chinese summary",
  "detail": "Chinese detail",
  "significance": "Chinese significance",
  "links": ["https://github.com/owner/repo"],
  "image": "img/owner-repo.jpg",
  "image_type": "logo",
  "tags": ["Python", "AI", "开源"],
  "stars": 12345,
  "stars_gained": 2340,
  "language": "Python",
  "forks": 567,
  "owner": "owner",
  "repo": "repo"
}
```

**Field rules:**
- `id` — `"<section_id>-<1-indexed position>"` (e.g., `new_hot-1`, `rising_stars-7`)
- `source` — `"@" + owner`
- `source_name` — always the literal string `"GitHub"`
- `links` — single-element array with the repo URL
- `image` — value from `avatar_path` in raw.json; if `null`, omit the `image` field entirely
- `image_type` — always `"logo"` (GitHub avatars are logo-style)
- `stars_gained` — integer for `rising_stars` items, `null` for `new_hot` items

## Step 5: Do NOT update `web/manifest.json`

The entry script (`scripts/run-github-trending.sh` → `commit_and_push` in `scripts/briefing-common.sh`) rebuilds `web/manifest.json` from disk as a post-step via `scripts/rebuild_manifest.py`. This skill writes its data files and exits.

## Constraints

- All Chinese text uses Simplified Chinese; keep English for proper nouns and technical terms.
- Never invent repo features — ground every claim in `description`, `readme_excerpt`, or `topics`.
- Quality over quantity — if Chinese content for a repo would be weak, reduce to 2 sentences of `detail` rather than padding.
- Do not modify or delete `research_results/GitHub/` — it is managed manually.
- Budget: this skill should spend well under $3 per run. Most of the work is the deterministic Python fetch, not Claude inference.
