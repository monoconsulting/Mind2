import React from 'react'
import { BrowserRouter, Routes, Route, useNavigate, useLocation } from 'react-router-dom'
import { FiHome, FiList, FiCreditCard, FiSliders, FiUpload, FiLogOut, FiBarChart } from 'react-icons/fi'
import Dashboard from '../ui/pages/Dashboard.jsx'
import Receipts from '../ui/pages/Receipts.jsx'
import CompanyCard from '../ui/pages/CompanyCard.jsx'
import Settings from '../ui/pages/Settings.jsx'
import ExportPage from '../ui/pages/Export.jsx'
import Login from '../ui/pages/Login.jsx'
import AiPage from '../ui/pages/Ai.jsx'
import { api } from '../ui/api'

function NavButton({ icon: Icon, label, to, isActive }) {
  const navigate = useNavigate()
  return (
    <button
      className={`w-full text-left flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200 ${
        isActive
          ? 'active bg-red-600 text-white'
          : 'text-gray-400 hover:text-white hover:bg-red-600 hover:bg-opacity-20'
      }`}
      onClick={() => navigate(to)}
    >
      <Icon className="text-lg flex-shrink-0" />
      <span className="font-medium">{label}</span>
    </button>
  )
}

function Shell({ children }) {
  const navigate = useNavigate()
  const location = useLocation()
  const authed = !!localStorage.getItem('mind.jwt')

  React.useEffect(() => {
    if (!authed) navigate('/login')
  }, [authed, navigate])

  const getPageTitle = () => {
    const titles = {
      '/': 'Översikt',
      '/receipts': 'Kvitton',
      '/company-card': 'Kortmatchning',
      '/ai': 'Analys',
      '/export': 'Export',
      '/settings': 'Användare'
    }
    return titles[location.pathname] || 'Mind Admin'
  }

  const handleLogout = () => {
    api.logout()
    navigate('/login')
  }

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="logo">
          <div className="brand-icon">M</div>
          <div className="brand-text">Mind Admin</div>
        </div>

        <nav className="flex flex-col gap-1">
          <NavButton
            icon={FiHome}
            label="Översikt"
            to="/"
            isActive={location.pathname === '/'}
          />
          <NavButton
            icon={FiList}
            label="Kvitton"
            to="/receipts"
            isActive={location.pathname === '/receipts'}
          />
          <NavButton
            icon={FiCreditCard}
            label="Kortmatchning"
            to="/company-card"
            isActive={location.pathname === '/company-card'}
          />
          <NavButton
            icon={FiBarChart}
            label="Analys"
            to="/ai"
            isActive={location.pathname === '/ai'}
          />
          <NavButton
            icon={FiUpload}
            label="Export"
            to="/export"
            isActive={location.pathname === '/export'}
          />
          <NavButton
            icon={FiSliders}
            label="Användare"
            to="/settings"
            isActive={location.pathname === '/settings'}
          />
        </nav>

        <div className="mt-auto pt-6">
          <div className="border-t border-gray-600 pt-4">
            <div className="flex items-center gap-2 mb-3 px-4">
              <div className="w-8 h-8 bg-gray-600 rounded-full flex items-center justify-center text-sm font-bold">
                A
              </div>
              <div className="text-sm">
                <div className="text-white font-medium">Administratör</div>
                <div className="text-gray-400 text-xs">Systemansvarig</div>
              </div>
            </div>
            <button
              className="w-full text-left flex items-center gap-3 px-4 py-3 rounded-lg text-gray-400 hover:text-white hover:bg-red-600 hover:bg-opacity-20 transition-all duration-200"
              onClick={handleLogout}
            >
              <FiLogOut className="text-lg" />
              <span className="font-medium">Logga ut</span>
            </button>
          </div>
        </div>
      </aside>

      <div className="flex flex-col h-full">
        <header className="header">
          <div className="page-title">{getPageTitle()}</div>
          <div className="user-menu">
            <div className="text-sm">
              Överblick över status för kvittohanteringen och centrala nyckeltal
            </div>
          </div>
        </header>
        <main className="main flex-1">{children}</main>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/" element={<Shell><Dashboard /></Shell>} />
        <Route path="/receipts" element={<Shell><Receipts /></Shell>} />
        <Route path="/company-card" element={<Shell><CompanyCard /></Shell>} />
        <Route path="/export" element={<Shell><ExportPage /></Shell>} />
        <Route path="/ai" element={<Shell><AiPage /></Shell>} />
        <Route path="/settings" element={<Shell><Settings /></Shell>} />
      </Routes>
    </BrowserRouter>
  )
}
