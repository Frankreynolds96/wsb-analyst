import React from 'react'
import RecommendationBadge from './RecommendationBadge'
import PriceChart from './PriceChart'

export default function AnalysisReport({ recommendation, onClose }) {
  const {
    ticker, signal, score, investment_thesis, bull_case, bear_case,
    risk_flags, fundamental, technical, risk, info, price_history,
  } = recommendation

  return (
    <div className="card">
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <div className="flex items-center gap-3">
            <h2 className="text-3xl font-bold mono">{ticker}</h2>
            <RecommendationBadge signal={signal} />
          </div>
          {info && (
            <p className="text-sm text-gray-400 mt-1">
              {info.name} &middot; {info.sector} &middot;{' '}
              {info.market_cap
                ? `$${(info.market_cap / 1e9).toFixed(1)}B`
                : ''}
            </p>
          )}
        </div>
        <button
          className="text-gray-500 hover:text-white text-2xl leading-none"
          onClick={onClose}
        >
          &times;
        </button>
      </div>

      {/* Price Chart */}
      {price_history?.length > 0 && (
        <div className="mb-6">
          <PriceChart data={price_history} />
        </div>
      )}

      {/* Score */}
      <div className="mb-6">
        <div className="flex items-center gap-4 mb-2">
          <span className="text-4xl font-bold mono">{score}</span>
          <span className="text-gray-500">/100</span>
        </div>
        <div className="h-3 bg-gray-700 rounded-full overflow-hidden">
          <div
            className="h-full rounded-full"
            style={{
              width: `${score}%`,
              backgroundColor: score >= 70 ? '#00c853' : score >= 40 ? '#ffd600' : '#ff1744',
            }}
          />
        </div>
      </div>

      {/* Investment Thesis */}
      <div className="mb-6">
        <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-2">
          Investment Thesis
        </h3>
        <p className="text-gray-300">{investment_thesis}</p>
      </div>

      {/* Bull / Bear Case */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <div className="bg-wsb-green/5 border border-wsb-green/20 rounded-lg p-4">
          <h4 className="text-wsb-green font-semibold text-sm mb-2">Bull Case</h4>
          <p className="text-sm text-gray-300">{bull_case}</p>
        </div>
        <div className="bg-wsb-red/5 border border-wsb-red/20 rounded-lg p-4">
          <h4 className="text-wsb-red font-semibold text-sm mb-2">Bear Case</h4>
          <p className="text-sm text-gray-300">{bear_case}</p>
        </div>
      </div>

      {/* Metrics Table */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <MetricsCard title="Fundamentals" data={fundamental} />
        <MetricsCard title="Technicals" data={technical} />
        <MetricsCard title="Risk" data={risk} />
      </div>

      {/* Risk Flags */}
      {risk_flags?.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-2">
            Risk Flags
          </h3>
          <div className="flex flex-wrap gap-2">
            {risk_flags.map((flag, i) => (
              <span
                key={i}
                className="text-sm bg-wsb-red/10 text-wsb-red border border-wsb-red/20 rounded-lg px-3 py-1"
              >
                {flag}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function MetricsCard({ title, data }) {
  if (!data) return null

  const metrics = []
  if (title === 'Fundamentals') {
    if (data.trailing_pe != null) metrics.push(['P/E', data.trailing_pe.toFixed(1)])
    if (data.revenue_growth_yoy != null) metrics.push(['Rev Growth', (data.revenue_growth_yoy * 100).toFixed(1) + '%'])
    if (data.debt_to_equity != null) metrics.push(['D/E', data.debt_to_equity.toFixed(2)])
    if (data.profit_margin != null) metrics.push(['Margin', (data.profit_margin * 100).toFixed(1) + '%'])
    if (data.dcf_upside_pct != null) metrics.push(['DCF Upside', (data.dcf_upside_pct * 100).toFixed(1) + '%'])
  } else if (title === 'Technicals') {
    if (data.rsi_14 != null) metrics.push(['RSI', data.rsi_14.toFixed(1)])
    if (data.trend_signal) metrics.push(['Trend', data.trend_signal])
    if (data.macd_histogram != null) metrics.push(['MACD Hist', data.macd_histogram.toFixed(4)])
    if (data.volume_ratio != null) metrics.push(['Vol Ratio', data.volume_ratio.toFixed(1) + 'x'])
  } else if (title === 'Risk') {
    if (data.beta != null) metrics.push(['Beta', data.beta.toFixed(2)])
    if (data.sharpe_ratio != null) metrics.push(['Sharpe', data.sharpe_ratio.toFixed(2)])
    if (data.volatility_annual != null) metrics.push(['Volatility', (data.volatility_annual * 100).toFixed(1) + '%'])
    if (data.max_drawdown != null) metrics.push(['Max DD', (data.max_drawdown * 100).toFixed(1) + '%'])
    if (data.var_95_1day != null) metrics.push(['VaR 95%', (data.var_95_1day * 100).toFixed(2) + '%'])
  }

  const scoreColor = data.score >= 70 ? 'text-wsb-green' : data.score >= 40 ? 'text-wsb-gold' : 'text-wsb-red'

  return (
    <div className="bg-gray-800/50 border border-wsb-border rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-semibold text-gray-400 uppercase">{title}</h4>
        <span className={`mono font-bold ${scoreColor}`}>{data.score?.toFixed(0)}</span>
      </div>
      <div className="space-y-2">
        {metrics.map(([label, value]) => (
          <div key={label} className="flex items-center justify-between text-sm">
            <span className="text-gray-500">{label}</span>
            <span className="mono text-gray-300">{value}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
