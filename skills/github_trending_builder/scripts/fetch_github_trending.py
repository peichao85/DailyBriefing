#!/usr/bin/env python3
"""
Fetch GitHub trending data for the daily briefing.

Produces two groupings:
  - new_hot:     top 10 repos created in the last 7 days, sorted by absolute stars
  - rising_stars: top 10 existing repos ranked by stars gained in the last 7 days

The "stars gained" metric is computed at runtime from the GitHub stargazers
endpoint (with the `star+json` media type, which returns per-star timestamps).
No state is persisted between runs.

Outputs:
  research_results/GitHub/<date>/raw.json   -- candidate data for the Chinese
                                              summarization pass
  web/GitHub/<date>/img/<owner>-<repo>.jpg  -- 256x256 owner avatars (JPEG)

The SKILL.md reads raw.json, generates Chinese fields, then writes the final
web/GitHub/<date>/data.json. This script intentionally does NOT write data.json
itself.

Usage:
  python3 fetch_github_trending.py --date 2026-04-10
  python3 fetch_github_trending.py --repo huggingface/transformers --debug
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from typing import Iterable

import requests
from PIL import Image

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

WINDOW_DAYS = 7

# Authenticated: generous pool; unauth: much tighter to stay under 60/hr.
CANDIDATE_POOL_AUTH = 30
CANDIDATE_POOL_UNAUTH = 15

# How far to walk the stargazers pagination per repo before giving up.
# GraphQL: cheap (each query ~1 point, 5000-point/hr budget) — use a generous cap
# so ranking works for repos gaining thousands of stars/week.
# REST: expensive (each call = 1 request, 5000 req/hr) — stay conservative.
MAX_STARGAZER_PAGES_AUTH = 30  # 3000 stars/week ceiling — plenty for ranking
MAX_STARGAZER_PAGES_UNAUTH = 2

MIN_STARS_THRESHOLD = 500  # for the rising-stars candidate pool
PICK_PER_SECTION = 10

AI_DEV_TOPICS = {
    # AI / ML
    "ai", "artificial-intelligence", "llm", "llms", "large-language-models",
    "machine-learning", "ml", "deep-learning", "nlp", "rag", "agent", "agents",
    "agentic", "mcp", "transformers", "diffusion", "generative-ai", "chatbot",
    # Dev tools
    "cli", "editor", "ide", "devtools", "developer-tools", "tooling",
    "vscode", "neovim", "terminal", "shell", "language-server",
    "code-editor", "code-completion", "copilot",
}

AI_DESCRIPTION_REGEX = re.compile(
    r"\b(ai|llm|agent|rag|mcp|llama|gpt|claude|chatbot|copilot|coding assistant)\b",
    re.IGNORECASE,
)

API_ROOT = "https://api.github.com"
GRAPHQL_URL = "https://api.github.com/graphql"
USER_AGENT = "DailyBriefing-GitHubTrending/1.0"

# REST stargazers endpoint caps pagination at ~400 pages (40k stars).
# Repos above this size cannot have stars-gained computed via REST.
REST_STARGAZER_MAX_PAGE = 400

log = logging.getLogger("fetch_github_trending")


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


def resolve_token() -> tuple[str | None, str]:
    """Returns (token, mode) where mode is 'gh', 'env', or 'unauth'."""
    # 1. gh CLI
    try:
        result = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip(), "gh"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    # 2. env
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        return token, "env"
    # 3. unauth
    return None, "unauth"


def make_session(token: str | None) -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": USER_AGENT,
        }
    )
    if token:
        s.headers["Authorization"] = f"Bearer {token}"
    return s


def api_get(session: requests.Session, url: str, *, accept: str | None = None,
            params: dict | None = None) -> requests.Response:
    headers = {}
    if accept:
        headers["Accept"] = accept
    for attempt in range(3):
        try:
            r = session.get(url, headers=headers, params=params, timeout=15)
        except requests.RequestException as e:
            log.warning("request error %s: %s (attempt %d)", url, e, attempt + 1)
            time.sleep(1 + attempt)
            continue
        # Rate limit: sleep briefly and retry on 403 with x-ratelimit-remaining: 0
        if r.status_code == 403 and r.headers.get("x-ratelimit-remaining") == "0":
            reset = int(r.headers.get("x-ratelimit-reset", "0"))
            wait = max(1, reset - int(time.time()) + 1)
            if wait > 60:
                log.error("rate limit hit, reset in %ds — aborting", wait)
                r.raise_for_status()
            log.warning("rate limit hit, sleeping %ds", wait)
            time.sleep(wait)
            continue
        return r
    r.raise_for_status()
    return r


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


@dataclass
class Repo:
    owner: str
    repo: str
    full_name: str
    html_url: str
    description: str
    topics: list[str]
    stars: int
    forks: int
    language: str | None
    created_at: str
    pushed_at: str
    avatar_url: str
    # Populated later
    readme_excerpt: str = ""
    stars_gained: int | None = None
    avatar_path: str | None = None


def search_rising_candidates(session: requests.Session, window_start: datetime,
                              per_page: int) -> list[Repo]:
    """Query the Search API for recently-active popular repos (rising pool)."""
    date_str = window_start.date().isoformat()
    q = f"pushed:>{date_str} stars:>{MIN_STARS_THRESHOLD}"
    log.info("rising search: q=%s per_page=%d", q, per_page)
    r = api_get(
        session,
        f"{API_ROOT}/search/repositories",
        params={"q": q, "sort": "stars", "order": "desc", "per_page": per_page},
    )
    r.raise_for_status()
    items = r.json().get("items", [])
    log.info("rising search returned %d candidates", len(items))
    return [repo_from_search_item(it) for it in items]


def search_new_candidates(session: requests.Session, window_start: datetime,
                          per_page: int) -> list[Repo]:
    """
    Query the Search API for brand-new repos sorted by stars.

    Uses `created:>{window_start}` with no star threshold — the `sort=stars`
    parameter naturally surfaces the top new repos. Without this separate
    query, the rising-pool search would miss new repos below 500 stars.
    """
    date_str = window_start.date().isoformat()
    q = f"created:>{date_str}"
    log.info("new search: q=%s per_page=%d", q, per_page)
    r = api_get(
        session,
        f"{API_ROOT}/search/repositories",
        params={"q": q, "sort": "stars", "order": "desc", "per_page": per_page},
    )
    r.raise_for_status()
    items = r.json().get("items", [])
    log.info("new search returned %d candidates", len(items))
    return [repo_from_search_item(it) for it in items]


def repo_from_search_item(item: dict) -> Repo:
    return Repo(
        owner=item["owner"]["login"],
        repo=item["name"],
        full_name=item["full_name"],
        html_url=item["html_url"],
        description=item.get("description") or "",
        topics=list(item.get("topics") or []),
        stars=int(item.get("stargazers_count") or 0),
        forks=int(item.get("forks_count") or 0),
        language=item.get("language"),
        created_at=item.get("created_at") or "",
        pushed_at=item.get("pushed_at") or "",
        avatar_url=item["owner"].get("avatar_url") or "",
    )


def filter_by_topic(repos: list[Repo], min_kept: int = 15) -> list[Repo]:
    """Keep repos matching the AI/dev topic whitelist, with a description fallback."""
    primary = [r for r in repos if set(r.topics) & AI_DEV_TOPICS]
    if len(primary) >= min_kept:
        return primary
    # Fallback: add repos whose description looks AI-ish
    extra_ids = {r.full_name for r in primary}
    secondary = [
        r for r in repos
        if r.full_name not in extra_ids and AI_DESCRIPTION_REGEX.search(r.description or "")
    ]
    combined = primary + secondary
    if len(combined) >= min_kept:
        return combined
    # Last resort: pad with top unfiltered
    padding = [r for r in repos if r.full_name not in {x.full_name for x in combined}]
    return combined + padding[: max(0, min_kept - len(combined))]


# ---------------------------------------------------------------------------
# Stars-gained delta
# ---------------------------------------------------------------------------


def stars_gained_via_graphql(session: requests.Session, repo: Repo,
                             window_start: datetime, max_pages: int) -> int:
    """
    Preferred path (auth only): use GraphQL to fetch the most recent stars
    directly via orderBy: {field: STARRED_AT, direction: DESC}. No 400-page
    cap, works for repos of any size.

    Each page is 100 stargazers. Stop as soon as a page contains an entry
    older than window_start, or when the max_pages budget is exhausted.
    """
    query = """
    query($owner: String!, $name: String!, $cursor: String) {
      repository(owner: $owner, name: $name) {
        stargazers(first: 100, orderBy: {field: STARRED_AT, direction: DESC}, after: $cursor) {
          pageInfo { hasNextPage endCursor }
          edges { starredAt }
        }
      }
    }
    """
    total = 0
    cursor: str | None = None
    for page in range(max_pages):
        payload = {
            "query": query,
            "variables": {"owner": repo.owner, "name": repo.repo, "cursor": cursor},
        }
        try:
            r = session.post(GRAPHQL_URL, json=payload, timeout=15)
            r.raise_for_status()
            data = r.json()
        except requests.RequestException as e:
            log.warning("graphql stargazers failed for %s: %s", repo.full_name, e)
            return total
        if "errors" in data:
            log.warning("graphql errors for %s: %s", repo.full_name, data["errors"])
            return total
        sg = (data.get("data") or {}).get("repository", {}).get("stargazers")
        if not sg:
            return total
        edges = sg.get("edges") or []
        if not edges:
            break
        in_window = [e for e in edges if parse_iso8601(e["starredAt"]) >= window_start]
        total += len(in_window)
        if len(in_window) < len(edges):
            break  # Hit the window boundary on this page.
        if not sg["pageInfo"]["hasNextPage"]:
            break
        cursor = sg["pageInfo"]["endCursor"]
    return total


def stars_gained_via_rest(session: requests.Session, repo: Repo,
                          window_start: datetime, max_pages: int) -> int:
    """
    Fallback for unauthenticated mode (GraphQL requires auth).

    Walks backwards from the last REST page of /stargazers?per_page=100.
    Skips repos where last_page > REST_STARGAZER_MAX_PAGE because the REST
    endpoint returns 422 beyond that cap. For those repos we return 0 and
    they naturally drop out of the rising-stars ranking.
    """
    if repo.stars <= 0:
        return 0
    last_page = math.ceil(repo.stars / 100)
    if last_page > REST_STARGAZER_MAX_PAGE:
        log.info("%s has %d stars — beyond REST 40k cap, skipping delta",
                 repo.full_name, repo.stars)
        return 0
    total = 0
    page = last_page
    walked = 0
    while page >= 1 and walked < max_pages:
        url = f"{API_ROOT}/repos/{repo.owner}/{repo.repo}/stargazers"
        try:
            r = api_get(
                session,
                url,
                accept="application/vnd.github.star+json",
                params={"per_page": 100, "page": page},
            )
        except requests.HTTPError as e:
            log.warning("stargazers fetch failed for %s page %d: %s",
                        repo.full_name, page, e)
            return total
        if r.status_code != 200:
            log.warning("stargazers %s page %d: HTTP %d",
                        repo.full_name, page, r.status_code)
            return total
        entries = r.json()
        if not isinstance(entries, list) or not entries:
            break
        if "starred_at" not in entries[0]:
            log.error("starred_at missing for %s — media type header stripped?",
                      repo.full_name)
            return 0
        in_window = [e for e in entries if parse_iso8601(e["starred_at"]) >= window_start]
        total += len(in_window)
        walked += 1
        if len(in_window) < len(entries):
            break
        page -= 1
    if walked >= max_pages and page >= 1:
        log.info("%s: hit max pages (%d) while counting", repo.full_name, max_pages)
    return total


def stars_gained_in_window(session: requests.Session, repo: Repo,
                           window_start: datetime, max_pages: int,
                           *, auth_mode: str) -> int:
    """Dispatch: GraphQL for authenticated modes, REST fallback otherwise."""
    if auth_mode in ("gh", "env"):
        return stars_gained_via_graphql(session, repo, window_start, max_pages)
    return stars_gained_via_rest(session, repo, window_start, max_pages)


def parse_iso8601(s: str) -> datetime:
    # Handles both "2026-04-10T12:34:56Z" and with offset
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s)


def parse_iso8601_safe(s: str) -> datetime:
    """Like parse_iso8601 but returns a very old date on parse failure."""
    try:
        return parse_iso8601(s)
    except (ValueError, TypeError):
        return datetime(1970, 1, 1, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# README + avatar
# ---------------------------------------------------------------------------


def fetch_readme_excerpt(session: requests.Session, repo: Repo, max_chars: int = 800) -> str:
    url = f"{API_ROOT}/repos/{repo.owner}/{repo.repo}/readme"
    try:
        r = api_get(session, url, accept="application/vnd.github.raw")
        if r.status_code != 200:
            return ""
        text = r.text
    except requests.RequestException as e:
        log.info("readme fetch failed for %s: %s", repo.full_name, e)
        return ""
    # Strip trivial markdown noise (headings markers, html comments)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    text = re.sub(r"!\[.*?\]\(.*?\)", "", text)  # images
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)  # links → text
    text = re.sub(r"\s+\n", "\n", text)
    return text.strip()[:max_chars]


def download_avatar(session: requests.Session, repo: Repo, out_dir: Path) -> str | None:
    if not repo.avatar_url:
        return None
    out_name = f"{repo.owner}-{repo.repo}.jpg"
    out_path = out_dir / out_name
    try:
        # Avatar CDN doesn't need our auth and is outside the api.github.com host.
        r = requests.get(repo.avatar_url, timeout=15,
                         headers={"User-Agent": USER_AGENT})
        r.raise_for_status()
        img = Image.open(BytesIO(r.content)).convert("RGB")
        img = img.resize((256, 256), Image.LANCZOS)
        out_dir.mkdir(parents=True, exist_ok=True)
        img.save(out_path, "JPEG", quality=85, optimize=True)
        return f"img/{out_name}"
    except Exception as e:
        log.warning("avatar download failed for %s: %s", repo.full_name, e)
        return None


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------


def run(date_str: str, project_root: Path) -> dict:
    token, mode = resolve_token()
    log.info("auth mode: %s", mode)

    pool_size = CANDIDATE_POOL_AUTH if mode != "unauth" else CANDIDATE_POOL_UNAUTH
    max_pages = MAX_STARGAZER_PAGES_AUTH if mode != "unauth" else MAX_STARGAZER_PAGES_UNAUTH

    now = datetime.now(timezone.utc)
    window_start = now - timedelta(days=WINDOW_DAYS)

    session = make_session(token)

    # 1a. Rising candidates (recently active popular repos)
    rising_raw = search_rising_candidates(session, window_start, pool_size)
    rising_filtered = filter_by_topic(rising_raw, min_kept=max(15, PICK_PER_SECTION + 5))
    log.info("after topic filter (rising): %d", len(rising_filtered))

    # 1b. New candidates (brand-new repos sorted by stars)
    new_raw = search_new_candidates(session, window_start, pool_size)
    new_filtered = filter_by_topic(new_raw, min_kept=max(15, PICK_PER_SECTION + 5))
    log.info("after topic filter (new): %d", len(new_filtered))

    # 2. Drop any repo from the rising pool that was created within the window
    # (it belongs in new_hot, not rising). Also dedupe by full_name across pools.
    new_names = {r.full_name for r in new_filtered}
    rising_candidates = [
        r for r in rising_filtered
        if r.full_name not in new_names and parse_iso8601_safe(r.created_at) < window_start
    ]

    # 3. new_hot: sort by absolute stars desc, take top 10
    new_hot = sorted(new_filtered, key=lambda r: r.stars, reverse=True)[:PICK_PER_SECTION]

    # 4. rising_stars: compute 7d delta, rank, take top 10
    for r in rising_candidates:
        r.stars_gained = stars_gained_in_window(
            session, r, window_start, max_pages, auth_mode=mode
        )
    rising_candidates.sort(key=lambda r: (r.stars_gained or 0), reverse=True)
    rising = [r for r in rising_candidates if (r.stars_gained or 0) > 0][:PICK_PER_SECTION]

    # 6. Enrich all picks with README excerpts + avatar downloads
    web_img_dir = project_root / "web" / "GitHub" / date_str / "img"
    selected = new_hot + rising
    for r in selected:
        r.readme_excerpt = fetch_readme_excerpt(session, r)
        r.avatar_path = download_avatar(session, r, web_img_dir)

    # 7. Write raw.json (inputs for Chinese-summary pass)
    raw_dir = project_root / "research_results" / "GitHub" / date_str
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_path = raw_dir / "raw.json"
    payload = {
        "date": date_str,
        "generated_at": now.isoformat(),
        "auth_mode": mode,
        "window_days": WINDOW_DAYS,
        "sections": [
            {
                "id": "new_hot",
                "label": "新晋热门",
                "subtitle": "过去 7 天新建仓库按星数排序",
                "repos": [asdict(r) for r in new_hot],
            },
            {
                "id": "rising_stars",
                "label": "上升之星",
                "subtitle": "过去 7 天星数增长最快",
                "repos": [asdict(r) for r in rising],
            },
        ],
    }
    with raw_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    log.info("wrote %s", raw_path)
    log.info("new_hot=%d rising=%d", len(new_hot), len(rising))
    return payload


def debug_single_repo(full_name: str) -> None:
    token, mode = resolve_token()
    log.info("debug mode, auth=%s, repo=%s", mode, full_name)
    session = make_session(token)
    owner, name = full_name.split("/", 1)
    r = api_get(session, f"{API_ROOT}/repos/{owner}/{name}")
    r.raise_for_status()
    data = r.json()
    repo = Repo(
        owner=owner,
        repo=name,
        full_name=full_name,
        html_url=data["html_url"],
        description=data.get("description") or "",
        topics=list(data.get("topics") or []),
        stars=int(data.get("stargazers_count") or 0),
        forks=int(data.get("forks_count") or 0),
        language=data.get("language"),
        created_at=data.get("created_at") or "",
        pushed_at=data.get("pushed_at") or "",
        avatar_url=data["owner"].get("avatar_url") or "",
    )
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(days=WINDOW_DAYS)
    max_pages = MAX_STARGAZER_PAGES_AUTH if mode != "unauth" else MAX_STARGAZER_PAGES_UNAUTH
    gained = stars_gained_in_window(session, repo, window_start, max_pages, auth_mode=mode)
    print(f"{full_name}: total_stars={repo.stars} gained_last_{WINDOW_DAYS}d={gained}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--date", help="YYYY-MM-DD (default: today UTC)")
    ap.add_argument("--project-root", default=None,
                    help="Project root (default: auto-detect from script path)")
    ap.add_argument("--repo", help="Debug: inspect a single repo owner/name")
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    if args.repo:
        debug_single_repo(args.repo)
        return 0

    date_str = args.date or datetime.now(timezone.utc).date().isoformat()

    if args.project_root:
        project_root = Path(args.project_root).resolve()
    else:
        # skills/github_trending_builder/scripts/fetch_github_trending.py
        project_root = Path(__file__).resolve().parents[3]

    run(date_str, project_root)
    return 0


if __name__ == "__main__":
    sys.exit(main())
