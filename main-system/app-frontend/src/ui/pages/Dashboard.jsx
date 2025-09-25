import React from 'react'
import { FiActivity, FiFileText, FiCheckCircle, FiClock, FiTrendingUp, FiDollarSign, FiHardDrive } from 'react-icons/fi'
import { api } from '../api'

function StatCard({ icon: Icon, title, value, subtitle, color = 'red' }) {
  return (
    <div className={`stat-card ${color}`}>
      <div className="flex items-center justify-between mb-2">
        <Icon className="text-2xl opacity-80" />
        <div className="text-right">
          <div className="stat-number">{value}</div>
        </div>
      </div>
      <div className="stat-label">{title}</div>
      <div className="stat-subtitle">{subtitle}</div>
    </div>
  )
}

function RecentActivity({ activities }) {
  return (
    <div className="card">
      <div className="card-header">
        <div>
          <h3 className="card-title">Senaste händelser</h3>
          <p className="card-subtitle">Automatiska uppdateringar från systemet</p>
        </div>
      </div>
      <div>
        {activities.map((activity, index) => (
          <div key={index} className="activity-item">
            <div className={`activity-dot ${activity.type}`}></div>
            <div className="activity-content">
              <div className="activity-message">{activity.message}</div>
              <div className="activity-time">{activity.time}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function StorageUsage() {
  return (
    <div className="card">
      <div className="card-header">
        <div>
          <h3 className="card-title">Lagringsanvändning</h3>
          <p className="card-subtitle">Förbrukning i Mind-plattformen</p>
        </div>
        <FiHardDrive className="text-xl text-blue-400" />
      </div>
      <div>
        <div className="flex justify-between items-center mb-2">
          <span className="text-sm text-gray-400">Använt: 0 GB</span>
          <span className="text-sm text-blue-400">Totalt: 10 GB</span>
        </div>
        <div className="storage-bar">
          <div className="storage-progress" style={{ width: '0%' }}></div>
        </div>
        <p className="text-xs text-gray-500 mt-2">0% av tilldelad lagring nyttjas</p>
      </div>
    </div>
  )
}

function QuickActions() {
  const actions = [
    {
      icon: FiFileText,
      title: 'Visa alla kvitton',
      subtitle: 'Gå direkt till kvittoöversikten',
      color: 'red'
    },
    {
      icon: FiClock,
      title: 'Bearbetningsflöde',
      subtitle: 'Följ pipeline och köstatus',
      color: 'blue'
    },
    {
      icon: FiTrendingUp,
      title: 'Systemhantering',
      subtitle: 'Hantera integrationer och drift',
      color: 'purple'
    },
    {
      icon: FiCheckCircle,
      title: 'Hälsomonitor',
      subtitle: 'Kontrollera AI och regelmotor',
      color: 'green'
    },
    {
      icon: FiActivity,
      title: 'Felhantering',
      subtitle: 'Överblick över misslyckade poster',
      color: 'red'
    },
    {
      icon: FiDollarSign,
      title: 'Manuell hämtning',
      subtitle: 'Starta om FTP-importen',
      color: 'red'
    }
  ]

  return (
    <div className="card">
      <div className="card-header">
        <div>
          <h3 className="card-title">Snabbåtgärder</h3>
          <p className="card-subtitle">Vanliga steg för ekonomi- och driftteam</p>
        </div>
      </div>
      <div className="quick-actions-grid">
        {actions.map(({ icon: Icon, title, subtitle, color }) => (
          <div key={title} className={`quick-action-btn ${color}`}>
            <Icon className="text-lg" />
            <div>
              <div className="font-medium">{title}</div>
              <div className="text-xs opacity-75">{subtitle}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function Dashboard() {
  const [apiStatus, setApiStatus] = React.useState(null)
  const [loading, setLoading] = React.useState(false)

  const recentActivities = [
    {
      message: 'Kvitto IMG_2025_001.jpg behandlades utan fel',
      time: 'För 2 minuter sedan',
      type: 'success'
    },
    {
      message: 'OCR misslyckades för kvitto IMG_2025_002.jpg',
      time: 'För 5 minuter sedan',
      type: 'error'
    },
    {
      message: 'Batch med 12 kvitton är färdigställd',
      time: 'För 8 minuter sedan',
      type: 'success'
    },
    {
      message: 'Kvitto IMG_2025_003.jpg markerat för manuell kontroll',
      time: 'För 15 minuter sedan',
      type: 'warning'
    }
  ]

  const testApiConnection = async () => {
    setLoading(true)
    try {
      const res = await api.fetch('/ai/api/admin/ping')
      const txt = await res.text()
      setApiStatus({
        type: 'success',
        message: `API-anslutning fungerar (${res.status}: ${txt})`
      })
    } catch (error) {
      setApiStatus({
        type: 'error',
        message: `API-fel: ${error instanceof Error ? error.message : error}`
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="text-secondary text-sm">
        Daglig lägesbild över automatiserad kvittohantering och systemhälsa
      </div>

      <div className="stats-grid">
        <StatCard
          icon={FiFileText}
          title="Totalt antal kvitton"
          value="134"
          subtitle="306 registrerade denna vecka"
          color="red"
        />
        <StatCard
          icon={FiTrendingUp}
          title="Träffsäkerhet"
          value="94,5%"
          subtitle="+2,1 procentenheter jämfört med föregående vecka"
          color="green"
        />
        <StatCard
          icon={FiClock}
          title="Bearbetningskö"
          value="23"
          subtitle="0 pågår just nu · 8 kräver åtgärd"
          color="yellow"
        />
        <StatCard
          icon={FiCheckCircle}
          title="Systemhälsa"
          value="Varning"
          subtitle="Samtliga tjänster svarar normalt"
          color="blue"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <RecentActivity activities={recentActivities} />
        <StorageUsage />
      </div>

      <QuickActions />

      <div className="card">
        <div className="card-header">
          <div>
            <h3 className="card-title">Systemstatus</h3>
            <p className="card-subtitle">Testa API-knutpunkter och samla svar</p>
          </div>
        </div>
        <div className="space-y-4">
          <button
            className={`btn btn-primary ${loading ? 'opacity-50' : ''}`}
            onClick={testApiConnection}
            disabled={loading}
          >
            {loading ? (
              <>
                <div className="loading-spinner mr-2"></div>
                Testar anslutning...
              </>
            ) : (
              <>
                <FiActivity className="mr-2" />
                Testa API-anslutning
              </>
            )}
          </button>
          {apiStatus && (
            <div className={`p-4 rounded-lg text-sm ${
              apiStatus.type === 'success'
                ? 'bg-green-900 text-green-200 border border-green-700'
                : 'bg-red-900 text-red-200 border border-red-700'
            }`}>
              {apiStatus.message}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
