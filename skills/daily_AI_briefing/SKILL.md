---
name: daily_AI_briefing
description: "Generate a daily Tech & AI briefing as a polished Chinese PDF presentation (10-15 slides). Researches today's most significant AI news and insights from 50 key industry accounts on X/Twitter, curates the top 10-15 items, creates a visually rich Chinese PPTX, converts to PDF, and runs visual QA. Use this skill whenever the user asks for a daily AI briefing, tech news summary, AI news deck, or morning briefing — even if they don't say 'PDF' or 'presentation' explicitly. Also trigger when the user says things like 'what happened in AI today', 'AI news roundup', 'daily tech update', or asks for a Chinese AI briefing/report."
---

# Daily Tech & AI Briefing Generator

Generate a daily Tech & AI briefing as a polished Simplified Chinese PDF presentation (10-15 slides). Use the `pptx` skill for creating the presentation and follow its design guidance, QA process, and PDF conversion instructions.

## Step 1: Research Today's Content

Use web search to find recent tweets/posts and news from ALL of the following 50 accounts. Cast a wide net — only the most significant 10-15 items make the final deck.

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

## Step 2: Curate Ruthlessly

From all 50 accounts, only pick the 10-15 most important items that:
- Announce something new or significant
- Share a genuinely novel insight or opinion
- Spark major community discussion
- Are relevant to important AI/tech developments

Skip routine posts, retweets of minor things, casual conversation. If someone had nothing noteworthy, skip them entirely.

## Step 3: Create a 10-15 Slide Chinese PPTX

All text in Simplified Chinese (keep English for names, product names, company names, and commonly-used English terms).

**Slide structure:**

| Slide Type | Count | Description |
|-----------|-------|-------------|
| Title slide | 1 | Bold headline summarizing today's biggest story, with date and 2-3 bullet subtitle highlights. Footer: `精选自 50+ 位 AI 领袖, 研究者与建造者的动态` |
| Key People's Takes | 3-5 | Only the most impactful posts. Title = the KEY INSIGHT, not the person's name. Use icons and big stats where applicable. |
| Trending on X in AI | 1-2 | What's trending in the AI community on X today, with context |
| AI News & Developments | 2-3 | Key headlines with short summaries, using icons and visual hierarchy |
| Key Takeaways | 1 | 5 bullet points summarizing the most important things to know today. Footer: `明日简报将于上午 10:00 发布，保持关注！` |

**Design requirements:**
- Use gradient backgrounds (dark for section headers/takeaways, light for content slides)
- Use react-icons for visual elements on every slide
- Bold, insight-driven titles (e.g., "代码手写时代正式终结" not "Karpathy 的推文")
- Large stat callouts for key numbers
- Card-based layouts with shadows and colored accent bars
- 信号 (SIGNAL) line at bottom of content slides

## Step 4: Convert to PDF and QA

Save the final PDF to `daily_briefing/AI/pdf/daily-tech-ai-briefing-[YYYY-MM-DD]-cn.pdf` (relative to the working directory). Create the directory if it doesn't exist. Delete the intermediate PPTX after successful conversion. Follow the pptx skill's QA and conversion process.

## Constraints

- Quality over quantity — only 10-15 most significant items from 50 accounts
- All content in Simplified Chinese (keep English for proper nouns and technical terms commonly written in English)
- Titles must summarize the INSIGHT, not just name the person
- Every slide needs visual elements (icons, stats, shapes)
- Keep each slide concise and scannable
- Professional, modern formatting with gradient backgrounds
- Respect copyright — summarize, don't reproduce full articles or tweets
- Skip people with nothing noteworthy today
- Only deliver the final PDF — delete intermediate PPTX after conversion
