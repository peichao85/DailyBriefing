#!/usr/bin/env python3
"""
Fetch US-equities market data for the 美股复盘 (USStocks) daily briefing.

Stateless and key-free. Pulls everything price-based from three public sources
that are reachable without an API key:

  * CNBC  quote-html-webservice  -> snapshots (last/change/%/OHLC/volume/52wk)
                                    for indices (.SPX/.DJI/...), FX (.DXY),
                                    futures (@GC.1/@CL.1/@LCO.1) and crypto
                                    (BTC.CB=/ETH.CB=) as well as ETFs/stocks.
  * Nasdaq api  /quote/.../historical -> daily OHLCV history, used to compute
                                    5d/1mo returns and MA20/50/100/200, RSI14,
                                    MACD(12/26/9).
  * FRED  fredgraph.csv          -> Treasury yields (DGS2/10/30) and the
                                    2s10s spread (T10Y2Y).

It writes research_results/USStocks/<date>/raw.json. The Claude skill
(us_stocks_briefing) reads that file and layers on the narrative, news,
FedWatch, economic calendar, earnings and risk analysis that are not clean
number feeds.

What this helper deliberately does NOT try to compute: exchange-level breadth
internals (advance/decline, new highs/lows, McClellan, put/call). Those need
full-market constituent data that no key-free source exposes reliably, so they
are left for the skill to best-effort fetch or mark 暂无可靠数据.

Usage:
  python3 fetch_market_data.py --date 2026-06-01
  python3 fetch_market_data.py --date 2026-06-01 --project-root /path/to/repo
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
CNBC_URL = (
    "https://quote.cnbc.com/quote-html-webservice/restQuote/symbolType/symbol"
    "?symbols={syms}&requestMethod=itv&fund=1&exthrs=1&output=json"
)
NASDAQ_HIST = (
    "https://api.nasdaq.com/api/quote/{sym}/historical"
    "?assetclass={ac}&fromdate={frm}&todate={to}&limit={lim}"
)
FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"


# ---------------------------------------------------------------------------
# Symbol universe. (cnbc_symbol, display_name, [assetclass for history or None])
# assetclass=None  -> snapshot only (no history pull)
# ---------------------------------------------------------------------------

INDICES = [
    (".DJI", "道琼斯工业", None),
    (".SPX", "标普 500", None),
    (".IXIC", "纳斯达克综合", None),
    (".NDX", "纳斯达克 100", None),
    (".RUT", "罗素 2000", None),
    (".SOX", "费城半导体 SOX", None),
    (".VIX", "VIX 波动率", None),
]

# ETF proxies used for index technicals + the report's section-7 TA table.
TECH_ETFS = [
    ("SPY", "SPY 标普ETF", "etf"),
    ("QQQ", "QQQ 纳指100ETF", "etf"),
    ("DIA", "DIA 道指ETF", "etf"),
    ("IWM", "IWM 罗素2000ETF", "etf"),
    ("SMH", "SMH 半导体ETF", "etf"),
    ("IGV", "IGV 软件ETF", "etf"),
]

SECTOR_ETFS = [
    ("XLK", "信息技术", "etf"),
    ("XLC", "通信服务", "etf"),
    ("XLY", "可选消费", "etf"),
    ("XLF", "金融", "etf"),
    ("XLI", "工业", "etf"),
    ("XLV", "医疗保健", "etf"),
    ("XLP", "必需消费", "etf"),
    ("XLE", "能源", "etf"),
    ("XLU", "公用事业", "etf"),
    ("XLB", "材料", "etf"),
    ("XLRE", "房地产", "etf"),
]

THEME_ETFS = [
    ("SOXX", "半导体 SOXX", "etf"),
    ("CIBR", "网络安全 CIBR", "etf"),
    ("CLOU", "云计算 CLOU", "etf"),
    ("BOTZ", "AI/自动化 BOTZ", "etf"),
    ("AIQ", "AI/自动化 AIQ", "etf"),
    ("IWO", "小盘成长 IWO", "etf"),
    ("IWN", "小盘价值 IWN", "etf"),
    ("RSP", "等权标普 RSP", "etf"),
    ("SCHG", "大盘成长 SCHG", "etf"),
    ("VTV", "大盘价值 VTV", "etf"),
]

MACRO_ASSETS = [
    (".DXY", "美元指数 DXY", None),
    ("@GC.1", "黄金", None),
    ("@CL.1", "WTI 原油", None),
    ("@LCO.1", "Brent 原油", None),
    ("BTC.CB=", "比特币", None),
    ("ETH.CB=", "以太坊", None),
]

# Watchlist stock groups (report sections 8 & 12). History only for mag7 +
# a curated key set, to bound runtime / Nasdaq rate-limiting.
MAG7 = ["NVDA", "MSFT", "AAPL", "GOOGL", "AMZN", "META", "TSLA"]
AI_HARDWARE = ["NVDA", "AMD", "AVGO", "MRVL", "MU", "TSM", "ASML", "ARM",
               "INTC", "QCOM", "SMCI", "DELL", "HPE", "ANET", "CLS", "VRT",
               "COHR", "LITE", "AAOI"]
SOFTWARE = ["CRM", "NOW", "SNOW", "ORCL", "ADBE", "PANW", "CRWD", "DDOG",
            "NET", "MDB", "PLTR", "APP", "TEAM", "WDAY", "INTU", "SHOP"]
AI_POWER = ["CEG", "VST", "NRG", "ETN", "PWR", "GEV", "VRT", "FLNC", "OKLO",
            "SMR", "BE", "NEE", "SO", "DUK", "APLD", "IREN", "CORZ"]
# Pull history (for technicals) for these stocks only.
HISTORY_STOCKS = set(MAG7 + ["AVGO", "AMD", "MRVL", "PLTR", "CRM", "ORCL",
                             "VRT", "ANET", "CEG", "VST", "OKLO", "COHR"])

FRED_SERIES = [
    ("DGS2", "2 年期美债收益率"),
    ("DGS10", "10 年期美债收益率"),
    ("DGS30", "30 年期美债收益率"),
    ("T10Y2Y", "2Y-10Y 利差"),
]


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _get(url: str, timeout: int = 20, ua: str = UA) -> bytes:
    req = urllib.request.Request(url, headers={
        "User-Agent": ua,
        "Accept": "application/json, text/plain, */*",
    })
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def cnbc_quotes(symbols: list[str]) -> dict[str, dict]:
    """Return {symbol: quote_dict} for a batch of CNBC symbols."""
    out: dict[str, dict] = {}
    # CNBC accepts a pipe-separated list; chunk to keep URLs sane.
    for i in range(0, len(symbols), 25):
        chunk = symbols[i:i + 25]
        syms = urllib.parse.quote("|".join(chunk), safe="")
        try:
            data = json.loads(_get(CNBC_URL.format(syms=syms)))
            quotes = data["FormattedQuoteResult"]["FormattedQuote"]
            if isinstance(quotes, dict):
                quotes = [quotes]
            for q in quotes:
                if q.get("symbol"):
                    out[q["symbol"]] = q
        except Exception as e:  # noqa: BLE001 - degrade gracefully
            sys.stderr.write(f"[cnbc] chunk {chunk} failed: {e}\n")
        time.sleep(0.4)
    return out


def _to_float(s) -> float | None:
    if s is None:
        return None
    try:
        return float(str(s).replace(",", "").replace("$", "").replace("%", "").replace("+", ""))
    except (ValueError, TypeError):
        return None


def nasdaq_history(symbol: str, assetclass: str, days: int = 360) -> list[dict]:
    """Return ascending [{date, open, high, low, close, volume}] or []."""
    to = datetime.now(timezone.utc).date()
    frm = to - timedelta(days=days)
    url = NASDAQ_HIST.format(sym=symbol, ac=assetclass,
                             frm=frm.isoformat(), to=to.isoformat(), lim=400)
    try:
        data = json.loads(_get(url))
        rows = (data.get("data") or {}).get("tradesTable", {}).get("rows") or []
    except Exception as e:  # noqa: BLE001
        sys.stderr.write(f"[nasdaq] {symbol} history failed: {e}\n")
        return []
    parsed = []
    for r in rows:
        try:
            d = datetime.strptime(r["date"], "%m/%d/%Y").date().isoformat()
        except (ValueError, KeyError):
            continue
        parsed.append({
            "date": d,
            "open": _to_float(r.get("open")),
            "high": _to_float(r.get("high")),
            "low": _to_float(r.get("low")),
            "close": _to_float(r.get("close")),
            "volume": _to_float(r.get("volume")),
        })
    parsed.sort(key=lambda x: x["date"])  # ascending
    return parsed


def fred_latest(series_id: str) -> dict | None:
    """Return {date, value, change} for the two most recent valid points."""
    try:
        # FRED's WAF stalls browser-like User-Agents; a plain client UA is served
        # instantly. Use a generic UA here only.
        raw = _get(FRED_CSV.format(sid=series_id), ua="python-urllib/3").decode("utf-8")
    except Exception as e:  # noqa: BLE001
        sys.stderr.write(f"[fred] {series_id} failed: {e}\n")
        return None
    rows = list(csv.reader(io.StringIO(raw)))[1:]  # skip header
    vals = []
    for row in rows:
        if len(row) < 2:
            continue
        v = _to_float(row[1])
        if v is not None:
            vals.append((row[0], v))
    if not vals:
        return None
    date, value = vals[-1]
    change = round(value - vals[-2][1], 3) if len(vals) >= 2 else None
    return {"date": date, "value": value, "change": change}


# ---------------------------------------------------------------------------
# Indicator math (pure Python — pandas is not available in this env)
# ---------------------------------------------------------------------------

def sma(closes: list[float], n: int) -> float | None:
    if len(closes) < n:
        return None
    return round(sum(closes[-n:]) / n, 2)


def rsi(closes: list[float], n: int = 14) -> float | None:
    if len(closes) < n + 1:
        return None
    gains, losses = [], []
    for i in range(-n, 0):
        diff = closes[i] - closes[i - 1]
        gains.append(max(diff, 0.0))
        losses.append(max(-diff, 0.0))
    avg_gain = sum(gains) / n
    avg_loss = sum(losses) / n
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - 100 / (1 + rs), 1)


def _ema(values: list[float], n: int) -> list[float]:
    k = 2 / (n + 1)
    ema = [values[0]]
    for v in values[1:]:
        ema.append(v * k + ema[-1] * (1 - k))
    return ema


def macd(closes: list[float]) -> dict | None:
    if len(closes) < 35:
        return None
    ema12 = _ema(closes, 12)
    ema26 = _ema(closes, 26)
    macd_line = [a - b for a, b in zip(ema12, ema26)]
    signal = _ema(macd_line[25:], 9)  # align to where ema26 is meaningful
    return {
        "macd": round(macd_line[-1], 2),
        "signal": round(signal[-1], 2),
        "hist": round(macd_line[-1] - signal[-1], 2),
    }


def pct_return(closes: list[float], n: int) -> float | None:
    """Return over the last n trading days, in percent."""
    if len(closes) < n + 1:
        return None
    return round((closes[-1] / closes[-n - 1] - 1) * 100, 2)


def trend_label(price, ma20, ma50, ma200) -> str:
    if None in (price, ma50, ma200):
        return "数据不足"
    if price > ma50 > ma200:
        return "多头排列"
    if price < ma50 < ma200:
        return "空头排列"
    if ma200 and price > ma200:
        return "中期偏多"
    return "中期偏弱"


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------

def snapshot(q: dict) -> dict:
    return {
        "last": _to_float(q.get("last")),
        "change": _to_float(q.get("change")),
        "change_pct": q.get("change_pct"),
        "open": _to_float(q.get("open")),
        "high": _to_float(q.get("high")),
        "low": _to_float(q.get("low")),
        "volume": q.get("volume"),
        "prev_close": _to_float(q.get("previous_day_closing")),
        "yr_high": _to_float(q.get("yrhiprice")),
        "yr_low": _to_float(q.get("yrloprice")),
        "name": q.get("name"),
    }


def build_group(rows, quotes, hist_cache, want_returns=False, want_tech=False):
    out = []
    for sym, name, ac in rows:
        q = quotes.get(sym, {})
        rec = {"symbol": sym, "name": name}
        rec.update(snapshot(q))
        rec["name"] = name  # prefer our Chinese label
        if (want_returns or want_tech) and ac:
            closes = [h["close"] for h in hist_cache.get(sym, []) if h["close"]]
            if want_returns:
                rec["ret_5d"] = pct_return(closes, 5)
                rec["ret_1mo"] = pct_return(closes, 21)
            if want_tech and closes:
                price = closes[-1]
                ma20, ma50 = sma(closes, 20), sma(closes, 50)
                ma100, ma200 = sma(closes, 100), sma(closes, 200)
                rec["tech"] = {
                    "price": price, "ma20": ma20, "ma50": ma50,
                    "ma100": ma100, "ma200": ma200,
                    "rsi14": rsi(closes), "macd": macd(closes),
                    "trend": trend_label(price, ma20, ma50, ma200),
                }
        out.append(rec)
    return out


def stock_group(symbols, quotes):
    out = []
    seen = set()
    for sym in symbols:
        if sym in seen:
            continue
        seen.add(sym)
        q = quotes.get(sym, {})
        out.append({
            "symbol": sym,
            "name": q.get("name") or sym,
            "last": _to_float(q.get("last")),
            "change_pct": q.get("change_pct"),
            "change": _to_float(q.get("change")),
        })
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--date", default=datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    ap.add_argument("--project-root", default=None)
    args = ap.parse_args()

    project_root = (Path(args.project_root).resolve() if args.project_root
                    else Path(__file__).resolve().parents[3])

    # --- gather all CNBC symbols in one go ---
    all_rows = (INDICES + TECH_ETFS + SECTOR_ETFS + THEME_ETFS + MACRO_ASSETS)
    cnbc_symbols = [r[0] for r in all_rows]
    stock_symbols = sorted(set(MAG7 + AI_HARDWARE + SOFTWARE + AI_POWER))
    print(f"Fetching CNBC snapshots: {len(cnbc_symbols)} instruments + "
          f"{len(stock_symbols)} stocks ...")
    quotes = cnbc_quotes(cnbc_symbols + stock_symbols)
    print(f"  got {len(quotes)} quotes")

    # --- history for ETFs (returns + tech) and selected stocks (tech) ---
    hist_cache: dict[str, list] = {}
    hist_targets = ([(s, ac) for s, _, ac in TECH_ETFS + SECTOR_ETFS + THEME_ETFS if ac]
                    + [(s, "stocks") for s in sorted(HISTORY_STOCKS)])
    print(f"Fetching Nasdaq history for {len(hist_targets)} symbols ...")
    for sym, ac in hist_targets:
        hist_cache[sym] = nasdaq_history(sym, ac)
        time.sleep(0.3)
    got_hist = sum(1 for v in hist_cache.values() if v)
    print(f"  got history for {got_hist}/{len(hist_targets)} symbols")

    # --- FRED yields ---
    print("Fetching FRED yields ...")
    yields = {}
    for sid, label in FRED_SERIES:
        rec = fred_latest(sid)
        if rec:
            rec["label"] = label
            yields[sid] = rec
        time.sleep(0.2)

    # --- determine the trading day actually represented by the data ---
    trading_day = None
    for sym in ("SPY", "QQQ"):
        if hist_cache.get(sym):
            trading_day = hist_cache[sym][-1]["date"]
            break
    if not trading_day:
        # fall back to CNBC last_time of .SPX
        trading_day = (quotes.get(".SPX", {}).get("last_time") or args.date)

    # --- mover groups (snapshot-only) ---
    movers = {
        "mag7": stock_group(MAG7, quotes),
        "ai_hardware": stock_group(AI_HARDWARE, quotes),
        "software": stock_group(SOFTWARE, quotes),
        "ai_power": stock_group(AI_POWER, quotes),
    }
    # top gainers / losers across the whole stock universe
    universe = [s for g in movers.values() for s in g if s["change"] is not None]
    by_pct = sorted(universe, key=lambda s: _to_float(s["change_pct"]) or 0)
    top_losers = [s for s in by_pct[:8]]
    top_gainers = [s for s in by_pct[::-1][:8]]

    raw = {
        "report_date": args.date,
        "trading_day": trading_day,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_notes": {
            "snapshots": "CNBC quote-html-webservice (delayed)",
            "history": "Nasdaq api historical",
            "yields": "FRED fredgraph.csv",
            "breadth_internals": "NOT fetched — skill marks best-effort / 暂无可靠数据",
        },
        "indices": build_group(INDICES, quotes, hist_cache),
        "tech_etfs": build_group(TECH_ETFS, quotes, hist_cache, want_tech=True),
        "sectors": build_group(SECTOR_ETFS, quotes, hist_cache,
                               want_returns=True, want_tech=True),
        "themes": build_group(THEME_ETFS, quotes, hist_cache, want_returns=True),
        "macro_assets": build_group(MACRO_ASSETS, quotes, hist_cache),
        "yields": yields,
        "technicals_stocks": [
            {"symbol": s, **(lambda c: {
                "price": c[-1] if c else None,
                "ma20": sma(c, 20), "ma50": sma(c, 50),
                "ma100": sma(c, 100), "ma200": sma(c, 200),
                "rsi14": rsi(c), "macd": macd(c),
                "trend": trend_label(c[-1] if c else None, sma(c, 20),
                                     sma(c, 50), sma(c, 200)),
            })([h["close"] for h in hist_cache.get(s, []) if h["close"]])}
            for s in sorted(HISTORY_STOCKS)
        ],
        "movers": movers,
        "top_gainers": top_gainers,
        "top_losers": top_losers,
    }

    out_dir = project_root / "research_results" / "USStocks" / args.date
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "raw.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(raw, f, ensure_ascii=False, indent=2)
    print(f"\nWrote {out_path}")
    print(f"  trading_day={trading_day}  indices={len(raw['indices'])}  "
          f"sectors={len(raw['sectors'])}  yields={len(yields)}  "
          f"stocks_tech={got_hist}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
