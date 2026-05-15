import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiLogin } from '../api'
import { setTokens } from '../auth'

export default function Login() {
  const nav = useNavigate()
  const [email, setEmail] = useState('admin@example.com')
  const [password, setPassword] = useState('AdminPass123!')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  return (
    <div style={{ minHeight: '70vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div className="card" style={{ width: '100%', maxWidth: 440, padding: 40, borderTop: '4px solid var(--primary)', background: 'linear-gradient(to bottom, rgba(59, 130, 246, 0.05), transparent)' }}>
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <div style={{ width: 48, height: 48, borderRadius: 12, background: 'linear-gradient(135deg, #3b82f6, #8b5cf6)', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 0 20px rgba(59, 130, 246, 0.4)', marginBottom: 16 }}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>
          </div>
          <h2 style={{ margin: 0, fontSize: 28, letterSpacing: '-0.02em', background: 'var(--text-main)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>Welcome Back</h2>
          <div className="small" style={{ color: 'var(--text-muted)', marginTop: 8 }}>Authenticate to access the secure vault.</div>
        </div>

        <form onSubmit={async (e) => {
          e.preventDefault()
          setBusy(true); setError(null)
          try {
            const t = await apiLogin(email, password)
            setTokens(t.access_token, t.refresh_token)
            nav('/dashboard')
          } catch (e: any) { setError(e.message || 'Login failed') }
          finally { setBusy(false) }
        }}>
          <div style={{ display: 'grid', gap: 16 }}>
            <div>
              <label className="small" style={{ color: 'var(--text-muted)', display: 'block', marginBottom: 6, fontWeight: 500 }}>Corporate Email</label>
              <input className="input" style={{ width: '100%' }} value={email} onChange={e => setEmail(e.target.value)} placeholder="name@example.com" required />
            </div>
            <div>
              <label className="small" style={{ color: 'var(--text-muted)', display: 'block', marginBottom: 6, fontWeight: 500 }}>Password</label>
              <input className="input" style={{ width: '100%' }} value={password} onChange={e => setPassword(e.target.value)} placeholder="••••••••" type="password" required />
            </div>

            {error && <div className="small" style={{ color: 'var(--danger)', padding: '8px 12px', background: 'rgba(239, 68, 68, 0.1)', borderRadius: 6, textAlign: 'center' }}>{error}</div>}

            <button className="btn primary" disabled={busy} type="submit" style={{ marginTop: 8, height: 44, fontSize: 16, display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
              {busy ? (
                <div style={{ width: 18, height: 18, border: '2px solid white', borderTopColor: 'transparent', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
              ) : 'Authenticate Access'}
            </button>
          </div>
        </form>

        <div className="small" style={{ textAlign: 'center', marginTop: 24, color: 'var(--text-muted)', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>
          Restricted to authorized personnel only.
        </div>
      </div>
    </div>
  )
}
