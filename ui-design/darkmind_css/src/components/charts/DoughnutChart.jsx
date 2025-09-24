import React from 'react'
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from 'chart.js'
import { Doughnut } from 'react-chartjs-2'

ChartJS.register(ArcElement, Tooltip, Legend)

export default function DoughnutChart({ labels=['Direct','Social','Referral'], data=[55,35,10] }) {
  const chartData = {
    labels,
    datasets: [{
      label: 'Customers',
      data,
      backgroundColor: ['#8b5cf6', '#22d3ee', '#f59e0b'],
      borderWidth: 0,
      hoverOffset: 4,
    }]
  }
  const options = {
    plugins: {
      legend: {
        labels: { color: '#e5e7eb' }
      }
    }
  }
  return <div className="h-64"><Doughnut data={chartData} options={options} /></div>
}
