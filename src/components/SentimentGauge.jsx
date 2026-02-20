import React from 'react'

const SENTIMENT_COLORS = {
  bullish: { bg: 'bg-wsb-green/10', text: 'text-wsb-green', label: 'Bullish' },
  bearish: { bg: 'bg-wsb-red/10', text: 'text-wsb-red', label: 'Bearish' },
  mixed: { bg: 'bg-wsb-gold/10', text: 'text-wsb-gold', label: 'Mixed' },
  neutral: { bg: 'bg-gray-700/50', text: 'text-gray-400', label: 'Neutral' },
}

export default function SentimentGauge({ sentiment }) {
  if (!sentiment) return null

  const s = sentiment.sentiment || 'neutral'
  const config = SENTIMENT_COLORS[s] || SENTIMENT_COLORS.neutral
  const confidence = Math.round((sentiment.confidence || 0) * 100)

  return (
    <div className={`${config.bg} rounded-lg px-3 py-2`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className={`text-sm font-semibold ${config.text}`}>
            WSB: {config.label}
          </span>
          {sentiment.is_meme_hype && (
            <span className="text-xs bg-wsb-gold/20 text-wsb-gold rounded px-1.5 py-0.5">
              MEME
            </span>
          )}
          {sentiment.is_genuine_dd && (
            <span className="text-xs bg-blue-500/20 text-blue-400 rounded px-1.5 py-0.5">
              DD
            </span>
          )}
        </div>
        <span className="text-xs text-gray-500 mono">{confidence}% conf</span>
      </div>
      {sentiment.summary && (
        <p className="text-xs text-gray-400 mt-1 line-clamp-2">{sentiment.summary}</p>
      )}
    </div>
  )
}
