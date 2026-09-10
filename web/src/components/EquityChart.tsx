import ReactECharts from 'echarts-for-react'

const AXIS = '#7f93b5'
const GRID = 'rgba(80,180,255,0.08)'

export default function EquityChart({ dates, nav, benchmarkNav }: { dates: string[]; nav: number[]; benchmarkNav: number[] }) {
  const option = {
    backgroundColor: 'transparent',
    grid: { left: 52, right: 20, top: 34, bottom: 44 },
    legend: {
      data: ['策略净值', '基准(买入持有)'],
      textStyle: { color: AXIS, fontSize: 12 },
      top: 0,
      right: 10,
    },
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
    series: [
      {
        name: '策略净值',
        type: 'line',
        data: nav,
        showSymbol: false,
        smooth: true,
        lineStyle: { color: '#22d3ee', width: 2 },
        areaStyle: { color: 'rgba(34,211,238,0.10)' },
      },
      {
        name: '基准(买入持有)',
        type: 'line',
        data: benchmarkNav,
        showSymbol: false,
        smooth: true,
        lineStyle: { color: '#a855f7', width: 1.5, type: 'dashed' },
      },
    ],
  }

  return <ReactECharts option={option} style={{ height: 300 }} notMerge />
}
