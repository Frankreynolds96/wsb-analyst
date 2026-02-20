const BASE = '/api'

async function fetchWithTimeout(url, timeoutMs = 15000) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)
  try {
    const res = await fetch(url, { signal: controller.signal })
    clearTimeout(timer)
    return res
  } catch (e) {
    clearTimeout(timer)
    if (e.name === 'AbortError') {
      throw new Error('Request timed out — the server may be starting up. Try again.')
    }
    throw e
  }
}

export async function fetchTrending(timeFilter = 'day') {
  const res = await fetchWithTimeout(`${BASE}/trending?time_filter=${timeFilter}`, 15000)
  if (!res.ok) throw new Error('Failed to fetch trending tickers from Reddit')
  return res.json()
}

export async function fetchStockDetail(ticker) {
  const res = await fetchWithTimeout(`${BASE}/stock/${ticker}`, 15000)
  if (!res.ok) throw new Error(`Failed to analyze ${ticker}`)
  return res.json()
}
