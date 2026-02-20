from __future__ import annotations

from backend.models.schemas import FinancialStatements, FundamentalReport, StockData


def _safe_div(a: float | None, b: float | None) -> float | None:
    if a is None or b is None or b == 0:
        return None
    return a / b


def _simple_dcf(
    fcf: float | None,
    growth_rate: float = 0.10,
    discount_rate: float = 0.10,
    terminal_growth: float = 0.03,
    years: int = 5,
    shares_outstanding: float | None = None,
) -> float | None:
    """Simple DCF model: project FCF forward, discount back."""
    if fcf is None or fcf <= 0 or shares_outstanding is None or shares_outstanding <= 0:
        return None

    pv_fcfs = 0.0
    projected_fcf = fcf
    for year in range(1, years + 1):
        projected_fcf *= 1 + growth_rate
        pv_fcfs += projected_fcf / (1 + discount_rate) ** year

    # Terminal value
    terminal_fcf = projected_fcf * (1 + terminal_growth)
    terminal_value = terminal_fcf / (discount_rate - terminal_growth)
    pv_terminal = terminal_value / (1 + discount_rate) ** years

    enterprise_value = pv_fcfs + pv_terminal
    return round(enterprise_value / shares_outstanding, 2)


def analyze_fundamentals(
    ticker: str,
    stock_data: StockData,
    financials: FinancialStatements,
) -> FundamentalReport:
    """Run fundamental analysis and return a scored report."""
    info = stock_data.info

    # Revenue growth YoY
    revenue_growth = None
    if len(financials.revenue) >= 2 and financials.revenue[1] != 0:
        revenue_growth = round(
            (financials.revenue[0] - financials.revenue[1]) / abs(financials.revenue[1]),
            4,
        )

    # Earnings growth YoY
    earnings_growth = None
    if len(financials.net_income) >= 2 and financials.net_income[1] != 0:
        earnings_growth = round(
            (financials.net_income[0] - financials.net_income[1])
            / abs(financials.net_income[1]),
            4,
        )

    # Debt to equity
    debt_to_equity = _safe_div(financials.total_debt, financials.total_equity)
    if debt_to_equity is not None:
        debt_to_equity = round(debt_to_equity, 4)

    # DCF fair value estimate
    shares = None
    if info.market_cap and info.current_price and info.current_price > 0:
        shares = info.market_cap / info.current_price

    growth_for_dcf = max(min(revenue_growth or 0.05, 0.30), -0.10)
    dcf_value = _simple_dcf(
        fcf=financials.free_cash_flow,
        growth_rate=growth_for_dcf,
        shares_outstanding=shares,
    )

    dcf_upside = None
    if dcf_value and info.current_price and info.current_price > 0:
        dcf_upside = round((dcf_value - info.current_price) / info.current_price, 4)

    # Scoring (0-100) — higher is better
    score = 50.0
    if financials.trailing_pe is not None:
        if financials.trailing_pe < 15:
            score += 10
        elif financials.trailing_pe < 25:
            score += 5
        elif financials.trailing_pe > 50:
            score -= 10
    if revenue_growth is not None:
        if revenue_growth > 0.20:
            score += 10
        elif revenue_growth > 0.05:
            score += 5
        elif revenue_growth < 0:
            score -= 10
    if debt_to_equity is not None:
        if debt_to_equity < 0.5:
            score += 5
        elif debt_to_equity > 2.0:
            score -= 10
    if dcf_upside is not None:
        if dcf_upside > 0.30:
            score += 10
        elif dcf_upside > 0:
            score += 5
        elif dcf_upside < -0.30:
            score -= 10
    if financials.profit_margin is not None:
        if financials.profit_margin > 0.20:
            score += 5
        elif financials.profit_margin < 0:
            score -= 10

    score = max(0, min(100, score))

    # Summary
    parts = []
    if financials.trailing_pe:
        parts.append(f"P/E {financials.trailing_pe:.1f}")
    if revenue_growth is not None:
        parts.append(f"Rev growth {revenue_growth:+.1%}")
    if debt_to_equity is not None:
        parts.append(f"D/E {debt_to_equity:.2f}")
    if dcf_upside is not None:
        parts.append(f"DCF upside {dcf_upside:+.1%}")
    summary = f"{ticker}: " + ", ".join(parts) if parts else f"{ticker}: Limited data"

    return FundamentalReport(
        ticker=ticker,
        trailing_pe=financials.trailing_pe,
        forward_pe=financials.forward_pe,
        price_to_book=financials.price_to_book,
        revenue_growth_yoy=revenue_growth,
        earnings_growth_yoy=earnings_growth,
        debt_to_equity=debt_to_equity,
        free_cash_flow=financials.free_cash_flow,
        profit_margin=financials.profit_margin,
        operating_margin=financials.operating_margin,
        dcf_fair_value=dcf_value,
        current_price=info.current_price,
        dcf_upside_pct=dcf_upside,
        score=score,
        summary=summary,
    )
