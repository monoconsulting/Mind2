import React from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'

export default function Login() {
  const nav = useNavigate()
  const [err, setErr] = React.useState('')

  const onSubmit = async (e) => {
    e.preventDefault()
    setErr('')
    const u = e.currentTarget.querySelector('#u').value
    const p = e.currentTarget.querySelector('#p').value
    try {
      await api.login(u, p)
      nav('/')
    } catch (ex) {
      setErr(ex?.message || String(ex))
    }
  }

  return (
    <main className="max-w-md mx-auto mt-24 dm-card p-6">
      <h2 className="text-xl font-semibold mb-4">Logga in</h2>
      <form onSubmit={onSubmit} className="flex flex-col gap-3">
        <label className="flex flex-col gap-1">Användarnamn
          <input id="u" defaultValue="admin" className="dm-input" />
        </label>
        <label className="flex flex-col gap-1">Lösenord
          <input id="p" type="password" className="dm-input" />
        </label>
        <button type="submit" className="dm-btn self-start">Logga in</button>
        {err && <pre className="text-red-400 text-sm">{err}</pre>}
      </form>
    </main>
  )
}
