---
name: us_stocks_briefing
description: "Build the 美股复盘 (US-equities closing recap) daily briefing. Runs a Python helper that pulls index/sector/yield/mover data from CNBC, Nasdaq and FRED, then layers on Chinese analysis, news, FedWatch, earnings and risk commentary, and writes the document-mode web data file. Use this skill when the user asks to build the US stocks recap, refresh 美股复盘, run the finance/markets briefing, or run the US-stocks phase of the daily pipeline."
---

# US Stocks Briefing Builder — 美股复盘

Build `web/USStocks/<date>/data.json` for the **美股复盘** tab of the Daily
Briefing web page. This is a professional US-equities closing recap: a
data-driven analyst report covering the prior session — what happened, why the
market moved, where money rotated, and what to watch tomorrow.

You are acting as a US market daily analyst, macro strategist, and tech
growth-stock researcher. Output language: **Simplified Chinese**, English for
proper nouns / tickers. Style: professional, clear, data-driven, suitable for
investment review (复盘) and next-day trade planning.

The tab uses the web page's **document render mode** (`format: "document"`):
a section-navigated report of `blocks` (prose / table / callout), NOT item
cards. The Python helper provides the hard numbers; you provide everything that
isn't a clean number feed.

## Hard rules (non-negotiable)

- **Never invent data.** If a number, news item, or probability cannot be
  obtained or verified, write the literal string **`暂无可靠数据`**. Do not
  guess, interpolate, or carry yesterday's value forward.
- **Cite sources** for key facts, company news, earnings, and macro data —
  put a source name or URL in the relevant cell / `links`.
- When sources disagree, note the difference and prefer the more authoritative /
  more real-time one (CNBC, Reuters, Bloomberg, WSJ, official IR, SEC, FedWatch,
  FRED, CME, EIA).
- Quantitative tables come from `raw.json` — do not hand-edit those numbers.
- All prose is Simplified Chinese; keep tickers and proper nouns in English.

## Input

`$DATE` in YYYY-MM-DD (passed by the user or orchestrator). Default: today UTC.
The report covers the **most recent completed trading session** at or before
`$DATE` — the helper resolves this as `trading_day` in its output. **Use
`trading_day` for BOTH the output directory and the `date` field**
(`web/USStocks/<trading_day>/data.json`), so each session gets exactly one
entry and weekend/holiday re-runs are idempotent (they overwrite the same
Friday-session file rather than creating empty duplicates).

## Step 1: Run the Python helper

```bash
cd <project_root>
python3 skills/us_stocks_briefing/scripts/fetch_market_data.py --date <date>
```

> **Market-closed pre-flight (orchestrator only).** The helper also supports
> `--check-only`, which resolves the most recent completed session and exits
> **3** if `web/USStocks/<trading_day>/data.json` already exists (weekend /
> holiday / same-day re-run → nothing new), or **0** if there is work to do.
> `scripts/run-us-stocks-briefing.sh` uses this to skip the paid recap on closed days. A
> manual run of this skill is not gated by it — it always regenerates.

It writes `research_results/USStocks/<date>/raw.json` with:

- `trading_day` — the actual session the data represents (use this as the
  report's `date`, not `$DATE`).
- `indices` — DJI / S&P500 / Nasdaq Comp / NDX / RUT / SOX / VIX snapshots
  (`last`, `change`, `change_pct`, `open/high/low`, `volume`, 52wk range).
- `tech_etfs` — SPY/QQQ/DIA/IWM/SMH/IGV with full `tech` block
  (`ma20/50/100/200`, `rsi14`, `macd`, `trend`).
- `sectors` — 11 SPDR sector ETFs with `change_pct`, `ret_5d`, `ret_1mo`, `tech`.
- `themes` — theme/style ETFs (SOXX, CIBR, CLOU, BOTZ, AIQ, IWO, IWN, RSP,
  SCHG, VTV) with `change_pct`, `ret_5d`, `ret_1mo`.
- `macro_assets` — DXY, gold, WTI, Brent, BTC, ETH snapshots.
- `yields` — DGS2 / DGS10 / DGS30 + T10Y2Y (2s10s spread) from FRED, each with
  `value` and daily `change`.
- `technicals_stocks` — MA/RSI/MACD/trend for mag7 + key AI names.
- `movers` — `mag7`, `ai_hardware`, `software`, `ai_power` groups
  (`last`, `change_pct`), plus `top_gainers` / `top_losers`.

**Degrade gracefully.** If a field is missing (e.g. `yields` empty, a `change_pct`
is null), render it as `暂无可靠数据` rather than failing. The helper is
best-effort; a partial `raw.json` is still usable.

**What the helper does NOT provide** — fetch these yourself via web research, or
mark `暂无可靠数据`:
- Exchange breadth internals: advance/decline, new highs/lows, McClellan,
  put/call, % of S&P 500 above MA, MOVE, VVIX, credit spreads.
- CME FedWatch rate-cut probabilities.
- The economic-data calendar (CPI/PPI/PCE/NFP/claims/ISM/JOLTS/…).
- Company news catalysts, analyst rating changes, earnings results & guidance.
- Institutional strategy views, fund flows, M&A, insider activity.

## Step 2: Research the narrative layer (web)

Read `raw.json`, then use web search/fetch against authoritative sources to fill
the qualitative sections. Anchor every claim to a source. Prioritize:

1. **盘中走势复盘** — pre-market → open → midday → close → after-hours; the core
   driver (rates / earnings / AI / geopolitics); any sell-the-news / buy-the-dip
   / short-squeeze / rotation.
2. **宏观** — FedWatch probabilities & change vs. prior day; Fed-speak; the day's
   economic data (actual vs. consensus vs. prior + interpretation).
3. **个股催化** — the news behind each notable mover (七巨头, AI 硬件, 软件,
   AI 电力): earnings, orders, ratings, products, regulation.
4. **财报** — last night's results (rev/EPS beat-miss, margins, RPO/ARR/cloud/AI
   revenue, guidance, after-hours reaction) and the next 1–3 sessions' calendar.
5. **机构观点与资金流** — bank strategy notes, index targets, rating changes,
   ETF flows, notable options activity.
6. **板块轮动判断** & **风险** — synthesize from the data + news.

Keep budget discipline: the helper already did the heavy quantitative lifting.
Spend research effort where it adds the most signal (drivers, FedWatch,
earnings, catalysts). Budget guidance: **~$15** per run.

## Step 3: Assemble `web/USStocks/<date>/data.json`

Document-mode schema:

```json
{
  "date": "2026-05-29",
  "category": "USStocks",
  "format": "document",
  "title": "美股复盘 · 2026-05-29",
  "headline": "一句话总结：指数强、宽度弱，AI 硬件继续主导，但短线拥挤度上升。",
  "sections": [ /* Section */ ]
}
```

**Section**: `{ "id", "label", "icon", "subtitle"?, "blocks": [ Block ] }`

Use these 7 sections (group the report's 15 parts to keep the sub-tab bar usable):

| id | label | icon | report parts covered |
|----|-------|------|----------------------|
| `overview` | 总览 | 📊 | 0 一句话 · 1 大盘表现 · 2 盘中复盘 |
| `macro` | 宏观 | 🏦 | 3 美债 / Fed / 美元黄金油 / 经济数据 |
| `sectors` | 板块与主题 | 🔀 | 4 板块 · 5 主题风格 · 11 轮动判断 |
| `breadth` | 宽度与技术 | 📐 | 6 市场宽度 · 7 技术面 |
| `stocks` | 个股 | 💹 | 8 个股异动 · 12 重点关注股 |
| `earnings` | 财报与机构 | 📑 | 9 财报 · 10 机构观点与资金流 |
| `plan` | 计划与风险 | 🧭 | 13 明日计划 · 14 风险 · 15 结论 |

**Block** types:
- `{ "type": "heading", "text": "..." }` — a sub-heading within a section.
- `{ "type": "prose", "md": "..." }` — Markdown text (`**bold**`, `*italic*`,
  `- ` bullet lists; newlines preserved). Use for narrative & analysis.
- `{ "type": "callout", "tone": "info|bull|bear|warn", "title": "信号", "md": "..." }`
  — a highlighted box. Use `bull`/`bear` for directional judgments, `warn` for
  risks, `info` for neutral signals.
- `{ "type": "table", "title": "...", "columns": [...], "rows": [[...]],
  "posneg": [colIdx,...] }` — a data table. `posneg` lists the 0-based column
  indices whose cells should be colored by sign (green ↑ / red ↓, US convention).
  Put `暂无可靠数据` in any cell you can't fill.

**Content mapping cheatsheet** (build tables straight from `raw.json`):
- `overview` → 大盘表现 table: columns `指数 | 收盘 | 涨跌幅 | 日内高低 | 成交量 | 技术状态`,
  `posneg: [2]`. Then a `prose` 盘中复盘 + a `callout`(bull/bear) 今日市场状态.
- `macro` → 美债 table (`posneg` on the change column), FedWatch prose/table,
  美元黄金油加密 table (`posneg` on 涨跌幅), 经济数据 table.
- `sectors` → 11-sector table `板块 | ETF | 当日 | 近5日 | 近1月 | 主要驱动`
  (`posneg: [2,3,4]`); theme/style table; a `callout` 轮动判断.
- `breadth` → breadth tables (mostly `暂无可靠数据` unless researched) + the
  技术面 table from `tech_etfs`/`technicals_stocks`
  (`标的 | 价格 | 20/50/100/200日 | RSI | 趋势 | 支撑 | 压力`).
- `stocks` → 七巨头 table, AI 硬件 / 软件 / AI 电力 tables (`symbol | 涨跌幅 |
  原因 | 关注`, `posneg: [1]`), 其他显著异动, 重点关注股 table with your 判断 labels.
- `earnings` → 已公布财报 table, 未来 1–3 日财报日历 table, 机构观点 table.
- `plan` → 明日观察 prose/bullets, 风险矩阵 table (`风险维度 | 当前状态 | 风险等级`),
  最终结论 `callout`.

## Step 4: Do NOT update `web/manifest.json`

The orchestrator rebuilds `web/manifest.json` from disk via
`scripts/rebuild_manifest.py` (which already maps `USStocks → 美股复盘`). This
skill writes its data file and exits. If running standalone for local preview,
run `python3 scripts/rebuild_manifest.py` yourself afterward.

## Step 5: Validate

- `python3 -c "import json; json.load(open('web/USStocks/<date>/data.json'))"`
  parses without error.
- `format` is `"document"`, `date` equals `raw.json`'s `trading_day`, and there
  are 7 sections with non-empty `blocks`.
- Spot-check that index/sector numbers in the tables match `raw.json` and that
  every unfillable cell says `暂无可靠数据` (no fabricated values).

## Constraints & budget

- Simplified Chinese throughout; English for tickers/proper nouns.
- Never fabricate — `暂无可靠数据` is always preferable to a made-up number.
- Quality over completeness: a shorter, fully-sourced report beats a padded one.
- Do not modify `research_results/USStocks/` by hand — it is helper-managed.
- Budget: ~$15 per run; most quantitative work is the deterministic helper.
- This stage is **best-effort** in the daily pipeline — it must not block the
  AI briefing if a data source hiccups.
