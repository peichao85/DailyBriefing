---
name: ai_research
description: "Research today's most significant AI news and insights from 50 key industry accounts on X/Twitter and major outlets. Curates the top items into a structured JSON dataset with images. Use this skill when the user asks to research AI news, gather AI briefing data, or run the research phase of the daily briefing pipeline."
---

# AI Research — Daily Briefing Data Collection

Research today's most significant AI news and insights from 50+ key industry accounts and news sources. Output a structured JSON dataset that downstream skills (PDF builder, web builder) consume.

## Step 1: Research Today's Content

Use web search to find the latest news, announcements, and notable statements related to the following 25 key figures. These names serve as a **tracking list** — search for news *about* them from major outlets, not necessarily *from* their X accounts directly.

**Category 1 — Frontier Leaders & Founders:**
@sama (OpenAI CEO), @demishassabis (Google DeepMind CEO), @ilyasut (SSI founder), @DanielaAmodei (Anthropic Co-founder), @elonmusk (xAI/Tesla/SpaceX), @alexandr_wang (Scale AI / Meta AI)

**Category 2 — Product & Operators:**
@mntruell (Cursor CEO), @mikeyk (Anthropic CPO)

**Category 3 — Research & Science Leaders:**
@JeffDean (Google DeepMind Chief Scientist), @ylecun (AMI Labs / ex-Meta), @geoffreyhinton (AI pioneer), @AndrewYNg (Landing AI / DeepLearning.AI), @karpathy (Eureka Labs / ex-Tesla AI)

**Category 4 — Builders, Tools & Infrastructure:**
@julien_c (Hugging Face CTO), @ScottWu46 (Cognition founder), @alighodsi (Databricks CEO), @JonathanRoss321 (Groq CEO)

**Category 5 — Investors, Curators & Signal:**
@lexfridman (tech podcaster), @garrytan (YC CEO), @DrJimFan (NVIDIA AI)

**Search strategy (optimize for efficiency):**
1. Start with 3–5 broad searches: "AI news today", "breaking AI news April 2026", "AI funding announcements this week", etc. This alone covers most major stories.
2. Then do 3–4 grouped searches using OR operators to cover the tracking list, e.g.: `"Sam Altman" OR "Demis Hassabis" OR "Daniela Amodei" OR "Elon Musk" AI news April 2026`. Keep each group to 5–7 names.
3. Only do targeted individual searches for people who appeared in trending topics but lacked detail.

Target: ~10–12 total searches to cover everything. Do NOT search each name individually.

**Also search for:**
- Breaking tech and AI news from major outlets
- Significant product launches, model releases, funding rounds, or acquisitions in AI
- Major AI policy, regulation, or legal developments

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

## Step 3: Shortlist Candidates (cheap fields only)

From all candidate sources, pick the items that are plausibly worth publishing — items that appear to:
- Announce something new or significant
- Share a genuinely novel insight or opinion
- Spark major community discussion
- Be relevant to important AI/tech developments

Skip routine posts, retweets of minor things, casual conversation. If someone had nothing noteworthy, skip them entirely.

For each plausible candidate, record ONLY the following cheap fields. Do **not** write any Chinese `title`/`summary`/`detail`/`significance`/`key_quotes` yet, and do **not** search for or download images yet — the filter gate in Step 4 will drop a large fraction of candidates, and any Chinese writing or image work done before that gate is wasted.

| Field | Purpose |
|---|---|
| `title_en` | short English working title (used only for the filter log — thrown away after) |
| `source` | `@handle` or outlet name |
| `event_date` | ISO date of the underlying event (needed by the freshness filter) |
| `story_key` | stable english slug, 3–6 words, lowercase, hyphen-separated (needed by the returning-story filter; see rules below) |
| `source_url` | primary article URL |
| `one_line` | one short English sentence describing what this candidate is about (used by the returning-story filter to compare against prior-day summaries) |

**`story_key` rules:** name the story (actor + core event), not today's specific angle — so the same slug is reused across every day the story has a development. **Before creating a new key, scan ALL `story_key` values in the Step 2 lookback output. If any existing key describes the same story, reuse it exactly. Only mint a new key when no existing key matches.** Examples: `anthropic-mythos-zerodays`, `coreweave-anthropic-cloud-deal`, `openai-public-benefit-charter`.

**`event_date` rules:** ISO date of when the actual development covered by THIS item happened (announcement, release, incident, filing). NOT the research/publishing date. Advances only when the underlying world changes. If today's item is a follow-up to a story already published, `event_date` must be the date of the new development, not the original event.

## Step 4: Apply Filters (the gate)

Apply the following filters to the shortlist from Step 3. Any candidate that fails the gate is **dropped immediately** — no Chinese content, no image work. Only survivors reach Step 5.

1. **Freshness filter.** If `today − event_date > 5 days`, DROP. Only news whose underlying event happened within the last 5 days is eligible.
2. **Returning story filter.** If `story_key` appears in the lookback output, compare today's candidate (`title_en` + `one_line`) against the previously published title(s) and summary(ies) for that `story_key`. If the candidate covers **substantively new information** (new facts, data, reactions, decisions, or developments not present in prior coverage), KEEP. If it merely rehashes or rewords what was already published, DROP. When kept, the following constraints apply to the Chinese content that Step 5 will generate:
   - `title` MUST describe ONLY the new development. Do not re-litigate the original story in the title. Prior titles for this `story_key` are available in the lookback output — read them and make sure today's title covers fresh ground.
   - `summary` MUST be about the new development only. No recap of the original story in the one-sentence card lede.
   - `detail` leads with the new development, which takes the majority of the content. Append a short standalone paragraph clearly prefixed with **背景回顾：** (Background recap) — 1–2 sentences, ≤60 Chinese characters — naming the original story so downstream skills and readers missing prior days still have context. The recap must NOT expand into the main narrative.
   - `significance` MUST explain why the NEW development matters, not why the original story mattered. The original story's significance was already written on a prior day.
3. **Novel story.** If `story_key` does not appear in the lookback output, KEEP as a fresh story.

**Filter log:** After applying all filters, save a filter decision log to `research_results/AI/YYYY-MM-DD/filter_log.json`. Record **every** candidate that was evaluated (both kept and dropped), using only the shortlist fields plus the decision metadata. The log is written before Step 5, so entries contain no Chinese text — `title_en` is the log's title field. Schema:

```json
{
  "date": "YYYY-MM-DD",
  "total_candidates": 45,
  "kept": 15,
  "dropped": 30,
  "decisions": [
    {
      "story_key": "openai-gpt5-release",
      "event_date": "2026-04-10",
      "title_en": "OpenAI quietly ships GPT-5 fine-tune API",
      "source": "@sama",
      "action": "DROP",
      "filter": "freshness",
      "reason": "event_date 2026-04-10 is 7 days old (>5 day limit)"
    },
    {
      "story_key": "anthropic-claude-update",
      "event_date": "2026-04-13",
      "title_en": "Another recap of Claude nerfing controversy",
      "source": "@handle",
      "action": "DROP",
      "filter": "returning_story_no_update",
      "reason": "Already published on 04-12 with title '...'. No substantive new information found."
    },
    {
      "story_key": "anthropic-claude-update",
      "event_date": "2026-04-14",
      "title_en": "Anthropic announces pricing + rate limit changes",
      "source": "@handle",
      "action": "KEEP",
      "filter": "returning_story_with_update",
      "reason": "Previously published on 04-12. New info: pricing announced and API rate limits changed."
    },
    {
      "story_key": "meta-llama4-release",
      "event_date": "2026-04-14",
      "title_en": "Meta releases Llama 4 with multimodal tower",
      "source": "@handle",
      "action": "KEEP",
      "filter": "novel_story",
      "reason": "story_key not seen in lookback."
    }
  ]
}
```

Use these `filter` values: `freshness`, `returning_story_no_update`, `returning_story_with_update`, `novel_story`. The `reason` field should be specific enough to understand the decision without looking at other files — include dates, prior titles, and what new information was (or wasn't) found.

## Step 5: Elaborate Kept Items

Only items that passed the filter gate in Step 4 are elaborated here. Dropped candidates are already accounted for in `filter_log.json` and need no further work — never write Chinese content for them.

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
      "source": "@handle (optional, related person/account for metadata only — NOT displayed in UI)",
      "source_name": "Single most authoritative news source (see rules below)",
      "source_url": "URL of the source_name article from the links array",
      "story_key": "stable-english-slug-for-this-story",
      "event_date": "YYYY-MM-DD",
      "summary": "Brief summary in Chinese, 1-2 sentences",
      "detail": "Detailed analysis in Chinese, multiple paragraphs",
      "key_quotes": ["Original quotes, can be English"],
      "significance": "Why this matters, in Chinese",
      "links": ["https://..."],
      "tags": ["tag1", "tag2"],
      "category": "frontier_leaders|product_operators|research|builders|trending|news"
    }
  ]
}
```

**`source_name` rules:** Pick the **single most authoritative** news source for each item — NOT the person or company the story is about. This field tells the reader "where the information comes from" so they can judge credibility at a glance.

| Scenario | Selection rule | Example |
|----------|---------------|---------|
| Company self-publishes (blog, newsroom) | Use the company's publication name | NVIDIA Newsroom, Anthropic Blog |
| Single media exclusive | Use that outlet | TechCrunch, The Information |
| Multiple outlets covering the story | Pick the **one** most authoritative or earliest reporter | CNN (not "CNN / Fortune / NPR") |
| Leaked document or internal memo | Use the outlet that broke the story | Axios |

Key rule: **`source_name` must be exactly one source.** Never slash-separate multiple outlets.

**`source_url` rules:** Set this to the URL from the `links` array that corresponds to the `source_name` outlet. If `source_name` is "TechCrunch" and `links` contains a techcrunch.com URL, use that URL. This field powers the clickable source link on the frontend card.

**`source` field (optional):** The `@handle` field is retained purely as metadata for internal categorization. It is **not displayed** in the UI. You may omit it or set it to a brief label (e.g. "@sama", "NVIDIA", "泄露备忘录") for filtering/logging purposes.

**`story_key` and `event_date`:** carry over unchanged from the shortlist assigned in Step 3. These fields are never re-derived here — the values that went into the filter gate must be the values that land in `data.json`.

## Step 6: Gather Images (kept items only)

Images are gathered only for items kept by the filter gate in Step 4. Never search for or download images for candidates that were dropped.

**Target coverage:** aim for roughly **3–4 of every 10 kept items** to have an image. This is a floor on effort, not a cap — most AI stories have *something* reasonable available (a company logo, a headshot, a product screenshot, a press photo). Default to finding one; only skip when you've genuinely checked the ladder below and nothing fits.

### Item ordering and the hero card

Order `items[]` so the day's most important story is `id=1`. The web page renders `items[0]` as the full-width **hero card** and anchors the entire layout on it. A hero card without an image looks broken.

**Rule: item `id=1` MUST have an image.** Work down this ladder and stop at the first option that yields a clean, relevant image:

1. Official product screenshot, demo frame, or architecture diagram from the announcement
2. Benchmark chart, data visualization, or comparison table from the story
3. Company logo (Wikipedia or official brand asset) — works for funding rounds, acquisitions, regulatory action, business-strategy stories
4. Headshot of the central person (CEO, researcher, filer) — search `"[Name] headshot"` or `"[Name] official photo"`, prefer Wikipedia or company-bio photos
5. A press/event photo from the article that broke the story

In practice, (3) or (4) is always available for any major AI story — there is effectively no excuse for the hero card to ship without an image. If you genuinely cannot find one, reorder `items[]` so a story that DOES have an image becomes `id=1`.

### Other items (`id=2` onward)

Use the same ladder but with a lower bar for skipping: if none of (1)–(5) yields a reasonable-quality image for a given item, leave `image` unset. Do not force filler. Specifically skip when:

- The story is a generic trend roundup with no clear visual subject
- The only available image is a low-quality thumbnail or cropped social card
- The image would be decorative stock (e.g. a generic "AI chip" or "data center" photo that doesn't depict the actual story)

You should still aim for the 3–4/10 target across the day. A zero-image day (other than hero) means the ladder was not fully worked.

### File naming and `image_type`

Download to `research_results/AI/YYYY-MM-DD/img/` with descriptive filenames (e.g. `claude-mythos-architecture.png`, `sam-altman.jpg`, `gpqa-benchmark-chart.png`). Set the item's `"image"` field to `img/filename.png`.

**`image_type` is REQUIRED on every item that has an `image`** — downstream skills use it to choose display size:

- `"chart"` — benchmark charts, data visualizations, graphs, comparison tables, screenshots containing real data/numbers. Displayed larger so data is readable.
- `"logo"` — product logos, company logos, headshots, branding, decorative graphics, product UI mockups. Displayed as compact thumbnails.

If missing, downstream defaults to `"logo"`, which under-sizes chart content. Do not rely on the default — set it explicitly.

## Constraints

- **Filter before you elaborate.** Never write Chinese `title`/`summary`/`detail`/`significance`/`key_quotes` or search for/download images for a candidate before the filter gate in Step 4 has approved it. Around half of candidates are typically dropped by the gate; any elaboration work done before it is wasted tokens.
- **Hero card must have an image.** Item `id=1` renders as the full-width hero on the web page and must carry an image. If the top story genuinely has no usable image after working the Step 6 ladder, reorder `items[]` so that a story which does have one becomes `id=1`.
- **Aim for 3–4 of every 10 items to carry an image.** This is a floor on effort, not a cap. Skip only after working the Step 6 ladder.
- All titles, summaries, details, and significance in Simplified Chinese (keep English for names, product names, company names, and technical terms commonly written in English)
- Titles must summarize the INSIGHT, not just name the person
- Quality over quantity — only genuinely significant items
- Respect copyright — summarize, don't reproduce full articles or tweets
- Skip people with nothing noteworthy today
- Do NOT delete the output directory — it is managed manually
