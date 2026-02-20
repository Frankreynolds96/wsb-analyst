from __future__ import annotations

import yfinance as yf

from backend.models.schemas import FinancialStatements, OHLCVBar, StockData, StockInfo


def get_stock_data(ticker: str, period: str = "1y") -> StockData:
    """Fetch OHLCV history and company info from yfinance."""
    stock = yf.Ticker(ticker)
    info = stock.info or {}

    stock_info = StockInfo(
        ticker=ticker,
        name=info.get("longName", info.get("shortName", ticker)),
        sector=info.get("sector", ""),
        industry=info.get("industry", ""),
        market_cap=info.get("marketCap"),
        current_price=info.get("currentPrice", info.get("regularMarketPrice")),
        fifty_two_week_high=info.get("fiftyTwoWeekHigh"),
        fifty_two_week_low=info.get("fiftyTwoWeekLow"),
    )

    # Fetch price history
    hist = stock.history(period=period)
    history = []
    for date, row in hist.iterrows():
        history.append(
            OHLCVBar(
                date=date.strftime("%Y-%m-%d"),
                open=round(row["Open"], 2),
                high=round(row["High"], 2),
                low=round(row["Low"], 2),
                close=round(row["Close"], 2),
                volume=int(row["Volume"]),
            )
        )

    return StockData(info=stock_info, history=history)


def get_financial_statements(ticker: str) -> FinancialStatements:
    """Fetch financial statement data from yfinance."""
    stock = yf.Ticker(ticker)
    info = stock.info or {}

    # Revenue & net income from income statement
    revenue_list = []
    net_income_list = []
    try:
        income = stock.financials
        if income is not None and not income.empty:
            if "Total Revenue" in income.index:
                revenue_list = [
                    float(v) for v in income.loc["Total Revenue"].dropna().values
                ]
            if "Net Income" in income.index:
                net_income_list = [
                    float(v) for v in income.loc["Net Income"].dropna().values
                ]
    except Exception:
        pass

    # Free cash flow
    fcf = None
    try:
        cf = stock.cashflow
        if cf is not None and not cf.empty and "Free Cash Flow" in cf.index:
            vals = cf.loc["Free Cash Flow"].dropna().values
            if len(vals) > 0:
                fcf = float(vals[0])
    except Exception:
        pass

    # Debt & equity from balance sheet
    total_debt = None
    total_equity = None
    try:
        bs = stock.balance_sheet
        if bs is not None and not bs.empty:
            if "Total Debt" in bs.index:
                vals = bs.loc["Total Debt"].dropna().values
                if len(vals) > 0:
                    total_debt = float(vals[0])
            if "Stockholders Equity" in bs.index:
                vals = bs.loc["Stockholders Equity"].dropna().values
                if len(vals) > 0:
                    total_equity = float(vals[0])
    except Exception:
        pass

    return FinancialStatements(
        ticker=ticker,
        revenue=revenue_list,
        net_income=net_income_list,
        total_debt=total_debt,
        total_equity=total_equity,
        free_cash_flow=fcf,
        earnings_per_share=info.get("trailingEps"),
        forward_eps=info.get("forwardEps"),
        trailing_pe=info.get("trailingPE"),
        forward_pe=info.get("forwardPE"),
        price_to_book=info.get("priceToBook"),
        profit_margin=info.get("profitMargins"),
        operating_margin=info.get("operatingMargins"),
    )
