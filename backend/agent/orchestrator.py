"""Claude agent orchestrator — the brain of the WSB analyst."""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from typing import Optional

import anthropic

from backend.agent.prompts import ORCHESTRATOR_SYSTEM_PROMPT, SENTIMENT_SYSTEM_PROMPT
from backend.agent.tools import TOOLS
from backend.analysis.fundamental import analyze_fundamentals
from backend.analysis.risk import analyze_risk
from backend.analysis.technical import analyze_technicals
from backend.config import settings
from backend.data.market import get_stock_data, get_financial_statements
from backend.models.schemas import (
    AnalysisResult,
    Sentiment,
    SentimentReport,
    Signal,
    StockRecommendation,
)
from backend.scrapers.reddit import get_posts_for_ticker, get_trending_tickers

logger = logging.getLogger(__name__)


def _get_client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


def _has_api_credits() -> bool:
    """Check if we can make Claude API calls."""
    if not settings.anthropic_api_key:
        return False
    try:
        client = _get_client()
        client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=10,
            messages=[{"role": "user", "content": "hi"}],
        )
        return True
    except Exception as e:
        logger.warning(f"Claude API not available: {e}")
        return False


# ── Local analysis (no Claude needed) ────────────────────────


def _compute_signal(score: float) -> Signal:
    """Convert a 0-100 score to a buy/sell signal."""
    if score >= 75:
        return Signal.STRONG_BUY
    elif score >= 60:
        return Signal.BUY
    elif score >= 40:
        return Signal.HOLD
    elif score >= 25:
        return Signal.SELL
    else:
        return Signal.STRONG_SELL


def _basic_sentiment_from_posts(ticker: str, posts: list) -> SentimentReport:
    """Simple keyword-based sentiment (no AI). Works offline."""
    if not posts:
        return SentimentReport(
            ticker=ticker,
            sentiment=Sentiment.NEUTRAL,
            confidence=0.0,
            summary=f"No recent WSB posts found for {ticker}",
        )

    bullish_words = {"moon", "rocket", "buy", "calls", "bull", "long", "undervalued",
                     "squeeze", "green", "tendies", "gain", "up", "rip", "breakout",
                     "diamond", "hands", "apes", "strong"}
    bearish_words = {"puts", "short", "bear", "sell", "crash", "dump", "overvalued",
                     "red", "loss", "down", "rip", "drill", "dead", "bag", "holding",
                     "fucked", "worthless", "scam"}

    bull_count = 0
    bear_count = 0
    total_score = 0
    for post in posts:
        text = (post.title + " " + post.selftext).lower()
        words = set(text.split())
        bull_count += len(words & bullish_words)
        bear_count += len(words & bearish_words)
        total_score += post.score

    total = bull_count + bear_count
    if total == 0:
        sentiment = Sentiment.NEUTRAL
        confidence = 0.2
    elif bull_count > bear_count * 1.5:
        sentiment = Sentiment.BULLISH
        confidence = min(0.8, bull_count / total)
    elif bear_count > bull_count * 1.5:
        sentiment = Sentiment.BEARISH
        confidence = min(0.8, bear_count / total)
    else:
        sentiment = Sentiment.MIXED
        confidence = 0.4

    # Detect meme hype
    meme_words = {"moon", "rocket", "apes", "yolo", "diamond", "hands", "tendies", "squeeze"}
    all_text = " ".join((p.title + " " + p.selftext).lower() for p in posts)
    meme_count = sum(1 for w in meme_words if w in all_text)
    is_meme = meme_count >= 3

    # Detect genuine DD
    dd_signals = {"revenue", "earnings", "p/e", "growth", "margin", "valuation",
                  "balance sheet", "cash flow", "dcf", "analysis"}
    dd_count = sum(1 for w in dd_signals if w in all_text)
    is_dd = dd_count >= 2

    return SentimentReport(
        ticker=ticker,
        sentiment=sentiment,
        confidence=round(confidence, 2),
        is_meme_hype=is_meme,
        is_genuine_dd=is_dd,
        key_themes=[],
        catalysts=[],
        post_count_analyzed=len(posts),
        summary=f"WSB mentions: {len(posts)} posts, "
                f"avg score {total_score // max(len(posts), 1)}. "
                f"Keyword sentiment: {sentiment.value} "
                f"({'mostly meme hype' if is_meme else 'some DD present' if is_dd else 'mixed discussion'}).",
    )


def run_analysis_local(job_id: str) -> AnalysisResult:
    """Run full analysis using only local quant tools (no Claude API needed).

    This does everything except AI sentiment analysis and AI-written theses.
    Uses keyword sentiment and rule-based scoring instead.
    """
    logger.info("Running LOCAL analysis (no Claude API)")
    result = AnalysisResult(job_id=job_id, status="running")

    # Step 1: Get trending tickers from WSB
    logger.info("Step 1: Fetching trending WSB tickers...")
    trending = get_trending_tickers(time_filter="day", limit=100)

    if not trending:
        result.status = "error"
        result.error = "Could not fetch trending tickers from Reddit"
        return result

    result.trending_tickers = trending

    # Filter to likely real tickers (basic heuristic: 2-5 chars, not obviously wrong)
    # We'll try to fetch data and skip any that fail
    top_tickers = trending[:8]
    logger.info(f"Top tickers: {[t.ticker for t in top_tickers]}")

    # Step 2: Analyze each ticker
    recommendations = []
    for rank, mention in enumerate(top_tickers, 1):
        ticker = mention.ticker
        logger.info(f"Step 2: Analyzing {ticker} (rank #{rank})...")

        try:
            # Fetch market data
            stock_data = get_stock_data(ticker, period="1y")
            if not stock_data.history:
                logger.warning(f"  Skipping {ticker}: no price data (probably not a real ticker)")
                continue

            financials = get_financial_statements(ticker)

            # Run all analyses
            fundamental = analyze_fundamentals(ticker, stock_data, financials)
            technical = analyze_technicals(ticker, stock_data)
            risk = analyze_risk(ticker, stock_data)

            # Basic sentiment from WSB posts
            time.sleep(1)  # be polite to Reddit
            posts = get_posts_for_ticker(ticker, limit=15)
            sentiment = _basic_sentiment_from_posts(ticker, posts)

            # Composite score: 35% fundamental, 25% technical, 20% risk, 20% sentiment
            sent_score = 50.0
            if sentiment.sentiment == Sentiment.BULLISH:
                sent_score = 70.0
            elif sentiment.sentiment == Sentiment.BEARISH:
                sent_score = 30.0
            elif sentiment.sentiment == Sentiment.MIXED:
                sent_score = 50.0

            # Penalize pure meme hype
            if sentiment.is_meme_hype and not sentiment.is_genuine_dd:
                sent_score -= 10

            composite = (
                fundamental.score * 0.35
                + technical.score * 0.25
                + risk.score * 0.20
                + sent_score * 0.20
            )
            composite = max(0, min(100, round(composite, 1)))

            signal = _compute_signal(composite)

            # Generate a basic thesis from the numbers
            thesis_parts = []
            if fundamental.trailing_pe:
                thesis_parts.append(f"P/E of {fundamental.trailing_pe:.1f}")
            if fundamental.revenue_growth_yoy is not None:
                direction = "growing" if fundamental.revenue_growth_yoy > 0 else "declining"
                thesis_parts.append(f"revenue {direction} {abs(fundamental.revenue_growth_yoy):.1%} YoY")
            if technical.trend_signal:
                thesis_parts.append(f"technical trend is {technical.trend_signal}")
            if risk.sharpe_ratio is not None:
                quality = "good" if risk.sharpe_ratio > 1 else "moderate" if risk.sharpe_ratio > 0.5 else "poor"
                thesis_parts.append(f"{quality} risk-adjusted returns (Sharpe {risk.sharpe_ratio:.2f})")

            thesis = f"{ticker}: " + ", ".join(thesis_parts) + "." if thesis_parts else f"{ticker}: Limited data available."

            # Bull / bear cases
            bull_parts = []
            bear_parts = []
            if fundamental.dcf_upside_pct and fundamental.dcf_upside_pct > 0:
                bull_parts.append(f"DCF suggests {fundamental.dcf_upside_pct:.0%} upside")
            if fundamental.revenue_growth_yoy and fundamental.revenue_growth_yoy > 0.1:
                bull_parts.append(f"strong revenue growth ({fundamental.revenue_growth_yoy:.1%})")
            if technical.trend_signal == "bullish":
                bull_parts.append("bullish technical trend")
            if sentiment.sentiment == Sentiment.BULLISH:
                bull_parts.append("strong WSB bullish sentiment")

            if fundamental.trailing_pe and fundamental.trailing_pe > 40:
                bear_parts.append(f"expensive valuation (P/E {fundamental.trailing_pe:.0f})")
            if fundamental.debt_to_equity and fundamental.debt_to_equity > 2:
                bear_parts.append(f"high debt (D/E {fundamental.debt_to_equity:.1f})")
            if technical.trend_signal == "bearish":
                bear_parts.append("bearish technical trend")
            if risk.volatility_annual and risk.volatility_annual > 0.5:
                bear_parts.append(f"very volatile ({risk.volatility_annual:.0%} annual)")
            if sentiment.is_meme_hype:
                bear_parts.append("WSB hype may be meme-driven")

            # Risk flags
            risk_flags = []
            if sentiment.is_meme_hype:
                risk_flags.append("Meme stock hype")
            if risk.volatility_annual and risk.volatility_annual > 0.5:
                risk_flags.append("High volatility")
            if fundamental.trailing_pe and fundamental.trailing_pe > 50:
                risk_flags.append("Extreme valuation")
            if fundamental.debt_to_equity and fundamental.debt_to_equity > 3:
                risk_flags.append("Heavy debt load")
            if risk.max_drawdown and risk.max_drawdown < -0.3:
                risk_flags.append(f"Large recent drawdown ({risk.max_drawdown:.0%})")

            rec = StockRecommendation(
                ticker=ticker,
                signal=signal,
                score=composite,
                investment_thesis=thesis,
                bull_case=". ".join(bull_parts) if bull_parts else "Limited bullish signals.",
                bear_case=". ".join(bear_parts) if bear_parts else "Limited bearish signals.",
                risk_flags=risk_flags,
                fundamental=fundamental,
                technical=technical,
                risk=risk,
                sentiment=sentiment,
                wsb_mention_rank=rank,
            )
            recommendations.append(rec)
            logger.info(f"  {ticker}: score={composite}, signal={signal.value}")

        except Exception as e:
            logger.warning(f"  Skipping {ticker}: {e}")
            continue

    # Sort by score
    recommendations.sort(key=lambda r: r.score, reverse=True)

    result.recommendations = recommendations
    result.market_summary = (
        f"Analyzed {len(recommendations)} WSB trending stocks using quantitative analysis. "
        f"Top mentions: {', '.join(t.ticker for t in trending[:5])}. "
        f"(Running in local mode — add Anthropic API credits for AI-powered sentiment analysis and investment theses.)"
    )
    result.status = "completed"
    result.completed_at = datetime.utcnow()
    return result


# ── Claude-powered analysis ──────────────────────────────────


def _execute_tool(tool_name: str, tool_input: dict) -> str:
    """Execute a tool call and return the result as a JSON string."""
    try:
        if tool_name == "get_wsb_trending":
            tickers = get_trending_tickers(
                time_filter=tool_input.get("time_filter", "day"),
                limit=tool_input.get("limit", 100),
            )
            return json.dumps(
                [t.model_dump() for t in tickers[:15]], default=str
            )

        elif tool_name == "get_financial_data":
            ticker = tool_input["ticker"]
            period = tool_input.get("period", "1y")
            data = get_stock_data(ticker, period)
            result = data.model_dump()
            result["history"] = result["history"][-20:]
            return json.dumps(result, default=str)

        elif tool_name == "run_fundamental_analysis":
            ticker = tool_input["ticker"]
            stock_data = get_stock_data(ticker)
            financials = get_financial_statements(ticker)
            report = analyze_fundamentals(ticker, stock_data, financials)
            return json.dumps(report.model_dump(), default=str)

        elif tool_name == "run_technical_analysis":
            ticker = tool_input["ticker"]
            stock_data = get_stock_data(ticker)
            report = analyze_technicals(ticker, stock_data)
            return json.dumps(report.model_dump(), default=str)

        elif tool_name == "run_risk_analysis":
            ticker = tool_input["ticker"]
            stock_data = get_stock_data(ticker)
            report = analyze_risk(ticker, stock_data)
            return json.dumps(report.model_dump(), default=str)

        elif tool_name == "analyze_wsb_sentiment":
            ticker = tool_input["ticker"]
            return _run_sentiment_analysis(ticker)

        else:
            return json.dumps({"error": f"Unknown tool: {tool_name}"})

    except Exception as e:
        logger.exception(f"Tool execution error: {tool_name}")
        return json.dumps({"error": str(e)})


def _run_sentiment_analysis(ticker: str) -> str:
    """Use a separate Claude call to analyze WSB sentiment for a ticker."""
    client = _get_client()

    posts = get_posts_for_ticker(ticker, limit=20)
    if not posts:
        return json.dumps(
            SentimentReport(
                ticker=ticker,
                sentiment=Sentiment.NEUTRAL,
                confidence=0.0,
                summary=f"No recent WSB posts found for {ticker}",
            ).model_dump()
        )

    posts_text = "\n\n---\n\n".join(
        f"**{p.title}** (score: {p.score}, comments: {p.num_comments})\n{p.selftext[:500]}"
        for p in posts
    )

    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=1024,
        system=SENTIMENT_SYSTEM_PROMPT.format(ticker=ticker),
        messages=[
            {
                "role": "user",
                "content": f"Analyze the sentiment of these {len(posts)} WSB posts about {ticker}:\n\n{posts_text}",
            }
        ],
    )

    response_text = response.content[0].text
    try:
        json_start = response_text.find("{")
        json_end = response_text.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            data = json.loads(response_text[json_start:json_end])
            report = SentimentReport(
                ticker=ticker,
                sentiment=Sentiment(data.get("sentiment", "neutral")),
                confidence=data.get("confidence", 0.5),
                is_meme_hype=data.get("is_meme_hype", False),
                is_genuine_dd=data.get("is_genuine_dd", False),
                key_themes=data.get("key_themes", []),
                catalysts=data.get("catalysts", []),
                post_count_analyzed=len(posts),
                summary=data.get("summary", ""),
            )
            return json.dumps(report.model_dump())
    except (json.JSONDecodeError, ValueError):
        pass

    return json.dumps(
        SentimentReport(
            ticker=ticker,
            sentiment=Sentiment.MIXED,
            confidence=0.3,
            post_count_analyzed=len(posts),
            summary=response_text[:300],
        ).model_dump()
    )


def run_analysis_claude(job_id: str) -> AnalysisResult:
    """Run the full Claude agent analysis loop."""
    client = _get_client()
    result = AnalysisResult(job_id=job_id, status="running")

    messages = [
        {
            "role": "user",
            "content": (
                "Analyze the current WallStreetBets trending stocks. "
                "Get the trending tickers, then for the top 5 most-mentioned ones, "
                "run fundamental, technical, risk, and sentiment analysis. "
                "Finally, synthesize everything into your ranked recommendations."
            ),
        }
    ]

    max_iterations = 30
    iteration = 0

    while iteration < max_iterations:
        iteration += 1
        logger.info(f"Agent iteration {iteration}")

        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=4096,
            system=ORCHESTRATOR_SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        if response.stop_reason == "tool_use":
            assistant_content = response.content
            tool_results = []

            for block in assistant_content:
                if block.type == "tool_use":
                    logger.info(f"  Tool call: {block.name}({json.dumps(block.input)[:100]})")
                    tool_result = _execute_tool(block.name, block.input)
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": tool_result,
                        }
                    )

            messages.append({"role": "assistant", "content": assistant_content})
            messages.append({"role": "user", "content": tool_results})

        elif response.stop_reason == "end_turn":
            final_text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    final_text += block.text

            result = _parse_final_response(job_id, final_text)
            result.status = "completed"
            result.completed_at = datetime.utcnow()
            return result

        else:
            logger.warning(f"Unexpected stop reason: {response.stop_reason}")
            break

    result.status = "error"
    result.error = "Agent exceeded maximum iterations"
    return result


def _parse_final_response(job_id: str, response_text: str) -> AnalysisResult:
    """Parse Claude's final JSON response into an AnalysisResult."""
    result = AnalysisResult(job_id=job_id)

    try:
        json_start = response_text.find("{")
        json_end = response_text.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            data = json.loads(response_text[json_start:json_end])

            result.market_summary = data.get("market_summary", "")

            for i, rec in enumerate(data.get("recommendations", [])):
                signal_map = {
                    "strong_buy": Signal.STRONG_BUY,
                    "buy": Signal.BUY,
                    "hold": Signal.HOLD,
                    "sell": Signal.SELL,
                    "strong_sell": Signal.STRONG_SELL,
                }
                recommendation = StockRecommendation(
                    ticker=rec.get("ticker", ""),
                    signal=signal_map.get(rec.get("signal", "hold"), Signal.HOLD),
                    score=rec.get("score", 50),
                    investment_thesis=rec.get("investment_thesis", ""),
                    bull_case=rec.get("bull_case", ""),
                    bear_case=rec.get("bear_case", ""),
                    risk_flags=rec.get("risk_flags", []),
                    wsb_mention_rank=rec.get("wsb_mention_rank", i + 1),
                )
                result.recommendations.append(recommendation)

    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Failed to parse agent response: {e}")
        result.market_summary = response_text[:500]

    return result


# ── Main entry point (auto-detects mode) ─────────────────────


def run_analysis(job_id: str) -> AnalysisResult:
    """Run analysis — uses Claude if API credits available, otherwise runs locally."""
    if _has_api_credits():
        logger.info("Claude API available — running full AI analysis")
        return run_analysis_claude(job_id)
    else:
        logger.info("Claude API unavailable — running local quantitative analysis")
        return run_analysis_local(job_id)
