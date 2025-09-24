export const TOKEN_KEY = 'mind.jwt'

export const api = {
  async fetch(path, opts = {}) {
    const token = localStorage.getItem(TOKEN_KEY)
    const headers = new Headers(opts.headers || {})
    if (token) headers.set('Authorization', `Bearer ${token}`)
    const res = await fetch(path, { ...opts, headers })
    if (res.status === 401) {
      try { localStorage.removeItem(TOKEN_KEY) } catch {}
      if (typeof navigate === 'function') navigate('login')
    }
    return res
  },
  async login(username, password) {
    const res = await fetch('/ai/api/auth/login', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    })
    if (!res.ok) throw new Error(`Login failed (${res.status})`)
    const data = await res.json()
    localStorage.setItem(TOKEN_KEY, data.access_token)
    return data
  },
  logout() { localStorage.removeItem(TOKEN_KEY) }
}

const app = document.getElementById('app')

export function renderShell(contentHtml) {
  app.innerHTML = `
    <header class="dm-header">
      <h1>Mind Admin</h1>
      <div>
        <button id="logout" style="float:right;">Logout</button>
      </div>
    </header>
  <nav class="dm-nav" style="display:flex;gap:.5rem;padding:.5rem;border-bottom:1px solid var(--dm-border);background:#0f1426;">
      <button id="nav-dashboard">Dashboard</button>
      <button id="nav-receipts">Kvitton</button>
      <button id="nav-card">Company Card</button>
      <button id="nav-export">Export</button>
      <button id="nav-settings">Settings</button>
    </nav>
    <main class="dm-main">
      ${contentHtml}
    </main>
  `
  document.getElementById('nav-dashboard').addEventListener('click', () => navigate('dashboard'))
  document.getElementById('nav-receipts').addEventListener('click', () => navigate('receipts'))
  document.getElementById('nav-card').addEventListener('click', () => navigate('company-card'))
  document.getElementById('nav-export').addEventListener('click', () => navigate('export'))
  document.getElementById('nav-settings').addEventListener('click', () => navigate('settings'))
  document.getElementById('logout').addEventListener('click', () => { api.logout(); navigate('login') })
}

// simple router registry
const routes = new Map()
export function register(route, fn) { routes.set(route, fn) }

export function navigate(route, params) {
  const authed = !!localStorage.getItem(TOKEN_KEY)
  if (!authed && route !== 'login') return renderLogin()
  const fn = routes.get(route)
  if (fn) return fn(params)
  return renderLogin()
}

export function renderLogin() {
  app.innerHTML = `
    <main class="dm-main" style="max-width:420px;margin:5rem auto;">
      <h2>Sign in</h2>
      <form id="loginForm" class="dm-card" style="display:flex;flex-direction:column;gap:.5rem;padding:1rem;">
        <label>Username <input id="u" value="admin" /></label>
        <label>Password <input id="p" type="password" /></label>
        <button type="submit">Login</button>
        <pre id="err" style="color:#ff6b6b;"></pre>
      </form>
    </main>
  `
  document.getElementById('loginForm').addEventListener('submit', async (e) => {
    e.preventDefault()
    const u = document.getElementById('u').value
    const p = document.getElementById('p').value
    const err = document.getElementById('err')
    err.textContent = ''
    try { await api.login(u, p); navigate('dashboard') } catch (ex) { err.textContent = ex?.message || String(ex) }
  })
}

