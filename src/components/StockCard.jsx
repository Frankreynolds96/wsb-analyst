import React from 'react'
import RecommendationBadge from './RecommendationBadge'
import SentimentGauge from './SentimentGauge'

export default function StockCard({ recommendation, isSelected, onClick }) {
  const { ticker, signal, score, investment_thesis, risk_flags, wsb_mention_rank, sentiment } = recommendation

  return (
    <div
      className={`card cursor-pointer transition-all hover:border-blue-500/50 ${
        isSelected ? 'border-blue-500 ring-1 ring-blue-500/30' : ''
      }`}
      onClick={onClick}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="text-xl font-bold mono">{ticker}</h3>
          <span className="text-xs text-gray-500">
            WSB rank #{wsb_mention_rank}
          </span>
        </div>
        <RecommendationBadge signal={signal} />
      </div>

      {/* Score Bar */}
      <div className="mb-3">
        <div className="flex items-center justify-between text-xs text-gray-400 mb-1">
          <span>Score</span>
          <span className="mono font-semibold text-white">{score}/100</span>
        </div>
        <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all"
            style={{
              width: `${score}%`,
              backgroundColor: score >= 70 ? '#00c853' : score >= 40 ? '#ffd600' : '#ff1744',
            }}
          />
        </div>
      </div>

      {/* Thesis snippet */}
      <p className="text-sm text-gray-400 line-clamp-2 mb-3">
        {investment_thesis || 'Click to see full analysis'}
      </p>

      {/* Sentiment */}
      {sentiment && (
        <SentimentGauge sentiment={sentiment} />
      )}

      {/* Risk flags */}
      {risk_flags?.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-3">
          {risk_flags.slice(0, 3).map((flag, i) => (
            <span
              key={i}
              className="text-xs bg-wsb-red/10 text-wsb-red/80 border border-wsb-red/20 rounded px-2 py-0.5"
            >
              {flag}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}
