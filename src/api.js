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

// ── Reddit scraping (runs in the browser, not on Vercel) ──

// Common words that look like tickers but aren't
const FALSE_POSITIVES = new Set([
  "I", "A", "AM", "AN", "AT", "BE", "BY", "DO", "GO", "IF", "IN", "IS",
  "IT", "ME", "MY", "NO", "OF", "OK", "ON", "OR", "SO", "TO", "UP", "US",
  "WE", "CEO", "CFO", "CTO", "COO", "IPO", "ETF", "SEC", "FDA", "FED",
  "GDP", "ATH", "DD", "DFV", "EPS", "EOD", "ERR", "EST", "FOR", "FYI",
  "GG", "HQ", "IMO", "LOL", "NYC", "OTC", "PDT", "PE", "PM", "PT",
  "RH", "SP", "TD", "UK", "USA", "WSB", "YOLO", "FOMO", "HODL", "MOON",
  "APE", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC",
  "JAN", "FEB", "MAR", "MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN",
  "THE", "AND", "BUT", "NOT", "ALL", "ANY", "ARE", "CAN", "DAY", "DID",
  "GET", "GOT", "HAS", "HAD", "HER", "HIM", "HIS", "HOW", "ITS", "LET",
  "MAD", "MAN", "MEN", "NEW", "NOW", "OLD", "ONE", "OUR", "OUT", "OWN",
  "PUT", "RAN", "RED", "RUN", "SAW", "SAY", "SHE", "THE", "TOO", "TOP",
  "TRY", "TWO", "WAR", "WAS", "WAY", "WHO", "WHY", "WIN", "WON", "YET",
  "YOU", "BIG", "LOW", "HIGH", "CALL", "PUTS", "LONG", "SHORT", "BULL",
  "BEAR", "HOLD", "SELL", "BUY", "GAIN", "LOSS", "PUMP", "DUMP", "CASH",
  "DEBT", "RISK", "SAFE", "EDIT", "TLDR", "OP", "LMAO", "ROPE", "RIP",
  "BANG", "OG", "AI", "EV", "GOOD", "BAD", "BEST", "LIKE", "JUST", "EVEN",
  "OVER", "MOST", "MUCH", "NEXT", "ONLY", "VERY", "WELL", "ALSO", "BACK",
  "BEEN", "COME", "DOWN", "EACH", "FIND", "GIVE", "HAVE", "HERE", "KEEP",
  "LAST", "LOOK", "MADE", "MAKE", "MANY", "MORE", "MOVE", "MUST", "NAME",
  "NEED", "OPEN", "PART", "PLAY", "REAL", "SAID", "SAME", "SOME", "SURE",
  "TAKE", "TELL", "THAN", "THAT", "THEM", "THEN", "THEY", "THIS", "TIME",
  "TURN", "WANT", "WEEK", "WENT", "WERE", "WHAT", "WHEN", "WILL", "WITH",
  "WORK", "YEAR", "YOUR", "FREE", "HUGE", "HARD", "ZERO", "LMFAO",
  "COST", "FROM", "DOES", "DONE", "FULL", "HALF", "HELP", "HOME", "INTO",
  "LEFT", "LESS", "LIFE", "LINE", "LIST", "LIVE", "LONG", "LOST", "MARK",
  "MISS", "OWE", "PAYS", "POST", "REST", "RICH", "RISE", "SAVE", "SIDE",
  "SIZE", "STOP", "TALK", "TERM", "THEM", "TILL", "TRUE", "TYPE", "USED",
  "WAIT", "WAKE", "WALL", "WISH", "WORD", "YALL", "HOLY", "SHIT",
])

const TICKER_RE = /\$([A-Z]{1,5})\b/g
const BARE_TICKER_RE = /\b([A-Z]{2,5})\b/g

function extractTickers(text) {
  const tickers = new Set()
  for (const m of text.matchAll(TICKER_RE)) {
    if (!FALSE_POSITIVES.has(m[1])) tickers.add(m[1])
  }
  for (const m of text.matchAll(BARE_TICKER_RE)) {
    if (!FALSE_POSITIVES.has(m[1])) tickers.add(m[1])
  }
  return [...tickers]
}

export async function fetchTrending() {
  // Fetch directly from Reddit (browser request — no cloud IP blocking)
  const url = 'https://www.reddit.com/r/wallstreetbets/hot.json?limit=25'
  const res = await fetchWithTimeout(url, 10000)
  if (!res.ok) throw new Error('Reddit returned an error — try again in a moment')
  const data = await res.json()

  const children = (data?.data?.children || [])
  const mentions = {}

  for (const child of children) {
    const post = child?.data
    if (!post || post.stickied) continue

    const text = `${post.title || ''} ${post.selftext || ''}`
    const tickers = extractTickers(text)

    for (const ticker of tickers) {
      if (!mentions[ticker]) {
        mentions[ticker] = { ticker, mention_count: 0, total_score: 0, total_comments: 0 }
      }
      mentions[ticker].mention_count += 1
      mentions[ticker].total_score += (post.score || 0)
      mentions[ticker].total_comments += (post.num_comments || 0)
    }
  }

  // Rank by weighted score
  const tickers = Object.values(mentions)
    .map(t => ({
      ...t,
      weighted_score: t.mention_count * 3 + t.total_score * 0.01 + t.total_comments * 0.05,
    }))
    .sort((a, b) => b.weighted_score - a.weighted_score)
    .slice(0, 20)

  return { tickers }
}

// ── Stock analysis (calls Vercel backend) ──

export async function fetchStockDetail(ticker) {
  const res = await fetchWithTimeout(`${BASE}/stock/${ticker}`, 30000)
  if (!res.ok) throw new Error(`Failed to analyze ${ticker}`)
  return res.json()
}
