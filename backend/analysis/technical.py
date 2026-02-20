from __future__ import annotations

import numpy as np
import pandas as pd
import ta

from backend.models.schemas import StockData, TechnicalReport


def _to_dataframe(stock_data: StockData) -> pd.DataFrame:
    """Convert StockData history to a pandas DataFrame."""
    rows = [
        {
            "date": bar.date,
            "open": bar.open,
            "high": bar.high,
            "low": bar.low,
            "close": bar.close,
            "volume": bar.volume,
        }
        for bar in stock_data.history
    ]
    df = pd.DataFrame(rows)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date").sort_index()
    return df


def analyze_technicals(ticker: str, stock_data: StockData) -> TechnicalReport:
    """Compute technical indicators and return a scored report."""
    df = _to_dataframe(stock_data)

    if df.empty or len(df) < 20:
        return TechnicalReport(
            ticker=ticker,
            score=50.0,
            summary=f"{ticker}: Insufficient price history for technical analysis",
        )

    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]
    current_price = float(close.iloc[-1])

    # Moving Averages
    sma_20 = float(close.rolling(20).mean().iloc[-1]) if len(df) >= 20 else None
    sma_50 = float(close.rolling(50).mean().iloc[-1]) if len(df) >= 50 else None
    sma_200 = float(close.rolling(200).mean().iloc[-1]) if len(df) >= 200 else None
    ema_12 = float(close.ewm(span=12).mean().iloc[-1])
    ema_26 = float(close.ewm(span=26).mean().iloc[-1]) if len(df) >= 26 else None

    # RSI
    rsi_indicator = ta.momentum.RSIIndicator(close, window=14)
    rsi_series = rsi_indicator.rsi()
    rsi_14 = float(rsi_series.iloc[-1]) if not rsi_series.empty else None

    # MACD
    macd_indicator = ta.trend.MACD(close)
    macd_val = float(macd_indicator.macd().iloc[-1])
    macd_signal = float(macd_indicator.macd_signal().iloc[-1])
    macd_hist = float(macd_indicator.macd_diff().iloc[-1])

    # Bollinger Bands
    bb = ta.volatility.BollingerBands(close, window=20, window_dev=2)
    bb_upper = float(bb.bollinger_hband().iloc[-1])
    bb_lower = float(bb.bollinger_lband().iloc[-1])
    bb_mid = float(bb.bollinger_mavg().iloc[-1])

    # Volume
    avg_volume_20d = float(volume.rolling(20).mean().iloc[-1]) if len(df) >= 20 else None
    current_volume = float(volume.iloc[-1])
    vol_ratio = current_volume / avg_volume_20d if avg_volume_20d and avg_volume_20d > 0 else None

    # Trend determination
    signals = []
    if sma_50 and sma_200:
        if sma_50 > sma_200:
            signals.append("golden_cross")
        else:
            signals.append("death_cross")
    if rsi_14 is not None:
        if rsi_14 > 70:
            signals.append("overbought")
        elif rsi_14 < 30:
            signals.append("oversold")
    if macd_hist > 0:
        signals.append("macd_bullish")
    else:
        signals.append("macd_bearish")
    if current_price > bb_upper:
        signals.append("above_upper_bb")
    elif current_price < bb_lower:
        signals.append("below_lower_bb")

    bullish_count = sum(
        1
        for s in signals
        if s in ("golden_cross", "oversold", "macd_bullish", "below_lower_bb")
    )
    bearish_count = sum(
        1
        for s in signals
        if s in ("death_cross", "overbought", "macd_bearish", "above_upper_bb")
    )

    if bullish_count > bearish_count:
        trend_signal = "bullish"
    elif bearish_count > bullish_count:
        trend_signal = "bearish"
    else:
        trend_signal = "neutral"

    # Scoring
    score = 50.0
    if sma_20 and current_price > sma_20:
        score += 5
    if sma_50 and current_price > sma_50:
        score += 5
    if sma_200 and current_price > sma_200:
        score += 5
    if rsi_14 is not None:
        if 30 < rsi_14 < 50:
            score += 5  # potential upswing
        elif rsi_14 > 70:
            score -= 10  # overbought
        elif rsi_14 < 30:
            score += 5  # oversold bounce potential
    if macd_hist > 0:
        score += 5
    else:
        score -= 5
    if "golden_cross" in signals:
        score += 10
    elif "death_cross" in signals:
        score -= 10
    if vol_ratio and vol_ratio > 2.0:
        score += 5  # unusual volume

    score = max(0, min(100, score))

    # Summary
    parts = [f"Trend: {trend_signal}"]
    if rsi_14:
        parts.append(f"RSI {rsi_14:.1f}")
    parts.append(f"MACD {'bullish' if macd_hist > 0 else 'bearish'}")
    if vol_ratio:
        parts.append(f"Vol ratio {vol_ratio:.1f}x")
    summary = f"{ticker}: " + ", ".join(parts)

    return TechnicalReport(
        ticker=ticker,
        sma_20=round(sma_20, 2) if sma_20 else None,
        sma_50=round(sma_50, 2) if sma_50 else None,
        sma_200=round(sma_200, 2) if sma_200 else None,
        ema_12=round(ema_12, 2),
        ema_26=round(ema_26, 2) if ema_26 else None,
        rsi_14=round(rsi_14, 2) if rsi_14 else None,
        macd=round(macd_val, 4),
        macd_signal=round(macd_signal, 4),
        macd_histogram=round(macd_hist, 4),
        bollinger_upper=round(bb_upper, 2),
        bollinger_lower=round(bb_lower, 2),
        bollinger_mid=round(bb_mid, 2),
        avg_volume_20d=round(avg_volume_20d, 0) if avg_volume_20d else None,
        current_volume=current_volume,
        volume_ratio=round(vol_ratio, 2) if vol_ratio else None,
        current_price=current_price,
        trend_signal=trend_signal,
        score=score,
        summary=summary,
    )
