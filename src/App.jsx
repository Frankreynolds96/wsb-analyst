import React, { useState, useCallback } from 'react'
import Dashboard from './components/Dashboard'
import { fetchTrending, fetchStockDetail } from './api'

export default function App() {
  const [trending, setTrending] = useState([])
  const [stocks, setStocks] = useState({})
  const [loading, setLoading] = useState(false)
  const [progress, setProgress] = useState('')
  const [error, setError] = useState(null)

  const runAnalysis = useCallback(async () => {
    setLoading(true)
    setError(null)
    setStocks({})
    setTrending([])

    try {
      // Step 1: Fetch trending tickers from WSB
      setProgress('Scanning r/WallStreetBets for trending stocks...')
      const data = await fetchTrending('day')
      const tickers = (data.tickers || []).slice(0, 8)
      setTrending(tickers)

      if (tickers.length === 0) {
        setError('No trending tickers found. Reddit may be rate-limiting — try again in a minute.')
        setLoading(false)
        return
      }

      // Step 2: Analyze each ticker one-by-one (cards appear progressively)
      for (let i = 0; i < tickers.length; i++) {
        const ticker = tickers[i].ticker
        setProgress(`Analyzing ${ticker}... (${i + 1}/${tickers.length})`)

        try {
          const detail = await fetchStockDetail(ticker)

          // Build a recommendation from the stock detail
          const f = detail.fundamental || {}
          const t = detail.technical || {}
          const r = detail.risk || {}

          // Composite score
          const composite = Math.round(
            (f.score || 50) * 0.35 +
            (t.score || 50) * 0.25 +
            (r.score || 50) * 0.20 +
            50 * 0.20
          )

          // Signal from score
          let signal = 'hold'
          if (composite >= 75) signal = 'strong_buy'
          else if (composite >= 60) signal = 'buy'
          else if (composite <= 25) signal = 'strong_sell'
          else if (composite <= 40) signal = 'sell'

          // Build thesis from numbers
          const parts = []
          if (f.trailing_pe) parts.push(`P/E ${f.trailing_pe.toFixed(1)}`)
          if (f.revenue_growth_yoy != null) {
            const dir = f.revenue_growth_yoy > 0 ? 'growing' : 'declining'
            parts.push(`revenue ${dir} ${Math.abs(f.revenue_growth_yoy * 100).toFixed(1)}% YoY`)
          }
          if (t.trend_signal) parts.push(`${t.trend_signal} trend`)
          if (r.sharpe_ratio != null) parts.push(`Sharpe ${r.sharpe_ratio.toFixed(2)}`)
          const thesis = parts.length > 0
            ? `${ticker}: ${parts.join(', ')}.`
            : `${ticker}: Limited data available.`

          // Risk flags
          const flags = []
          if (f.trailing_pe && f.trailing_pe > 50) flags.push('Extreme valuation')
          if (f.debt_to_equity && f.debt_to_equity > 3) flags.push('Heavy debt')
          if (r.volatility_annual && r.volatility_annual > 0.5) flags.push('High volatility')
          if (r.max_drawdown && r.max_drawdown < -0.3) flags.push(`${(r.max_drawdown * 100).toFixed(0)}% max drawdown`)

          // Bull/bear
          const bull = []
          const bear = []
          if (f.dcf_upside_pct && f.dcf_upside_pct > 0) bull.push(`DCF suggests ${(f.dcf_upside_pct * 100).toFixed(0)}% upside`)
          if (f.revenue_growth_yoy && f.revenue_growth_yoy > 0.1) bull.push('Strong revenue growth')
          if (t.trend_signal === 'bullish') bull.push('Bullish technicals')
          if (f.trailing_pe && f.trailing_pe > 40) bear.push(`Expensive (P/E ${f.trailing_pe.toFixed(0)})`)
          if (t.trend_signal === 'bearish') bear.push('Bearish technicals')
          if (r.volatility_annual && r.volatility_annual > 0.5) bear.push('Very volatile')

          const rec = {
            ticker,
            signal,
            score: composite,
            investment_thesis: thesis,
            bull_case: bull.join('. ') || 'Limited bullish signals.',
            bear_case: bear.join('. ') || 'Limited bearish signals.',
            risk_flags: flags,
            fundamental: f,
            technical: t,
            risk: r,
            wsb_mention_rank: i + 1,
            info: detail.info,
            price_history: detail.price_history,
          }

          setStocks(prev => ({ ...prev, [ticker]: rec }))
        } catch (e) {
          console.warn(`Skipping ${ticker}:`, e.message)
        }
      }

      setProgress('')
      setLoading(false)
    } catch (e) {
      setError(e.message)
      setLoading(false)
    }
  }, [])

  const recommendations = Object.values(stocks).sort((a, b) => b.score - a.score)
  const hasResults = recommendations.length > 0

  return (
    <div className="min-h-screen">
      <header className="border-b border-wsb-border px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">
              <span className="text-wsb-gold">WSB</span> Stock Analyst
            </h1>
            <p className="text-sm text-gray-400 mt-1">
              AI-powered analysis of r/WallStreetBets trending stocks
            </p>
          </div>
          <button
            className="btn-primary flex items-center gap-2"
            onClick={runAnalysis}
            disabled={loading}
          >
            {loading ? (
              <>
                <Spinner /> Analyzing...
              </>
            ) : (
              'Run Analysis'
            )}
          </button>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {error && (
          <div className="bg-wsb-red/10 border border-wsb-red/30 rounded-lg p-4 mb-6 text-wsb-red">
            {error}
          </div>
        )}

        {loading && progress && (
          <div className="card mb-6 flex items-center gap-3">
            <Spinner />
            <span className="text-gray-300">{progress}</span>
          </div>
        )}

        {trending.length > 0 && (
          <div className="card mb-6">
            <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
              Trending on r/WallStreetBets
            </h3>
            <div className="flex flex-wrap gap-2">
              {trending.map(t => (
                <div
                  key={t.ticker}
                  className={`border rounded-lg px-3 py-2 text-center ${
                    stocks[t.ticker]
                      ? 'bg-gray-800 border-wsb-border'
                      : 'bg-gray-900 border-gray-700 animate-pulse'
                  }`}
                >
                  <div className="font-bold mono text-sm">{t.ticker}</div>
                  <div className="text-xs text-gray-500">
                    {t.mention_count} mention{t.mention_count !== 1 ? 's' : ''}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {hasResults ? (
          <Dashboard analysis={{ recommendations, market_summary: '' }} />
        ) : !loading ? (
          <EmptyState onRun={runAnalysis} />
        ) : null}
      </main>
    </div>
  )
}

function Spinner() {
  return (
    <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
  )
}

function EmptyState({ onRun }) {
  return (
    <div className="text-center py-20">
      <div className="text-6xl mb-4">📊</div>
      <h2 className="text-xl font-semibold mb-2">No Analysis Yet</h2>
      <p className="text-gray-400 mb-6 max-w-md mx-auto">
        Click "Run Analysis" to scan r/WallStreetBets for trending stocks
        and run full quantitative analysis on each one.
      </p>
      <button className="btn-primary" onClick={onRun}>
        Run Your First Analysis
      </button>
    </div>
  )
}
