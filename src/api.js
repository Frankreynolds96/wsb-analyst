const BASE = '/api'

export async function fetchTrending(timeFilter = 'day') {
  const res = await fetch(`${BASE}/trending?time_filter=${timeFilter}`)
  if (!res.ok) throw new Error('Failed to fetch trending tickers from Reddit')
  return res.json()
}

export async function fetchStockDetail(ticker) {
  const res = await fetch(`${BASE}/stock/${ticker}`)
  if (!res.ok) throw new Error(`Failed to analyze ${ticker}`)
  return res.json()
}
