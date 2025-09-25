import React from 'react'
import { useNavigate } from 'react-router-dom'
import { FiLogIn } from 'react-icons/fi'
import { api } from '../api'

export default function Login() {
  const nav = useNavigate()
  const [err, setErr] = React.useState('')
  const [loading, setLoading] = React.useState(false)

  const onSubmit = async (e) => {
    e.preventDefault()
    setErr('')
    setLoading(true)

    const form = e.currentTarget
    const username = form.querySelector('#login-username').value
    const password = form.querySelector('#login-password').value

    try {
      await api.login(username, password)
      nav('/')
    } catch (ex) {
      setErr(ex?.message || String(ex))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex items-center justify-center" style={{ minHeight: '100vh', background: 'var(--bg-primary)' }}>
      <div className="card" style={{ width: '100%', maxWidth: '420px' }}>
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-lg bg-red-600 flex items-center justify-center font-bold text-white text-lg">
            M
          </div>
          <div>
            <h1 className="text-xl font-semibold text-white">Mind Admin</h1>
            <h2 className="text-lg text-gray-200">Logga in</h2>
            <p className="text-sm text-gray-400">Logga in för att hantera kvitton och systemstatus.</p>
          </div>
        </div>

        <form onSubmit={onSubmit} className="space-y-4">
          <label className="flex flex-col gap-2 text-sm text-gray-300">
            Användarnamn
            <input id="login-username" defaultValue="admin" placeholder="Ange användarnamn" />
          </label>
          <label className="flex flex-col gap-2 text-sm text-gray-300">
            Lösenord
            <input id="login-password" type="password" placeholder="Ange lösenord" />
          </label>
          <button type="submit" className="btn btn-primary w-full" disabled={loading}>
            {loading ? (
              <>
                <div className="loading-spinner mr-2"></div>
                Loggar in...
              </>
            ) : (
              <>
                <FiLogIn className="mr-2" />
                Logga in
              </>
            )}
          </button>
          {err && (
            <div className="p-3 rounded-lg border border-red-700 bg-red-900 text-red-200 text-sm">
              {err}
            </div>
          )}
        </form>
      </div>
    </div>
  )
}
