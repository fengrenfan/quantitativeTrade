import { useEffect, useState } from 'react'
import { fetchCatalog, fetchSignal } from '../api/client'
import type { Catalog, SignalResponse } from '../api/client'
import EquityChart from './EquityChart'
import KlineChart from './KlineChart'

const STRATEGY_LABEL: Record<string, string> = {
  dual_ma: '双均线',
  macd: 'MACD',
  bollinger: '布林带',
  momentum: '动量',
}
const TF_LABEL: Record<string, string> = { daily: '日线', weekly: '周线', '60min': '60分钟' }

export default function Dashboard() {
  const [catalog, setCatalog] = useState<Catalog | null>(null)
  const [symbol, setSymbol] = useState('600519.SH')
  const [strategy, setStrategy] = useState('dual_ma')
  const [timeframe, setTimeframe] = useState('daily')
  const [fast, setFast] = useState(5)
  const [slow, setSlow] = useState(20)
  const [data, setData] = useState<SignalResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    fetchCatalog()
      .then((c) => {
        setCatalog(c)
        setSymbol(c.symbols[0])
        setFast(c.defaultFast)
        setSlow(c.defaultSlow)
      })
      .catch((e) => setError(String(e?.message || e)))
  }, [])

  const load = () => {
    setLoading(true)
    setError('')
    fetchSignal({ symbol, strategy, timeframe, fast, slow })
      .then(setData)
      .catch((e) => setError(String(e?.message || e)))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const m = data?.metrics
  const pct = (v?: number | null) => (v == null ? '—' : `${(v * 100).toFixed(2)}%`)
  const num = (v?: number | null) => (v == null ? '—' : v.toFixed(2))
  const cls = (v?: number | null) => (v == null ? '' : v >= 0 ? 'pos' : 'neg')

  return (
    <div className="app">
      <div className="header">
        <div>
          <div className="title">量化趋势看板</div>
          <div className="subtitle">A股 · 多标的 / 多策略 / 多周期 / 多参数 · Python 引擎 + Spring Boot 网关 + ECharts</div>
        </div>
        {data && (
          <span className={`badge ${data.signal === '持多' ? 'long' : 'flat'}`}>当前信号：{data.signal}</span>
        )}
      </div>

      <div className="panel" style={{ marginBottom: 18 }}>
        <div className="controls">
          <div className="field">
            <label>标的</label>
            <select value={symbol} onChange={(e) => setSymbol(e.target.value)}>
              {(catalog?.symbols ?? ['600519.SH']).map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>策略</label>
            <select value={strategy} onChange={(e) => setStrategy(e.target.value)}>
              {(catalog?.strategies ?? ['dual_ma']).map((s) => (
                <option key={s} value={s}>{STRATEGY_LABEL[s] ?? s}</option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>周期</label>
            <select value={timeframe} onChange={(e) => setTimeframe(e.target.value)}>
              {(catalog?.timeframes ?? ['daily']).map((t) => (
                <option key={t} value={t}>{TF_LABEL[t] ?? t}</option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>快线</label>
            <input type="number" value={fast} onChange={(e) => setFast(Number(e.target.value))} />
          </div>
          <div className="field">
            <label>慢线</label>
            <input type="number" value={slow} onChange={(e) => setSlow(Number(e.target.value))} />
          </div>
          <button className="primary" onClick={load} disabled={loading}>
            {loading ? '计算中…' : '查询'}
          </button>
        </div>
      </div>

      {error && <div className="error">⚠ {error}</div>}

      {m && (
        <div className="metrics">
          <Metric label="年化收益" value={pct(m.annualReturn)} cls={cls(m.annualReturn)} />
          <Metric label="夏普比率" value={num(m.sharpe)} cls={cls(m.sharpe)} />
          <Metric label="最大回撤" value={pct(m.maxDrawdown)} cls="neg" />
          <Metric label="卡玛比率" value={num(m.calmar)} />
          <Metric label="胜率" value={pct(m.winRate)} />
          <Metric label="交易次数" value={String(data?.signals.length ?? 0)} />
        </div>
      )}

      {data && (
        <div className="charts">
          <div className="panel">
            <div className="chart-title">K 线（B=买入 / S=卖出）· {TF_LABEL[data.timeframe] ?? data.timeframe}</div>
            <KlineChart kline={data.kline} signals={data.signals} />
          </div>
          <div className="panel">
            <div className="chart-title">净值曲线（策略 vs 基准）</div>
            <EquityChart dates={data.dates} nav={data.nav} benchmarkNav={data.benchmarkNav} />
          </div>
        </div>
      )}
    </div>
  )
}

function Metric({ label, value, cls = '' }: { label: string; value: string; cls?: string }) {
  return (
    <div className="metric">
      <div className="label">{label}</div>
      <div className={`value ${cls}`}>{value}</div>
    </div>
  )
}
