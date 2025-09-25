import React from 'react'
import { FiActivity, FiFileText, FiCheckCircle, FiClock, FiTrendingUp, FiDollarSign, FiHardDrive } from 'react-icons/fi'
import { api } from '../api'

function StatCard({ icon: Icon, title, value, subtitle, color = "red" }) {
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
          <h3 className="card-title">Recent Activity</h3>
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
          <h3 className="card-title">Storage Usage</h3>
        </div>
        <FiHardDrive className="text-xl text-blue-400" />
      </div>
      <div>
        <div className="flex justify-between items-center mb-2">
          <span className="text-sm text-gray-400">Used: 0 GB</span>
          <span className="text-sm text-blue-400">Total: 10 GB</span>
        </div>
        <div className="storage-bar">
          <div className="storage-progress" style={{ width: '0%' }}></div>
        </div>
        <p className="text-xs text-gray-500 mt-2">0% of available storage used</p>
      </div>
    </div>
  )
}

function QuickActions() {
  return (
    <div className="card">
      <div className="card-header">
        <div>
          <h3 className="card-title">Quick Actions</h3>
        </div>
      </div>
      <div className="quick-actions-grid">
        <div className="quick-action-btn red">
          <FiFileText className="text-lg" />
          <div>
            <div className="font-medium">View All Receipts</div>
            <div className="text-xs opacity-75">Browse and manage receipts</div>
          </div>
        </div>
        <div className="quick-action-btn blue">
          <FiClock className="text-lg" />
          <div>
            <div className="font-medium">Processing Pipeline</div>
            <div className="text-xs opacity-75">Monitor workflow status</div>
          </div>
        </div>
        <div className="quick-action-btn purple">
          <FiTrendingUp className="text-lg" />
          <div>
            <div className="font-medium">System Management</div>
            <div className="text-xs opacity-75">Control infrastructure tools</div>
          </div>
        </div>
        <div className="quick-action-btn green">
          <FiCheckCircle className="text-lg" />
          <div>
            <div className="font-medium">Health Monitor</div>
            <div className="text-xs opacity-75">View system analytics</div>
          </div>
        </div>
        <div className="quick-action-btn red">
          <FiActivity className="text-lg" />
          <div>
            <div className="font-medium">Failed Items</div>
            <div className="text-xs opacity-75">Review and retry failures</div>
          </div>
        </div>
        <div className="quick-action-btn red">
          <FiDollarSign className="text-lg" />
          <div>
            <div className="font-medium">Trigger Manual Fetch</div>
            <div className="text-xs opacity-75">Force FTP download now</div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function Dashboard() {
  const [apiStatus, setApiStatus] = React.useState('')
  const [loading, setLoading] = React.useState(false)

  const recentActivities = [
    {
      message: "Receipt IMG_2023_001.jpg processed successfully",
      time: "2 minutes ago",
      type: "success"
    },
    {
      message: "OCR failed for receipt IMG_2023_002.jpg",
      time: "5 minutes ago",
      type: "error"
    },
    {
      message: "Batch of 12 receipts completed",
      time: "8 minutes ago",
      type: "success"
    },
    {
      message: "Receipt IMG_2023_003.jpg flagged for manual review",
      time: "15 minutes ago",
      type: "warning"
    }
  ]

  const testApiConnection = async () => {
    setLoading(true)
    try {
      const res = await api.fetch('/ai/api/admin/ping')
      const txt = await res.text()
      setApiStatus(`API connection working (${res.status}: ${txt})`)
    } catch (e) {
      setApiStatus(`API error: ${e}`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Welcome Section */}
      <div className="text-secondary text-sm">
        Overview of receipt processing system status and metrics
      </div>

      {/* Stats Grid */}
      <div className="stats-grid">
        <StatCard
          icon={FiFileText}
          title="Total Receipts"
          value="134"
          subtitle="269 this week • +347 this month"
          color="red"
        />
        <StatCard
          icon={FiTrendingUp}
          title="Success Rate"
          value="94.5%"
          subtitle="+2.1% from last week"
          color="green"
        />
        <StatCard
          icon={FiClock}
          title="Processing Queue"
          value="23"
          subtitle="0 processing • 8 failed"
          color="yellow"
        />
        <StatCard
          icon={FiCheckCircle}
          title="System Health"
          value="Warning"
          subtitle="All systems operational"
          color="blue"
        />
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <RecentActivity activities={recentActivities} />
        <StorageUsage />
      </div>

      {/* Quick Actions */}
      <QuickActions />

      {/* System Status Test */}
      <div className="card">
        <div className="card-header">
          <div>
            <h3 className="card-title">System Status</h3>
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
                Testing API...
              </>
            ) : (
              <>
                <FiActivity className="mr-2" />
                Test API Connection
              </>
            )}
          </button>
          {apiStatus && (
            <div className={`p-4 rounded-lg text-sm ${
              apiStatus.includes('working')
                ? 'bg-green-900 text-green-200 border border-green-700'
                : 'bg-red-900 text-red-200 border border-red-700'
            }`}>
              {apiStatus}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}