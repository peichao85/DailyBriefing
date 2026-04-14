---
name: ai_research
description: "Research today's most significant AI news and insights from 50 key industry accounts on X/Twitter and major outlets. Curates the top items into a structured JSON dataset with images. Use this skill when the user asks to research AI news, gather AI briefing data, or run the research phase of the daily briefing pipeline."
---

# AI Research — Daily Briefing Data Collection

Research today's most significant AI news and insights from 50+ key industry accounts and news sources. Output a structured JSON dataset that downstream skills (PDF builder, web builder) consume.

## Step 1: Research Today's Content

Use web search to find recent tweets/posts and news from ALL of the following 50 accounts. Cast a wide net — only the most significant items make the final dataset.

**Category 1 — Frontier Leaders & Founders:**
@sama (OpenAI CEO), @gdb (OpenAI Co-founder & President), @demishassabis (Google DeepMind CEO), @mustafasuleyman (Microsoft AI CEO), @ilyasut (SSI founder), @DanielaAmodei (Anthropic Co-founder), @elonmusk (xAI/Tesla/SpaceX), @aidangomez (Cohere Co-founder), @alexandr_wang (Scale AI CEO), @AravSrinivas (Perplexity CEO)

**Category 2 — Product, Design & Operators:**
@kevinweil (OpenAI CPO), @mikeyk (Anthropic CPO), @jasonfried (37signals), @levie (Box CEO), @mntruell (Cursor CEO), @ryolu_ (Cursor Chief Designer), @antonosika (Lovable CEO), @levelsio (indie dev), @joshm (The Browser Company CEO), @rauchg (Vercel CEO, v0)

**Category 3 — Research & Science Leaders:**
@JeffDean (Google DeepMind Chief Scientist), @ylecun (Meta Chief AI Scientist), @geoffreyhinton (AI pioneer), @AndrewYNg (Landing AI / DeepLearning.AI), @OriolVinyalsML (DeepMind VP Research), @soumithchintala (PyTorch co-founder), @ShaneLegg (DeepMind co-founder), @karpathy (ex-Tesla AI), @ctnzr (NVIDIA DL Research), @jackclarkSF (Anthropic co-founder)

**Category 4 — Builders, Tools & Infrastructure:**
@julien_c (Hugging Face CTO), @RichardSocher (You.com CEO), @c_valenzuelab (Runway CEO), @alexgraveley (GitHub Copilot architect), @amasad (Replit CEO), @ScottWu46 (Cognition founder), @drorwe (Tabnine co-founder), @ivanhzhao (Notion founder), @alighodsi (Databricks CEO), @JonathanRoss321 (Groq CEO)

**Category 5 — Investors, Curators & Signal:**
@lexfridman (tech podcaster), @lennysan (product podcast), @naval (entrepreneur), @garrytan (YC CEO), @pmarca (a16z co-founder), @paulg (YC co-founder), @DrJimFan (NVIDIA AI), @rasbt (ML researcher), @hwchase17 (LangChain CEO), @polynoamial (OpenAI research scientist)

**Also search for:**
- Trending AI topics on X today
- Breaking tech and AI news from major outlets
- Popular AI articles and blog posts gaining traction
- Significant product launches, model releases, funding rounds, or acquisitions in AI

## Step 2: Freshness + Dedup Lookback

Before selecting items, pull a compact view of what has already been published in the last 7 days. Every candidate item must be checked against this list so that stale news and rehashes never reach readers twice.

**Run the lookback (one jq call):**

```bash
jq -r '.items[] | [.event_date, .story_key, .title, .summary] | @tsv' \
  web/AI/{date-1}/data.json web/AI/{date-2}/data.json web/AI/{date-3}/data.json \
  web/AI/{date-4}/data.json web/AI/{date-5}/data.json web/AI/{date-6}/data.json \
  web/AI/{date-7}/data.json \
  2>/dev/null
```

Substitute `{date-1}` through `{date-7}` with the 7 ISO dates preceding today. `2>/dev/null` swallows errors for dates where no briefing was published. Output is one TSV line per prior item: `event_date \t story_key \t title \t summary`. Treat this list as the "already published" set. The title and summary are used by the returning-story filter to judge whether today's candidate contains substantively new information.

**Transition note:** briefings published before this step existed lack `story_key` and `event_date` — those rows arrive with empty first two columns. For those rows only, fall back to fuzzy title matching when checking for duplicates. All new publications carry both fields and are matched structurally.

## Step 3: Curate and Structure

From all candidate sources, pick the most important items that:
- Announce something new or significant
- Share a genuinely novel insight or opinion
- Spark major community discussion
- Are relevant to important AI/tech developments

Skip routine posts, retweets of minor things, casual conversation. If someone had nothing noteworthy, skip them entirely.

**Before finalizing each candidate, assign its `story_key` and `event_date` (see field rules in Step 4), then apply the following filters in order:**

1. **Freshness filter.** If `today − event_date > 3 days`, DROP. Only news whose underlying event happened within the last 3 days is eligible.
2. **Returning story filter.** If `story_key` appears in the lookback output, compare today's candidate against the previously published title(s) and summary(ies) for that `story_key`. If the candidate covers **substantively new information** (new facts, data, reactions, decisions, or developments not present in prior coverage), KEEP. If it merely rehashes or rewords what was already published, DROP. When kept, the following constraints apply:
   - `title` MUST describe ONLY the new development. Do not re-litigate the original story in the title. Prior titles for this `story_key` are available in the lookback output — read them and make sure today's title covers fresh ground.
   - `summary` MUST be about the new development only. No recap of the original story in the one-sentence card lede.
   - `detail` leads with the new development, which takes the majority of the content. Append a short standalone paragraph clearly prefixed with **背景回顾：** (Background recap) — 1–2 sentences, ≤60 Chinese characters — naming the original story so downstream skills and readers missing prior days still have context. The recap must NOT expand into the main narrative.
   - `significance` MUST explain why the NEW development matters, not why the original story mattered. The original story's significance was already written on a prior day.
3. **Novel story.** If `story_key` does not appear in the lookback output, KEEP as a fresh story.

**Filter log:** After applying all filters, save a filter decision log to `research_results/AI/YYYY-MM-DD/filter_log.json`. Record **every** candidate that was evaluated (both kept and dropped). Schema:

```json
{
  "date": "YYYY-MM-DD",
  "total_candidates": 45,
  "kept": 15,
  "dropped": 30,
  "decisions": [
    {
      "story_key": "openai-gpt5-release",
      "event_date": "2026-04-12",
      "title": "候选标题",
      "source": "@handle",
      "action": "DROP",
      "filter": "freshness",
      "reason": "event_date 2026-04-10 is 4 days old (>3 day limit)"
    },
    {
      "story_key": "anthropic-claude-update",
      "event_date": "2026-04-13",
      "title": "候选标题",
      "source": "@handle",
      "action": "DROP",
      "filter": "returning_story_no_update",
      "reason": "Already published on 04-12 with title '...'. No substantive new information found."
    },
    {
      "story_key": "anthropic-claude-update",
      "event_date": "2026-04-14",
      "title": "候选标题",
      "source": "@handle",
      "action": "KEEP",
      "filter": "returning_story_with_update",
      "reason": "Previously published on 04-12. New info: pricing announced and API rate limits changed."
    },
    {
      "story_key": "meta-llama4-release",
      "event_date": "2026-04-14",
      "title": "候选标题",
      "source": "@handle",
      "action": "KEEP",
      "filter": "novel_story",
      "reason": "story_key not seen in lookback."
    }
  ]
}
```

Use these `filter` values: `freshness`, `returning_story_no_update`, `returning_story_with_update`, `novel_story`. The `reason` field should be specific enough to understand the decision without looking at other files — include dates, prior titles, and what new information was (or wasn't) found.

## Step 4: Output Structured Data

Save the research results to `research_results/AI/YYYY-MM-DD/data.json` (create the directory if needed).

**Output schema:**

```json
{
  "date": "YYYY-MM-DD",
  "category": "AI",
  "researched_at": "ISO 8601 timestamp",
  "sources_checked": ["@handle1", "@handle2", "..."],
  "items": [
    {
      "id": "1",
      "title": "Insight-driven title in Chinese (e.g., '代码手写时代正式终结')",
      "source": "@handle",
      "source_name": "Full Name",
      "source_role": "Role/Title",
      "story_key": "stable-english-slug-for-this-story",
      "event_date": "YYYY-MM-DD",
      "summary": "Brief summary in Chinese, 1-2 sentences",
      "detail": "Detailed analysis in Chinese, multiple paragraphs",
      "key_quotes": ["Original quotes, can be English"],
      "significance": "Why this matters, in Chinese",
      "links": ["https://..."],
      "original_language": "en|zh",
      "tags": ["tag1", "tag2"],
      "category": "frontier_leaders|product_operators|research|builders|trending|news"
    }
  ]
}
```

**`story_key` rules:** 3–6 words, lowercase, hyphen-separated, English. Name the story (actor + core event), not today's specific angle — so the same slug is reused across every day the story has a development. **Before creating a new key, scan ALL `story_key` values in the Step 2 lookback output. If any existing key describes the same story, reuse it exactly. Only mint a new key when no existing key matches.** Examples: `anthropic-mythos-zerodays`, `coreweave-anthropic-cloud-deal`, `openai-public-benefit-charter`.

**`event_date` rules:** ISO date of when the actual development covered by THIS item happened (announcement, release, incident, filing). NOT the research/publishing date. Advances only when the underlying world changes. If today's item is a follow-up to a story already published, `event_date` must be the date of the new development, not the original event.

## Step 5: Gather Images

For items where a visual adds real value, download a relevant image to `research_results/AI/YYYY-MM-DD/img/`. **Not every item needs an image** — only include one when it genuinely helps the reader understand the story.

**When to include an image:**
- A new product or model with an official screenshot, demo, or architecture diagram
- A data visualization, benchmark chart, or comparison table that tells the story better than words
- An image generated by a newly released image model (to showcase its capabilities)
- A key person making a major announcement — use their professional/public profile photo (search for "[Name] headshot" or "[Name] official photo")

**When NOT to include an image:**
- Routine commentary or opinion posts — the person's words are the content, not their face
- Trending topic roundups — these are aggregations, not visual stories
- When no high-quality, relevant image can be found — never use a placeholder or low-quality image

**Image sources (in order of preference):**
1. Official press images, product screenshots, or diagrams from the announcement
2. Public profile photos from company websites or Wikipedia (for major announcements by a person)
3. Charts/graphs from research papers or blog posts
4. Skip the image if nothing good is available

**File naming:** use descriptive names like `claude-mythos-architecture.png`, `sam-altman.jpg`, `gpqa-benchmark-chart.png`. Reference them in the item's `"image"` field as `img/filename.png`.

**Image type classification:** Set `"image_type"` on each item with an image:
- `"chart"` — benchmark charts, data visualizations, graphs, comparison tables, screenshots with real data/numbers. These are displayed larger so the data is readable.
- `"logo"` — product logos, branding images, headshots, decorative graphics, product UI mockups. These are displayed as compact thumbnails.

## Constraints

- All titles, summaries, details, and significance in Simplified Chinese (keep English for names, product names, company names, and technical terms commonly written in English)
- Titles must summarize the INSIGHT, not just name the person
- Quality over quantity — only genuinely significant items
- Respect copyright — summarize, don't reproduce full articles or tweets
- Skip people with nothing noteworthy today
- Do NOT delete the output directory — it is managed manually
