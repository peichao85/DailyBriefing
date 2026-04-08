---
name: ai_pdf_builder
description: "Build a polished Chinese PDF presentation (10-15 slides) from AI research data. Reads structured research results and creates a visually rich PPTX, then converts to PDF. Use this skill when the user asks to build the AI briefing PDF, create the presentation, or run the PDF builder phase of the daily briefing pipeline."
---

# AI PDF Builder — Daily Briefing Presentation

Create a polished Simplified Chinese PDF presentation (10-15 slides) from research data. Use the `pptx` skill for creating the presentation and follow its design guidance, QA process, and PDF conversion instructions.

## Input

Read research data from `research_results/AI/YYYY-MM-DD/data.json` (where YYYY-MM-DD is today's date, or the date specified by the user).

## Step 1: Select Content for Slides

From the research data, select the 10-15 most impactful items for the slide deck. The PDF is the most condensed version — only the highlights.

## Step 2: Create a 10-15 Slide Chinese PPTX

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

## Step 3: Convert to PDF and QA

Use `pdf/AI/tmp/` as the working directory for all intermediate files (JS scripts, PPTX, slide images). Create it if it doesn't exist. Save the final PDF to `pdf/AI/daily-tech-ai-briefing-YYYY-MM-DD-cn.pdf`. Create the directory if it doesn't exist. After the final PDF is successfully saved, delete the entire `pdf/AI/tmp/` directory to clean up all intermediate files. Follow the pptx skill's QA and conversion process.

## Constraints

- Quality over quantity — only 10-15 most significant items from the research data
- All content in Simplified Chinese (keep English for proper nouns and technical terms)
- Titles must summarize the INSIGHT, not just name the person
- Every slide needs visual elements (icons, stats, shapes)
- Keep each slide concise and scannable
- Professional, modern formatting with gradient backgrounds
- Only deliver the final PDF — delete `pdf/AI/tmp/` after successful conversion
