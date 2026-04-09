---
name: ai_pdf_builder
description: "Build a polished Chinese PDF presentation (10-15 slides) from AI research data. Reads structured research results and creates a visually rich PPTX, then converts to PDF. Use this skill when the user asks to build the AI briefing PDF, create the presentation, or run the PDF builder phase of the daily briefing pipeline."
---
You are generating a daily Tech & AI briefing as a polished Chinese PDF presentation (10-15 slides). Generate a Chinese PPTX as an intermediate format (for layout purposes), then convert it into a PDF file. Only deliver the final PDF — do not keep the intermediate PPTX unless explicitly requested.

Use `pdf/AI/tmp/` as the working directory for all intermediate files (JS scripts, PPTX, slide images). Create it if it doesn't exist. Save the final PDF to `pdf/AI/daily-tech-ai-briefing-YYYY-MM-DD-cn.pdf`. Create the directory if it doesn't exist. After the final PDF is successfully saved, delete the entire `pdf/AI/tmp/` directory to clean up all intermediate files.

## Steps

1. **Read the pptx skill** at the pptx skill location and follow its instructions for creating the presentation.

2. **Read today's data** Read research data from `research_results/AI/YYYY-MM-DD/data.json` (where YYYY-MM-DD is today's date, or the date specified by the user).

3. **Curate ruthlessly** — from the research data, select the 10-15 most impactful items for the slide deck. The PDF is the most condensed version — only the highlights.


4. **Create a 10-15 slide Chinese PPTX** with CONTENT-FOCUSED titles (NOT "what person X said" but the actual insight/news).
   - **Title slide**: A bold, attention-grabbing headline summarizing today's biggest story, with date and 2-3 bullet subtitle highlights
   - **Key People's Takes** (3-5 slides): Only the most impactful posts. Title each slide with the KEY INSIGHT, not the person's name. Use icons and big stats where applicable. Include a "信号:" line at the bottom of each content slide explaining why it matters.
   - **Trending on X in AI** (1-2 slides): What's trending in the AI community on X today, with context
   - **AI News & Developments** (2-3 slides): Key headlines with short summaries, using icons and visual hierarchy
   - **Key Takeaways** (1 slide): 5 bullet points summarizing the most important things to know today, with icons

   **Design requirements:**
   - Use gradient backgrounds (dark for section headers/takeaways, light for content slides. But avoid high contrast between the light and dark slides.)
   - Use react-icons for visual elements on every slide
   - Bold, insight-driven titles (e.g., "代码手写时代正式终结" not "Karpathy 的推文")
   - Large stat callouts for key numbers
   - Card-based layouts with shadows and colored accent bars
   - 信号 (SIGNAL) line at bottom of content slides

5. **Convert to PDF** — Convert the Chinese PPTX into PDF using LibreOffice. Save the final PDF to the outputs folder with filename `daily-tech-ai-briefing-[YYYY-MM-DD]-cn.pdf`. Delete the intermediate PPTX after successful PDF conversion.

6. **Visual QA** — Convert the PDF to images and verify each slide renders correctly with proper layout, text, and visual elements.

## Constraints
- Quality over quantity — only 10-15 most significant items from the research data
- All content should be in Simplified Chinese (keep English for proper nouns and technical terms)
- Titles must summarize the INSIGHT, not just name the person
- Every slide needs visual elements (icons, stats, shapes)
- Keep each slide concise and scannable
- Professional, modern formatting with gradient backgrounds
- Only deliver the final PDF — no intermediate files
- Follow the pptx skill's QA and conversion process.

