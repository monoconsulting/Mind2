import React from 'react'
import { Routes, Route, NavLink } from 'react-router-dom'
import { FiBarChart2, FiGrid, FiSettings, FiSearch, FiFolder, FiHome } from 'react-icons/fi'
import Dashboard from './pages/Dashboard.jsx'
import Projects from './pages/Projects.jsx'
import Analytics from './pages/Analytics.jsx'

const SidebarLink = ({ to, icon: Icon, children }) => (
  <NavLink
    to={to}
    className={({ isActive }) =>
      `flex items-center gap-3 px-4 py-2 rounded-xl hover:bg-dm-muted/60 transition ${isActive ? 'bg-dm-muted nav-active' : 'text-dm-subt'}`
    }
  >
    <Icon className="text-lg" />
    <span className="font-medium">{children}</span>
  </NavLink>
)

export default function App() {
  return (
    <div className="min-h-screen bg-dm-bg text-dm-text">
      <div className="flex">
        {/* Sidebar */}
        <aside className="w-64 hidden md:flex flex-col gap-4 p-4 border-r border-dm-border bg-dm-surface">
          <div className="flex items-center gap-3 px-2 py-3">
            <div className="h-9 w-9 rounded-2xl dm-gradient shadow-dm-soft" />
            <div>
              <div className="text-lg font-semibold">DarkMind</div>
              <div className="text-xs text-dm-subt">Admin Suite</div>
            </div>
          </div>
          <nav className="flex flex-col gap-1">
            <div className="uppercase tracking-wide text-xs text-dm-subt px-2 mt-2 mb-1">General</div>
            <SidebarLink to="/" icon={FiHome}>Dashboard</SidebarLink>
            <SidebarLink to="/projects" icon={FiFolder}>Projects</SidebarLink>
            <SidebarLink to="/analytics" icon={FiBarChart2}>Analytics</SidebarLink>
            <div className="uppercase tracking-wide text-xs text-dm-subt px-2 mt-4 mb-1">System</div>
            <SidebarLink to="/settings" icon={FiSettings}>Settings</SidebarLink>
          </nav>
          <div className="mt-auto text-xs text-dm-subt px-2">v1.0.0</div>
        </aside>

        {/* Main */}
        <main className="flex-1">
          {/* Topbar */}
          <header className="sticky top-0 z-20 bg-dm-bg/80 backdrop-blur border-b border-dm-border">
            <div className="max-w-7xl mx-auto px-4 py-3 flex items-center gap-3">
              <div className="text-xl font-semibold hidden sm:block">Dashboard Overview</div>
              <div className="flex-1" />
              <div className="relative w-full max-w-md hidden md:block">
                <FiSearch className="absolute left-3 top-1/2 -translate-y-1/2 text-dm-subt" />
                <input type="search" placeholder="Search" className="w-full pl-10" />
              </div>
              <button className="dm flex items-center gap-2"><FiSettings /> <span className="hidden sm:inline">Settings</span></button>
            </div>
          </header>

          {/* Content */}
          <div className="max-w-7xl mx-auto p-4 grid gap-6">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/projects" element={<Projects />} />
              <Route path="/analytics" element={<Analytics />} />
              <Route path="*" element={<div className="dm-card p-6">Not Found</div>} />
            </Routes>
          </div>
        </main>
      </div>
    </div>
  )
}
