import React from 'react'

export default function TrendingTickers({ tickers }) {
  if (!tickers?.length) return null

  return (
    <div className="card mb-6">
      <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
        Trending on WSB
      </h3>
      <div className="flex flex-wrap gap-2">
        {tickers.map(t => (
          <div
            key={t.ticker}
            className="bg-gray-800 border border-wsb-border rounded-lg px-3 py-2 text-center"
          >
            <div className="font-bold mono text-sm">{t.ticker}</div>
            <div className="text-xs text-gray-500">
              {t.mention_count} mentions
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
