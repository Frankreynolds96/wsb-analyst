"""Tool definitions for the Claude agent orchestrator."""

TOOLS = [
    {
        "name": "get_wsb_trending",
        "description": (
            "Get the most talked-about stock tickers on r/WallStreetBets right now. "
            "Returns tickers ranked by a weighted score of mention frequency, upvotes, "
            "and comment engagement. Each ticker includes sample posts."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "time_filter": {
                    "type": "string",
                    "enum": ["hour", "day", "week"],
                    "description": "Time filter for top posts. Default: day",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max posts to scan. Default: 100",
                },
            },
        },
    },
    {
        "name": "get_financial_data",
        "description": (
            "Fetch stock price history (1 year OHLCV) and company info for a ticker. "
            "Returns current price, market cap, sector, 52-week range, and full price history."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Stock ticker symbol (e.g. AAPL, TSLA, GME)",
                },
                "period": {
                    "type": "string",
                    "enum": ["3mo", "6mo", "1y", "2y"],
                    "description": "Price history period. Default: 1y",
                },
            },
            "required": ["ticker"],
        },
    },
    {
        "name": "run_fundamental_analysis",
        "description": (
            "Run fundamental analysis on a stock. Returns P/E ratios, revenue growth, "
            "earnings growth, debt-to-equity, free cash flow, profit margins, and a "
            "simple DCF fair value estimate with upside/downside percentage."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Stock ticker symbol",
                },
            },
            "required": ["ticker"],
        },
    },
    {
        "name": "run_technical_analysis",
        "description": (
            "Run technical analysis on a stock. Returns SMA (20/50/200), EMA (12/26), "
            "RSI, MACD with signal & histogram, Bollinger Bands, volume analysis, "
            "and an overall trend signal (bullish/bearish/neutral)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Stock ticker symbol",
                },
            },
            "required": ["ticker"],
        },
    },
    {
        "name": "run_risk_analysis",
        "description": (
            "Calculate risk metrics for a stock vs SPY benchmark. Returns beta, "
            "Sharpe ratio, Sortino ratio, max drawdown, annualized volatility, "
            "and Value at Risk (95% confidence, 1-day)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Stock ticker symbol",
                },
            },
            "required": ["ticker"],
        },
    },
    {
        "name": "analyze_wsb_sentiment",
        "description": (
            "Analyze the sentiment of recent WallStreetBets posts about a specific ticker. "
            "Uses AI to detect sarcasm, meme hype vs genuine DD, bullish/bearish signals, "
            "key themes, and catalysts. Returns a sentiment report with confidence score."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Stock ticker symbol to analyze sentiment for",
                },
            },
            "required": ["ticker"],
        },
    },
]
