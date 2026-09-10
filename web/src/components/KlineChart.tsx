import ReactECharts from 'echarts-for-react'
import type { KlineBar, SignalPoint } from '../api/client'

// A 股约定：涨红跌绿
const UP = '#ff4d6d'
const DOWN = '#22c55e'
const AXIS = '#7f93b5'
const GRID = 'rgba(80,180,255,0.08)'

export default function KlineChart({ kline, signals }: { kline: KlineBar[]; signals: SignalPoint[] }) {
  const dates = kline.map((k) => k.date)
  const ohlc = kline.map((k) => [k.open, k.close, k.low, k.high])

  const marks = signals.map((s) => ({
    coord: [s.date, s.type === 'buy' ? s.price * 0.982 : s.price * 1.018],
    value: s.type === 'buy' ? 'B' : 'S',
    itemStyle: { color: s.type === 'buy' ? UP : DOWN },
    label: { color: '#05070d', fontSize: 11, fontWeight: 700 },
  }))

  const option = {
    backgroundColor: 'transparent',
    grid: { left: 52, right: 20, top: 18, bottom: 52 },
    tooltip: { trigger: 'axis', backgroundColor: '#0d1424', borderColor: 'rgba(80,180,255,0.3)', textStyle: { color: '#e6f0ff', fontSize: 12 } },
    xAxis: {
      type: 'category',
      data: dates,
      axisLine: { lineStyle: { color: '#2a3a55' } },
      axisLabel: { color: AXIS, fontSize: 11 },
    },
    yAxis: {
      scale: true,
      axisLabel: { color: AXIS, fontSize: 11 },
      splitLine: { lineStyle: { color: GRID } },
    },
    dataZoom: [
      { type: 'inside', start: 55, end: 100 },
      { type: 'slider', start: 55, end: 100, height: 18, bottom: 10, borderColor: 'transparent', textStyle: { color: AXIS }, dataBackground: { lineStyle: { color: '#2a3a55' }, areaStyle: { color: '#1b2942' } } },
    ],
    series: [
      {
        type: 'candlestick',
        data: ohlc,
        itemStyle: { color: UP, color0: DOWN, borderColor: UP, borderColor0: DOWN },
        markPoint: { symbolSize: 42, data: marks },
      },
    ],
  }

  return <ReactECharts option={option} style={{ height: 360 }} notMerge />
}
