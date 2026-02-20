from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


# ── Reddit / WSB ──────────────────────────────────────────────


class RedditPost(BaseModel):
    post_id: str
    title: str
    selftext: str = ""
    score: int = 0
    num_comments: int = 0
    upvote_ratio: float = 0.0
    created_utc: float = 0.0
    url: str = ""
    flair: Optional[str] = None


class TickerMention(BaseModel):
    ticker: str
    mention_count: int = 0
    total_score: int = 0
    total_comments: int = 0
    weighted_score: float = 0.0
    sample_posts: List[RedditPost] = Field(default_factory=list)


# ── Market Data ───────────────────────────────────────────────


class OHLCVBar(BaseModel):
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int


class StockInfo(BaseModel):
    ticker: str
    name: str = ""
    sector: str = ""
    industry: str = ""
    market_cap: Optional[float] = None
    current_price: Optional[float] = None
    fifty_two_week_high: Optional[float] = None
    fifty_two_week_low: Optional[float] = None


class FinancialStatements(BaseModel):
    ticker: str
    revenue: List[float] = Field(default_factory=list)
    net_income: List[float] = Field(default_factory=list)
    total_debt: Optional[float] = None
    total_equity: Optional[float] = None
    free_cash_flow: Optional[float] = None
    earnings_per_share: Optional[float] = None
    forward_eps: Optional[float] = None
    trailing_pe: Optional[float] = None
    forward_pe: Optional[float] = None
    price_to_book: Optional[float] = None
    profit_margin: Optional[float] = None
    operating_margin: Optional[float] = None


class StockData(BaseModel):
    info: StockInfo
    history: List[OHLCVBar] = Field(default_factory=list)
    financials: Optional[FinancialStatements] = None


# ── Analysis Reports ──────────────────────────────────────────


class FundamentalReport(BaseModel):
    ticker: str
    trailing_pe: Optional[float] = None
    forward_pe: Optional[float] = None
    price_to_book: Optional[float] = None
    revenue_growth_yoy: Optional[float] = None
    earnings_growth_yoy: Optional[float] = None
    debt_to_equity: Optional[float] = None
    free_cash_flow: Optional[float] = None
    profit_margin: Optional[float] = None
    operating_margin: Optional[float] = None
    dcf_fair_value: Optional[float] = None
    current_price: Optional[float] = None
    dcf_upside_pct: Optional[float] = None
    score: float = 0.0
    summary: str = ""


class TechnicalReport(BaseModel):
    ticker: str
    sma_20: Optional[float] = None
    sma_50: Optional[float] = None
    sma_200: Optional[float] = None
    ema_12: Optional[float] = None
    ema_26: Optional[float] = None
    rsi_14: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_histogram: Optional[float] = None
    bollinger_upper: Optional[float] = None
    bollinger_lower: Optional[float] = None
    bollinger_mid: Optional[float] = None
    avg_volume_20d: Optional[float] = None
    current_volume: Optional[float] = None
    volume_ratio: Optional[float] = None
    current_price: Optional[float] = None
    trend_signal: str = ""
    score: float = 0.0
    summary: str = ""


class RiskReport(BaseModel):
    ticker: str
    beta: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    sortino_ratio: Optional[float] = None
    max_drawdown: Optional[float] = None
    volatility_annual: Optional[float] = None
    var_95_1day: Optional[float] = None
    score: float = 0.0
    summary: str = ""


class Sentiment(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    MIXED = "mixed"
    NEUTRAL = "neutral"


class SentimentReport(BaseModel):
    ticker: str
    sentiment: Sentiment = Sentiment.NEUTRAL
    confidence: float = 0.0
    is_meme_hype: bool = False
    is_genuine_dd: bool = False
    key_themes: List[str] = Field(default_factory=list)
    catalysts: List[str] = Field(default_factory=list)
    post_count_analyzed: int = 0
    summary: str = ""


# ── Recommendation ────────────────────────────────────────────


class Signal(str, Enum):
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    HOLD = "hold"
    SELL = "sell"
    STRONG_SELL = "strong_sell"


class StockRecommendation(BaseModel):
    ticker: str
    signal: Signal = Signal.HOLD
    score: float = 50.0  # 0-100
    investment_thesis: str = ""
    bull_case: str = ""
    bear_case: str = ""
    risk_flags: List[str] = Field(default_factory=list)
    fundamental: Optional[FundamentalReport] = None
    technical: Optional[TechnicalReport] = None
    risk: Optional[RiskReport] = None
    sentiment: Optional[SentimentReport] = None
    wsb_mention_rank: int = 0


class AnalysisResult(BaseModel):
    job_id: str = ""
    status: str = "pending"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    trending_tickers: List[TickerMention] = Field(default_factory=list)
    recommendations: List[StockRecommendation] = Field(default_factory=list)
    market_summary: str = ""
    error: Optional[str] = None
