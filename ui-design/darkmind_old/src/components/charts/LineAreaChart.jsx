import React, { useRef, useEffect } from 'react'
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Filler } from 'chart.js'
import { Line } from 'react-chartjs-2'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Filler)

export default function LineAreaChart({ labels, seriesLabel='Revenue', data }) {
  const ref = useRef(null)

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: {
          label: (ctx) => `${seriesLabel}: $${ctx.parsed.y}`
        }
      }
    },
    scales: {
      x: { ticks: { color: '#9ca3af' }, grid: { display: false } },
      y: { ticks: { color: '#9ca3af' }, grid: { color: 'rgba(255,255,255,0.06)' } }
    }
  }

  const gradientFactory = (ctx) => {
    const g = ctx.createLinearGradient(0, 0, 0, 260)
    g.addColorStop(0, 'rgba(139,92,246,0.45)')   // violet
    g.addColorStop(1, 'rgba(139,92,246,0.02)')
    return g
  }

  const chartData = {
    labels,
    datasets: [
      {
        label: seriesLabel,
        data,
        borderColor: '#f97316',       // orange-500 line for contrast
        borderWidth: 2.5,
        fill: true,
        pointRadius: 0,
        backgroundColor: (ctx) => {
          const chart = ctx.chart
          const {ctx: c} = chart
          return gradientFactory(c)
        },
        tension: 0.35,
      }
    ]
  }

  return (
    <div className="h-64">
      <Line ref={ref} options={options} data={chartData} />
    </div>
  )
}
