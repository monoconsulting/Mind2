import React from 'react'
import { createRoot } from 'react-dom/client'
import { FiActivity, FiFileText, FiCheckCircle, FiClock, FiTrendingUp, FiDollarSign, FiHardDrive } from 'react-icons/fi'
import './index.css'

// Simple Dashboard component without API calls for testing
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

function SimpleTestDashboard() {
  return (
    <div className="space-y-6" style={{padding: '20px'}}>
      <div className="text-secondary text-sm" style={{color: '#a0aec0'}}>
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

      {/* Recent Activity */}
      <div className="card">
        <div className="card-header">
          <div>
            <h3 className="card-title">Recent Activity</h3>
          </div>
        </div>
        <div>
          <div className="activity-item">
            <div className="activity-dot success"></div>
            <div className="activity-content">
              <div className="activity-message">Receipt IMG_2023_001.jpg processed successfully</div>
              <div className="activity-time">2 minutes ago</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function TestApp() {
  return (
    <div style={{background: '#1a202c', minHeight: '100vh'}}>
      <h1 style={{color: 'white', padding: '20px', margin: 0}}>SIMPLE DASHBOARD TEST</h1>
      <SimpleTestDashboard />
    </div>
  )
}

createRoot(document.getElementById('root')).render(<TestApp />)