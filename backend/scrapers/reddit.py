from __future__ import annotations

import re
import logging
from collections import defaultdict

import httpx

from backend.models.schemas import RedditPost, TickerMention

logger = logging.getLogger(__name__)

# Common words that look like tickers but aren't
FALSE_POSITIVES = {
    "I", "A", "AM", "AN", "AT", "BE", "BY", "DO", "GO", "IF", "IN", "IS",
    "IT", "ME", "MY", "NO", "OF", "OK", "ON", "OR", "SO", "TO", "UP", "US",
    "WE", "CEO", "CFO", "CTO", "COO", "IPO", "ETF", "SEC", "FDA", "FED",
    "GDP", "ATH", "DD", "DFV", "EPS", "EOD", "ERR", "EST", "FOR", "FYI",
    "GG", "HQ", "IMO", "LOL", "NYC", "OTC", "PDT", "PE", "PM", "PT",
    "RH", "SP", "TD", "UK", "USA", "WSB", "YOLO", "FOMO", "HODL", "MOON",
    "APE", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC",
    "JAN", "FEB", "MAR", "MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN",
    "THE", "AND", "BUT", "NOT", "ALL", "ANY", "ARE", "CAN", "DAY", "DID",
    "GET", "GOT", "HAS", "HAD", "HER", "HIM", "HIS", "HOW", "ITS", "LET",
    "MAD", "MAN", "MEN", "NEW", "NOW", "OLD", "ONE", "OUR", "OUT", "OWN",
    "PUT", "RAN", "RED", "RUN", "SAW", "SAY", "SHE", "THE", "TOO", "TOP",
    "TRY", "TWO", "WAR", "WAS", "WAY", "WHO", "WHY", "WIN", "WON", "YET",
    "YOU", "BIG", "LOW", "HIGH", "CALL", "PUTS", "LONG", "SHORT", "BULL",
    "BEAR", "HOLD", "SELL", "BUY", "GAIN", "LOSS", "PUMP", "DUMP", "CASH",
    "DEBT", "RISK", "SAFE", "EDIT", "TLDR", "OP", "LMAO", "ROPE", "RIP",
    "BANG", "OG", "AI", "EV", "GOOD", "BAD", "BEST", "LIKE", "JUST", "EVEN",
    "OVER", "MOST", "MUCH", "NEXT", "ONLY", "VERY", "WELL", "ALSO", "BACK",
    "BEEN", "COME", "DOWN", "EACH", "FIND", "GIVE", "HAVE", "HERE", "KEEP",
    "LAST", "LOOK", "MADE", "MAKE", "MANY", "MORE", "MOVE", "MUST", "NAME",
    "NEED", "OPEN", "PART", "PLAY", "REAL", "SAID", "SAME", "SOME", "SURE",
    "TAKE", "TELL", "THAN", "THAT", "THEM", "THEN", "THEY", "THIS", "TIME",
    "TURN", "WANT", "WEEK", "WENT", "WERE", "WHAT", "WHEN", "WILL", "WITH",
    "WORK", "YEAR", "YOUR", "FREE", "HUGE", "HARD", "ZERO", "LMFAO",
    "COST", "FROM", "DOES", "DONE", "FULL", "HALF", "HELP", "HOME", "INTO",
    "LEFT", "LESS", "LIFE", "LINE", "LIST", "LIVE", "LONG", "LOST", "MARK",
    "MISS", "OWE", "PAYS", "POST", "REST", "RICH", "RISE", "SAVE", "SIDE",
    "SIZE", "STOP", "TALK", "TERM", "THEM", "TILL", "TRUE", "TYPE", "USED",
    "WAIT", "WAKE", "WALL", "WISH", "WORD", "YALL", "HOLY", "SHIT",
}

# Regex: $TICKER or standalone 1-5 uppercase letters that look like tickers
TICKER_PATTERN = re.compile(r"\$([A-Z]{1,5})\b")
BARE_TICKER_PATTERN = re.compile(r"\b([A-Z]{2,5})\b")

# Use a browser-like user agent and add retry logic to avoid Reddit 429s
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
}


def _extract_tickers(text: str) -> list:
    """Extract likely stock tickers from text."""
    tickers = set()

    # $TICKER mentions (high confidence)
    for match in TICKER_PATTERN.findall(text):
        if match not in FALSE_POSITIVES and len(match) >= 1:
            tickers.add(match)

    # Bare uppercase words (lower confidence, require 2+ chars)
    for match in BARE_TICKER_PATTERN.findall(text):
        if match not in FALSE_POSITIVES and len(match) >= 2:
            tickers.add(match)

    return list(tickers)


def _fetch_reddit_json(url: str) -> list:
    """Fetch posts from a Reddit .json endpoint (no API key needed).

    Optimized for Vercel serverless (5s timeout, no retries).
    """
    posts = []
    try:
        resp = httpx.get(url, headers=HEADERS, timeout=5, follow_redirects=True)

        if resp.status_code == 429:
            logger.warning("Reddit rate limited (429)")
            return posts

        resp.raise_for_status()
        data = resp.json()

        children = data.get("data", {}).get("children", [])
        for child in children:
            post = child.get("data", {})
            if post.get("stickied"):
                continue
            posts.append(post)

    except Exception as e:
        logger.error(f"Reddit fetch error for {url}: {e}")

    return posts


def get_trending_tickers(
    subreddit: str = "wallstreetbets",
    time_filter: str = "day",
    limit: int = 100,
) -> list:
    """Scrape WSB for the most-mentioned stock tickers.

    Uses Reddit's public JSON feed — no API credentials needed.
    Returns tickers ranked by a weighted score of mentions + engagement.
    """
    mentions = defaultdict(
        lambda: {"count": 0, "score": 0, "comments": 0, "posts": []}
    )

    # Single request only — must stay under Vercel's 10s serverless limit
    cap = min(limit, 25)
    hot_url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={cap}"
    hot_posts = _fetch_reddit_json(hot_url)
    top_posts = []

    # Combine and deduplicate
    seen_ids = set()
    all_posts = []
    for post in hot_posts + top_posts:
        pid = post.get("id", "")
        if pid and pid not in seen_ids:
            seen_ids.add(pid)
            all_posts.append(post)

    logger.info(f"Fetched {len(all_posts)} posts from r/{subreddit}")

    for post in all_posts:
        title = post.get("title", "")
        selftext = post.get("selftext", "")
        text = f"{title} {selftext}"
        tickers = _extract_tickers(text)

        reddit_post = RedditPost(
            post_id=post.get("id", ""),
            title=title,
            selftext=selftext[:500],
            score=post.get("score", 0),
            num_comments=post.get("num_comments", 0),
            upvote_ratio=post.get("upvote_ratio", 0.0),
            created_utc=post.get("created_utc", 0.0),
            url=f"https://reddit.com{post.get('permalink', '')}",
            flair=post.get("link_flair_text"),
        )

        for ticker in tickers:
            data = mentions[ticker]
            data["count"] += 1
            data["score"] += reddit_post.score
            data["comments"] += reddit_post.num_comments
            if len(data["posts"]) < 5:
                data["posts"].append(reddit_post)

    # Build ranked list
    results = []
    for ticker, data in mentions.items():
        weighted = data["count"] * 3 + data["score"] * 0.01 + data["comments"] * 0.05
        results.append(
            TickerMention(
                ticker=ticker,
                mention_count=data["count"],
                total_score=data["score"],
                total_comments=data["comments"],
                weighted_score=round(weighted, 2),
                sample_posts=data["posts"],
            )
        )

    results.sort(key=lambda x: x.weighted_score, reverse=True)
    return results[:20]


def get_posts_for_ticker(
    ticker: str,
    subreddit: str = "wallstreetbets",
    limit: int = 25,
) -> list:
    """Get recent WSB posts mentioning a specific ticker."""
    url = (
        f"https://www.reddit.com/r/{subreddit}/search.json"
        f"?q={ticker}&restrict_sr=on&sort=relevance&t=week&limit={limit}"
    )
    raw_posts = _fetch_reddit_json(url)

    posts = []
    for post in raw_posts:
        title = post.get("title", "")
        selftext = post.get("selftext", "")
        text = f"{title} {selftext}"
        if ticker in _extract_tickers(text):
            posts.append(
                RedditPost(
                    post_id=post.get("id", ""),
                    title=title,
                    selftext=selftext[:1000],
                    score=post.get("score", 0),
                    num_comments=post.get("num_comments", 0),
                    upvote_ratio=post.get("upvote_ratio", 0.0),
                    created_utc=post.get("created_utc", 0.0),
                    url=f"https://reddit.com{post.get('permalink', '')}",
                    flair=post.get("link_flair_text"),
                )
            )

    return posts
