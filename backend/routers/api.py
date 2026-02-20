from __future__ import annotations

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api")


@router.get("/stock/{ticker}")
def api_stock_detail(ticker: str):
    """Get detailed analysis for a single stock.

    Heavy imports (pandas, numpy, yfinance, ta) are loaded lazily
    to keep cold starts fast on Vercel serverless.
    """
    from backend.analysis.fundamental import analyze_fundamentals
    from backend.analysis.risk import analyze_risk
    from backend.analysis.technical import analyze_technicals
    from backend.data.market import get_financial_statements, get_stock_data

    ticker = ticker.upper()
    try:
        stock_data = get_stock_data(ticker)
        financials = get_financial_statements(ticker)
        fundamental = analyze_fundamentals(ticker, stock_data, financials)
        technical = analyze_technicals(ticker, stock_data)
        risk = analyze_risk(ticker, stock_data)

        return {
            "ticker": ticker,
            "info": stock_data.info.model_dump(),
            "fundamental": fundamental.model_dump(),
            "technical": technical.model_dump(),
            "risk": risk.model_dump(),
            "price_history": [bar.model_dump() for bar in stock_data.history[-60:]],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed for {ticker}: {str(e)}")
