import React from 'react'
import { FiTrendingUp, FiUsers, FiBriefcase, FiThumbsUp } from 'react-icons/fi'
import LineAreaChart from '../components/charts/LineAreaChart.jsx'
import DoughnutChart from '../components/charts/DoughnutChart.jsx'
import data from '../data/demo.js'

const StatCard = ({ icon: Icon, label, value, delta }) => (
  <div className="dm-card p-5">
    <div className="kpi">
      <div className="flex items-center justify-between">
        <div className="label flex items-center gap-2"><Icon className="text-dm-subt" /> {label}</div>
        {delta && <div className="text-sm text-dm-subt">{delta}</div>}
      </div>
      <div className="value">{value}</div>
    </div>
  </div>
)

export default function Dashboard() {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <section className="lg:col-span-2 dm-card p-6 dm-gradient-border">
        <div className="flex items-center justify-between mb-4">
          <div>
            <div className="text-lg font-semibold">Overview</div>
            <div className="text-sm text-dm-subt">Dashboard Overview • Last 30 days</div>
          </div>
          <div className="flex items-center gap-3">
            <div className="relative">
              <input placeholder="Search projects..." className="pl-10 pr-4 py-2 rounded-xl bg-dm-muted text-sm text-dm-text" />
              <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-dm-subt" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-4.35-4.35M10.5 18a7.5 7.5 0 1 0 0-15 7.5 7.5 0 0 0 0 15z"/></svg>
            </div>
            <div className="dm-avatar"><img src="/src/assets/logo.svg" alt="user"/></div>
          </div>
        </div>
        <LineAreaChart labels={data.months} data={data.revenue} seriesLabel="Revenue" />
      </section>

      <section className="dm-card p-6">
  <div className="text-lg font-semibold mb-4">Customer</div>
        <DoughnutChart />
        <div className="flex items-center justify-around mt-4 text-sm text-dm-subt">
          <div className="flex items-center gap-2"><span className="h-2 w-2 rounded-full" style={{background:'#8b5cf6'}}></span> Direct</div>
          <div className="flex items-center gap-2"><span className="h-2 w-2 rounded-full" style={{background:'#22d3ee'}}></span> Social</div>
        </div>
      </section>

      <section className="lg:col-span-3 grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard icon={FiTrendingUp} label="Monthly Revenue" value="$24,560" delta="+8%" />
        <StatCard icon={FiUsers} label="New Customers" value="1,204" delta="+2%" />
        <StatCard icon={FiBriefcase} label="Open Projects" value="42" delta="-1%" />
        <StatCard icon={FiThumbsUp} label="Satisfaction" value="96%" delta="+0.6%" />
      </section>

      <section className="lg:col-span-2 dm-card p-6">
        <div className="text-lg font-semibold mb-4">Top Projects</div>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="text-dm-subt">
              <tr>
                <th className="text-left py-2 pr-4">Project</th>
                <th className="text-left py-2 pr-4">Lead</th>
                <th className="text-left py-2 pr-4">Company</th>
                <th className="text-left py-2 pr-4">Progress</th>
                <th className="text-left py-2 pr-4">Value</th>
              </tr>
            </thead>
            <tbody>
              {Array.from({length:6}).map((_,i)=>{
                const lead = ['Alice','Bob','Carol','Dave'][i%4]
                const company = ['ByteSync Inc.','LunaTech Ltd.','TitanSys','AeroWave Co.'][i%4]
                const progress = [72,45,88,34,60,15][i%6]
                return (
                <tr key={i} className="border-t border-dm-border/60">
                  <td className="py-3 pr-4">Project #{i+1}</td>
                  <td className="py-3 pr-4 flex items-center gap-3">
                    <div className="dm-avatar"><img src={`/src/assets/logo.svg`} alt={lead} /></div>
                    <div>{lead}</div>
                  </td>
                  <td className="py-3 pr-4">{company}</td>
                  <td className="py-3 pr-4 w-40">
                    <div className="dm-progress"><i style={{width: `${progress}%`, background: `linear-gradient(90deg, var(--dm-primary), var(--dm-primary-2))`}}></i></div>
                    <div className="text-xs text-dm-subt mt-1">{progress}%</div>
                  </td>
                  <td className="py-3 pr-4">${(Math.random()*1000+250).toFixed(2)}</td>
                </tr>)
              })}
            </tbody>
          </table>
        </div>
      </section>

      <section className="dm-card p-6">
        <div className="text-lg font-semibold mb-2">Team Chat</div>
        <div className="text-sm text-dm-subt">Lightweight placeholder for a chat widget.</div>
        <div className="mt-3 p-3 bg-dm-muted rounded-xl text-sm flex items-start gap-3">
          <div className="dm-avatar"><img src="/src/assets/logo.svg" alt="sarah"/></div>
          <div>
            <div className="text-sm font-medium">Sarah Johnson <span className="text-xs text-dm-subt">· 2m</span></div>
            <div className="text-sm text-dm-text">Hi there! 👋</div>
          </div>
        </div>
        <div className="mt-3 p-3 bg-dm-muted rounded-xl text-sm flex items-start gap-3">
          <div className="dm-avatar"><img src="/src/assets/logo.svg" alt="bob"/></div>
          <div>
            <div className="text-sm font-medium">Bob <span className="text-xs text-dm-subt">· 5m</span></div>
            <div className="text-sm text-dm-text">How's it going?</div>
          </div>
        </div>
      </section>
    </div>
  )
}
