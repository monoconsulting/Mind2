import React from 'react'
import { FiCpu, FiActivity, FiBarChart2, FiAlertCircle } from 'react-icons/fi'

const roadmapItems = [
  {
    title: 'Modellstatus',
    description: 'Överblick över träningsversioner, precision och driftstatus.',
    icon: FiCpu
  },
  {
    title: 'Automatiska insikter',
    description: 'Identifiera kvitton som avviker och föreslå åtgärder automatiskt.',
    icon: FiActivity
  },
  {
    title: 'Trendrapporter',
    description: 'Visa historik och prognoser för kostnader per kategori.',
    icon: FiBarChart2
  }
]

export default function AiPage() {
  return (
    <div className="space-y-6">
      <div className="card">
        <div className="card-header">
          <div>
            <h3 className="card-title">AI-panel</h3>
            <p className="card-subtitle">Kommande verktyg för analyser och kvalitetskontroll.</p>
          </div>
          <FiAlertCircle className="text-xl text-yellow-400" />
        </div>
        <p className="text-sm text-gray-300">
          Den här sidan sammanställer status för våra AI-modeller, träningsdata och kvalitetsmätningar.
          Funktionerna är under utveckling men kommer snart att visa såväl realtidsstatistik som rekommenderade åtgärder.
        </p>
      </div>

      <div className="stats-grid">
        {roadmapItems.map(({ title, description, icon: Icon }) => (
          <div key={title} className="card">
            <div className="flex items-start gap-3">
              <div className="p-3 rounded-lg bg-gray-800 text-red-300">
                <Icon className="text-xl" />
              </div>
              <div>
                <h4 className="text-lg font-semibold text-white mb-1">{title}</h4>
                <p className="text-sm text-gray-300">{description}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="card">
        <div className="card-header">
          <div>
            <h3 className="card-title">Nästa steg</h3>
            <p className="card-subtitle">Så förbereder du organisationen.</p>
          </div>
        </div>
        <ol className="list-decimal list-inside space-y-2 text-sm text-gray-300">
          <li>Säkerställ att kvittodata har rätt kategorisering för att förbättra modellernas träffsäkerhet.</li>
          <li>Planera hur avvikelser ska eskaleras när AI flaggar en transaktion.</li>
          <li>Förbered dashboards i ert BI-verktyg för att kombinera AI-insikter med andra nyckeltal.</li>
        </ol>
      </div>
    </div>
  )
}
