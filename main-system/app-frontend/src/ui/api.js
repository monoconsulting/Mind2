export const TOKEN_KEY = 'mind.jwt'

export const api = {
  async fetch(path, opts = {}) {
    const token = localStorage.getItem(TOKEN_KEY)
    const headers = new Headers(opts.headers || {})
    if (token) headers.set('Authorization', `Bearer ${token}`)
    const res = await fetch(path, { ...opts, headers })
    if (res.status === 401) {
      try { localStorage.removeItem(TOKEN_KEY) } catch {}
      if (typeof window !== 'undefined') window.location.href = '/login'
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

