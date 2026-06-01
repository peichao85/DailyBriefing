---
name: ai_web_builder
description: "Build web-friendly briefing data from AI research results. Transforms research JSON into optimized web content and updates the manifest. Use this skill when the user asks to build the web briefing, generate web content, or run the web builder phase of the daily briefing pipeline."
---

# AI Web Builder — Daily Briefing Web Content

Transform AI research data into web-friendly JSON and optimized images for the daily briefing website.

## Input

Read research data from `research_results/AI/YYYY-MM-DD/data.json` (where YYYY-MM-DD is today's date, or the date specified by the user).

## Step 1: Transform Data for Web

Create `web/AI/YYYY-MM-DD/data.json` with the following schema:

```json
{
  "date": "YYYY-MM-DD",
  "category": "AI",
  "title": "Today's headline summary in Chinese",
  "items": [
    {
      "id": "1",
      "title": "Insight-driven title in Chinese",
      "source": "@handle (optional, related person/account — not displayed in UI)",
      "source_name": "Single most authoritative news source",
      "source_url": "URL of the source_name article from the links array",
      "story_key": "stable-english-slug-for-this-story",
      "event_date": "YYYY-MM-DD",
      "summary": "Brief summary for card view, 1-2 sentences in Chinese",
      "detail": "Detailed content for expanded view, multiple paragraphs in Chinese",
      "key_quotes": ["Original quotes"],
      "significance": "Why this matters, in Chinese",
      "links": ["https://..."],
      "image": "img/filename.png",
      "image_type": "logo|chart",
      "tags": ["tag1", "tag2"],
      "category": "frontier_leaders|product_operators|research|builders|trending|news"
    }
  ]
}
```

**Transformation rules:**
- The web version is a superset of the PDF — include more items and more detail than what goes into the PDF
- Write a compelling `title` for the day's briefing that summarizes the biggest story
- Each item's `summary` should be concise (for card display), while `detail` can be comprehensive
- All text in Simplified Chinese (keep English for names, product names, technical terms)
- Titles must summarize the INSIGHT, not just name the person
- Pass through `story_key`, `event_date`, `category`, `source_url` from the research data unchanged. `story_key` and `event_date` are used by `ai_research` on subsequent days to detect stale news and story rehashes via a `jq` lookback over the last 7 days of web briefings — they must survive into `web/AI/YYYY-MM-DD/data.json` intact. `category` preserves the editorial classification for potential frontend filtering. `source_url` powers the clickable source link on the card.

## Step 2: Process Images

Only some items have images — that's intentional. Do not add images to items that don't have them in the research data.

### Cached images (`assets/` paths)

If an item's `image` field starts with `assets/` (e.g. `assets/logos/openai-logo.png`), it means the research skill reused a globally cached logo. **Pass it through unchanged** — do NOT copy anything. The frontend resolves `assets/` paths relative to the `web/` root. Also pass through `image_type` unchanged.

### New images (`img/` paths)

For items with `image` pointing to `research_results/AI/YYYY-MM-DD/img/`:
- Copy only the images referenced by items to `web/AI/YYYY-MM-DD/img/`
- Compress/resize for web: max 200KB per image, max 800px width, JPEG quality 85% for photos, PNG for diagrams/charts
- Keep the `"image"` field as a relative path like `img/filename.png`
- Pass through `"image_type"` from research data (`"chart"` or `"logo"`). If missing, default to `"logo"`.
- For items without an image, omit the `"image"` field or set it to `null`

The web page displays images inside the card when present — they appear below the summary as a visual element. Not every card needs one; cards without images still look good with the colored gradient and icon.

## Step 3: Do NOT update `web/manifest.json`

The manifest is rebuilt from disk by the orchestrator (`scripts/run-briefing.sh` → `scripts/rebuild_manifest.py`) as a post-step after all parallel builders finish. This avoids a write race between `ai_web_builder` and `github_trending_builder`, both of which run in parallel and would otherwise be updating the same file. Simply write the new `web/AI/<date>/data.json` and the rebuild step will pick it up automatically.

## Constraints

- Web content is a superset of PDF content — more items, more detail
- All text in Simplified Chinese (keep English for proper nouns and technical terms)
- Images must be optimized for web (compressed, resized)
- Do NOT touch `web/manifest.json` — the orchestrator handles it
- Do NOT modify or delete research_results/ — it is managed manually
