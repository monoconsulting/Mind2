export const TOKEN_KEY = 'mind.jwt'

const handleUnauthorized = () => {
  try {
    localStorage.removeItem(TOKEN_KEY)
  } catch (error) {
    // ignore storage errors
  }
  if (typeof window !== 'undefined') {
    window.location.href = '/login'
  }
}

export const api = {
  async fetch(path, opts = {}) {
    const token = localStorage.getItem(TOKEN_KEY)
    const headers = new Headers(opts.headers || {})
    if (token) {
      headers.set('Authorization', `Bearer ${token}`)
    }
    const response = await fetch(path, { ...opts, headers })
    if (response.status === 401) {
      handleUnauthorized()
    }
    return response
  },
  async login(username, password) {
    const res = await fetch('/ai/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    })
    if (!res.ok) throw new Error(`Login failed (${res.status})`)
    const data = await res.json()
    localStorage.setItem(TOKEN_KEY, data.access_token)
    return data
  },
  logout() {
    try {
      localStorage.removeItem(TOKEN_KEY)
    } catch (error) {
      // ignore storage errors
    }
  }
}
