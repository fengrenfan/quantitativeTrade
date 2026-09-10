export interface KlineBar {
  date: string
  open: number
  close: number
  low: number
  high: number
}

export interface SignalPoint {
  date: string
  type: 'buy' | 'sell'
  price: number
}

export interface Metrics {
  annualReturn: number | null
  annualVol: number | null
  sharpe: number | null
  maxDrawdown: number | null
  calmar: number | null
  winRate: number | null
  avgTurnover: number | null
  totalReturn: number | null
  benchmarkReturn: number | null
  bars: number
}

export interface SignalResponse {
  symbol: string
  strategy: string
  timeframe: string
  fast: number
  slow: number
  dates: string[]
  kline: KlineBar[]
  nav: number[]
  benchmarkNav: number[]
  position: number[]
  signals: SignalPoint[]
  signal: string
  lastClose: number | null
  lastDate: string | null
  metrics: Metrics
}

export interface Catalog {
  symbols: string[]
  strategies: string[]
  timeframes: string[]
  defaultFast: number
  defaultSlow: number
}

const BASE = (import.meta as any).env?.VITE_API_BASE ?? ''

export async function fetchCatalog(): Promise<Catalog> {
  const r = await fetch(`${BASE}/api/catalog`)
  if (!r.ok) throw new Error(`加载元数据失败：${r.status}`)
  return r.json()
}

export async function fetchSignal(params: {
  symbol: string
  strategy: string
  timeframe: string
  fast: number
  slow: number
}): Promise<SignalResponse> {
  const q = new URLSearchParams({
    symbol: params.symbol,
    strategy: params.strategy,
    timeframe: params.timeframe,
    fast: String(params.fast),
    slow: String(params.slow),
  })
  const r = await fetch(`${BASE}/api/signal?${q.toString()}`)
  if (!r.ok) {
    const txt = await r.text().catch(() => '')
    throw new Error(txt || `加载信号失败：${r.status}`)
  }
  return r.json()
}
