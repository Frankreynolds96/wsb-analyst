import React, { useState } from 'react'
import StockCard from './StockCard'
import AnalysisReport from './AnalysisReport'

export default function Dashboard({ analysis }) {
  const [selectedTicker, setSelectedTicker] = useState(null)
  const recs = analysis.recommendations || []

  const selected = recs.find(r => r.ticker === selectedTicker)

  // Sort by score descending
  const sorted = [...recs].sort((a, b) => b.score - a.score)

  return (
    <div>
      {/* Market Summary */}
      {analysis.market_summary && (
        <div className="card mb-6">
          <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-2">
            Market Summary
          </h3>
          <p className="text-gray-300">{analysis.market_summary}</p>
        </div>
      )}

      {/* Stock Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
        {sorted.map(rec => (
          <StockCard
            key={rec.ticker}
            recommendation={rec}
            isSelected={rec.ticker === selectedTicker}
            onClick={() => setSelectedTicker(
              rec.ticker === selectedTicker ? null : rec.ticker
            )}
          />
        ))}
      </div>

      {/* Detailed Report */}
      {selected && (
        <AnalysisReport
          recommendation={selected}
          onClose={() => setSelectedTicker(null)}
        />
      )}

      {recs.length === 0 && (
        <p className="text-center text-gray-500 py-10">
          No recommendations yet. Run an analysis to get started.
        </p>
      )}
    </div>
  )
}
