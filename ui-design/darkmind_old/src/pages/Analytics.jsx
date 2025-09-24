import React from 'react'
import LineAreaChart from '../components/charts/LineAreaChart.jsx'
import DoughnutChart from '../components/charts/DoughnutChart.jsx'
import data from '../data/demo.js'

export default function Analytics() {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div className="dm-card p-6">
        <div className="text-lg font-semibold mb-4">Revenue Trend</div>
        <LineAreaChart labels={data.months} data={data.revenue} seriesLabel="Revenue" />
      </div>
      <div className="dm-card p-6">
        <div className="text-lg font-semibold mb-4">Deals Trend</div>
        <LineAreaChart labels={data.months} data={data.deals} seriesLabel="Deals" />
      </div>
      <div className="dm-card p-6 lg:col-span-2">
        <div className="text-lg font-semibold mb-4">Customer Sources</div>
        <DoughnutChart labels={['Direct','Social','Referral']} data={[52, 36, 12]} />
      </div>
    </div>
  )
}
