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
      "source": "@handle",
      "source_name": "Full Name",
      "summary": "Brief summary for card view, 1-2 sentences in Chinese",
      "detail": "Detailed content for expanded view, multiple paragraphs in Chinese",
      "key_quotes": ["Original quotes"],
      "significance": "Why this matters, in Chinese",
      "links": ["https://..."],
      "image": "img/filename.png",
      "tags": ["tag1", "tag2"]
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

## Step 2: Process Images

Only some items have images — that's intentional. Do not add images to items that don't have them in the research data.

If the research data includes images in `research_results/AI/YYYY-MM-DD/img/`:
- Copy only the images referenced by items to `web/AI/YYYY-MM-DD/img/`
- Compress/resize for web: max 200KB per image, max 800px width, JPEG quality 85% for photos, PNG for diagrams/charts
- Keep the `"image"` field as a relative path like `img/filename.png`
- For items without an image, omit the `"image"` field or set it to `null`

The web page displays images inside the card when present — they appear below the summary as a visual element. Not every card needs one; cards without images still look good with the colored gradient and icon.

## Step 3: Update Manifest

Read `web/manifest.json` and add the new date to the AI category's dates array. Keep dates sorted newest first. Create the manifest if it doesn't exist.

**Manifest schema:**

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

## Constraints

- Web content is a superset of PDF content — more items, more detail
- All text in Simplified Chinese (keep English for proper nouns and technical terms)
- Images must be optimized for web (compressed, resized)
- Always update the manifest after generating content
- Do NOT modify or delete research_results/ — it is managed manually
