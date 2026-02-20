import React from 'react'

const SIGNAL_CONFIG = {
  strong_buy: { label: 'STRONG BUY', className: 'badge-buy font-bold' },
  buy: { label: 'BUY', className: 'badge-buy' },
  hold: { label: 'HOLD', className: 'badge-hold' },
  sell: { label: 'SELL', className: 'badge-sell' },
  strong_sell: { label: 'STRONG SELL', className: 'badge-sell font-bold' },
}

export default function RecommendationBadge({ signal }) {
  const config = SIGNAL_CONFIG[signal] || SIGNAL_CONFIG.hold
  return <span className={config.className}>{config.label}</span>
}
