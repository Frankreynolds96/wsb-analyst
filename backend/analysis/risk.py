from __future__ import annotations

import numpy as np
import pandas as pd
import yfinance as yf

from backend.models.schemas import RiskReport, StockData


def _get_returns(stock_data: StockData) -> np.ndarray:
    """Compute daily log returns from stock history."""
    prices = np.array([bar.close for bar in stock_data.history])
    if len(prices) < 2:
        return np.array([])
    return np.diff(np.log(prices))


def _get_benchmark_returns(benchmark: str, period: str = "1y") -> np.ndarray:
    """Fetch benchmark returns for beta calculation."""
    bench = yf.Ticker(benchmark)
    hist = bench.history(period=period)
    if hist.empty or len(hist) < 2:
        return np.array([])
    prices = hist["Close"].values
    return np.diff(np.log(prices))


def analyze_risk(
    ticker: str,
    stock_data: StockData,
    benchmark: str = "SPY",
) -> RiskReport:
    """Compute risk metrics and return a scored report."""
    returns = _get_returns(stock_data)

    if len(returns) < 20:
        return RiskReport(
            ticker=ticker,
            score=50.0,
            summary=f"{ticker}: Insufficient data for risk analysis",
        )

    # Volatility (annualized)
    daily_vol = float(np.std(returns))
    annual_vol = round(daily_vol * np.sqrt(252), 4)

    # Sharpe ratio (assuming risk-free rate ~5%)
    risk_free_daily = 0.05 / 252
    excess_returns = returns - risk_free_daily
    sharpe = None
    if daily_vol > 0:
        sharpe = round(float(np.mean(excess_returns) / np.std(excess_returns)) * np.sqrt(252), 4)

    # Sortino ratio (only penalizes downside volatility)
    downside_returns = returns[returns < 0]
    sortino = None
    if len(downside_returns) > 0:
        downside_vol = float(np.std(downside_returns))
        if downside_vol > 0:
            sortino = round(
                float(np.mean(excess_returns) / downside_vol) * np.sqrt(252), 4
            )

    # Max drawdown
    prices = np.array([bar.close for bar in stock_data.history])
    cummax = np.maximum.accumulate(prices)
    drawdowns = (prices - cummax) / cummax
    max_drawdown = round(float(np.min(drawdowns)), 4)

    # Value at Risk (95% confidence, 1-day, parametric)
    var_95 = round(float(np.percentile(returns, 5)), 4)

    # Beta (vs benchmark)
    beta = None
    bench_returns = _get_benchmark_returns(benchmark, period="1y")
    min_len = min(len(returns), len(bench_returns))
    if min_len >= 20:
        stock_r = returns[-min_len:]
        bench_r = bench_returns[-min_len:]
        cov = np.cov(stock_r, bench_r)
        if cov[1, 1] != 0:
            beta = round(float(cov[0, 1] / cov[1, 1]), 4)

    # Scoring (0-100) — lower risk = higher score
    score = 50.0
    if annual_vol < 0.20:
        score += 10
    elif annual_vol < 0.35:
        score += 5
    elif annual_vol > 0.60:
        score -= 15
    elif annual_vol > 0.45:
        score -= 10

    if sharpe is not None:
        if sharpe > 1.5:
            score += 15
        elif sharpe > 1.0:
            score += 10
        elif sharpe > 0.5:
            score += 5
        elif sharpe < 0:
            score -= 10

    if max_drawdown > -0.15:
        score += 5
    elif max_drawdown < -0.40:
        score -= 10

    if beta is not None:
        if beta < 0.8:
            score += 5
        elif beta > 1.5:
            score -= 10

    score = max(0, min(100, score))

    # Summary
    parts = [f"Vol {annual_vol:.1%}"]
    if sharpe is not None:
        parts.append(f"Sharpe {sharpe:.2f}")
    if beta is not None:
        parts.append(f"Beta {beta:.2f}")
    parts.append(f"Max DD {max_drawdown:.1%}")
    parts.append(f"VaR95 {var_95:.2%}")
    summary = f"{ticker}: " + ", ".join(parts)

    return RiskReport(
        ticker=ticker,
        beta=beta,
        sharpe_ratio=sharpe,
        sortino_ratio=sortino,
        max_drawdown=max_drawdown,
        volatility_annual=annual_vol,
        var_95_1day=var_95,
        score=score,
        summary=summary,
    )
