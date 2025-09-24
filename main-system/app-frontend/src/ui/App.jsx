import React from 'react'
import { Routes, Route, useNavigate } from 'react-router-dom'
import { FiHome, FiList, FiCreditCard, FiSliders, FiUpload, FiCpu } from 'react-icons/fi'
import Dashboard from '../ui/pages/Dashboard.jsx'
import Receipts from '../ui/pages/Receipts.jsx'
import CompanyCard from '../ui/pages/CompanyCard.jsx'
import Settings from '../ui/pages/Settings.jsx'
import ExportPage from '../ui/pages/Export.jsx'
import Login from '../ui/pages/Login.jsx'
import AiPage from '../ui/pages/Ai.jsx'
import { api } from '../ui/api'

function NavButton({ icon: Icon, label, to }) {
  const navigate = useNavigate()
  return (
    <button
      className="w-full text-left flex items-center gap-2 px-3 py-2 rounded hover:bg-[#0c1430]"
      onClick={() => navigate(to)}
    >
      <Icon className="text-xl text-[#9aa3c7]" />
      <span>{label}</span>
    </button>
  )
}

function Shell({ children }) {
  const navigate = useNavigate()
  const authed = !!localStorage.getItem('mind.jwt')
  React.useEffect(() => {
    if (!authed) navigate('/login')
  }, [authed, navigate])
  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="text-lg font-semibold mb-2">Mind Admin</div>
        <nav className="flex flex-col gap-1">
          <NavButton icon={FiHome} label="Översikt" to="/" />
          <NavButton icon={FiList} label="Kvitton" to="/receipts" />
          <NavButton icon={FiCreditCard} label="Företagskort" to="/company-card" />
          <NavButton icon={FiCpu} label="AI" to="/ai" />
          <NavButton icon={FiUpload} label="Export" to="/export" />
          <NavButton icon={FiSliders} label="Inställningar" to="/settings" />
        </nav>
      </aside>
      <div className="flex flex-col">
        <header className="header">
          <div />
          <div>
            {authed && (
              <button className="dm-btn" onClick={() => { api.logout(); navigate('/login') }}>Logga ut</button>
            )}
          </div>
        </header>
        <main className="main">{children}</main>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/" element={<Shell><Dashboard /></Shell>} />
      <Route path="/receipts" element={<Shell><Receipts /></Shell>} />
      <Route path="/company-card" element={<Shell><CompanyCard /></Shell>} />
      <Route path="/export" element={<Shell><ExportPage /></Shell>} />
      <Route path="/ai" element={<Shell><AiPage /></Shell>} />
      <Route path="/settings" element={<Shell><Settings /></Shell>} />
    </Routes>
  )
}
