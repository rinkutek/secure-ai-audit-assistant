import React, { useEffect, useState } from 'react'
import { apiAuditLogs, apiVerifyAudit, apiExportAuditLogs } from '../api'
import { getAccessToken, getUserRoles } from '../auth'

export default function AuditLogs() {
  const [rows, setRows] = useState<any[]>([])
  const [verify, setVerify] = useState<any | null>(null)
  const [error, setError] = useState<string | null>(null)
  
  const roles = getUserRoles()
  const isAdmin = roles.includes('admin')

  async function load() {
    setError(null)
    try {
      const token = getAccessToken()
      if (!token) throw new Error('Please login first.')
      setRows(await apiAuditLogs(token))
    } catch (e: any) { setError(e.message || 'Failed') }
  }

  useEffect(() => { load() }, [])

  return (
    <div className="card" style={{ borderTop: '4px solid var(--success)', background: 'linear-gradient(to bottom, rgba(16, 185, 129, 0.05), transparent)' }}>
      <div className="row" style={{ justifyContent: 'space-between', marginBottom: 16 }}>
        <div>
          <h3 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: 8 }}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--success)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>
            Immutable Audit Ledger
          </h3>
          <div className="small" style={{ color: 'var(--text-muted)', marginTop: 8 }}>Cryptographically enforced record of all security events and access logs.</div>
        </div>
        <div className="row" style={{ gap: 12 }}>
          <button className="btn secondary" onClick={load} style={{ fontSize: 13 }}>Sync Logs</button>
          {isAdmin && (
            <>
              <button className="btn secondary" style={{ fontSize: 13, display: 'flex', alignItems: 'center', gap: 6 }} onClick={async () => {
                setError(null)
                try {
                  const token = getAccessToken()
                  if (!token) return
                  await apiExportAuditLogs(token, 'csv')
                } catch (e: any) { setError(e.message || 'Export failed') }
              }}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
                Export CSV
              </button>
              <button className="btn primary" style={{ background: 'linear-gradient(135deg, var(--success), #059669)', fontSize: 13, display: 'flex', alignItems: 'center', gap: 6 }} onClick={async () => {
                setError(null)
                try {
                  const token = getAccessToken()
                  if (!token) throw new Error('Please login first.')
                  setVerify(await apiVerifyAudit(token))
                } catch (e: any) { setError(e.message || 'Verify failed') }
              }}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
                Verify Chain Integrity
              </button>
              <button className="btn primary" style={{ background: 'linear-gradient(135deg, var(--danger), #991b1b)', fontSize: 13, display: 'flex', alignItems: 'center', gap: 6, borderColor: 'transparent' }} onClick={async () => {
                const conf = confirm('WARNING: You are about to cryptographically shred the entire audit ledger. A new Genesis Block will be created recording this action. Proceed?')
                if (!conf) return
                setError(null)
                setVerify(null)
                try {
                  const token = getAccessToken()
                  if (!token) return
                  const { apiFlushAuditLogs } = await import('../api')
                  const res = await apiFlushAuditLogs(token)
                  alert(res.message)
                  load()
                } catch (e: any) { setError(e.message || 'Flush failed') }
              }}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path><line x1="10" y1="11" x2="10" y2="17"></line><line x1="14" y1="11" x2="14" y2="17"></line></svg>
                Shred Ledger
              </button>
            </>
          )}
        </div>
      </div>

      {verify && (
        <div style={{ padding: '12px 16px', background: verify.ok ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)', borderRadius: 8, border: `1px solid ${verify.ok ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)'}`, marginBottom: 20, display: 'flex', alignItems: 'center', gap: 8 }}>
          {verify.ok ? (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--success)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
          ) : (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--danger)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
          )}
          <span style={{ color: verify.ok ? 'var(--success)' : 'var(--danger)', fontWeight: 500 }}>
            Cryptographic Verification: {verify.ok ? 'PASSED' : 'FAILED'} (Blocks Checked: {verify.checked})
            {!verify.ok && <> • Mismatch detected at Block #{verify.mismatch_at_log_id} ({verify.reason})</>}
          </span>
        </div>
      )}

      {error && <div className="small" style={{ color: 'var(--danger)', marginBottom: 20, padding: '8px 12px', background: 'rgba(239, 68, 68, 0.1)', borderRadius: 6 }}>{error}</div>}

      <div style={{ overflowX: 'auto' }}>
        <table className="table" style={{ fontSize: 13 }}>
          <thead><tr><th>Seq</th><th>UTC Timestamp</th><th>Identity / User</th><th>Protocol Action</th><th>Status</th><th>Resources Accessed</th><th>SHA-256 Chain Hashes</th></tr></thead>
          <tbody>
            {rows.map((r: any) => (
              <tr key={r.log_id}>
                <td style={{ color: 'var(--text-muted)' }}>#{r.log_id}</td>
                <td style={{ color: 'var(--text-main)', whiteSpace: 'nowrap' }}>{new Date(r.timestamp_utc).toLocaleString()}</td>
                <td style={{ fontWeight: 500, color: 'var(--primary)' }}>{r.user_id}</td>
                <td><code>{r.action}</code></td>
                <td>
                  <span className="badge" style={{
                    background: r.outcome === 'ALLOW' ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                    color: r.outcome === 'ALLOW' ? 'var(--success)' : 'var(--danger)',
                    borderColor: r.outcome === 'ALLOW' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)'
                  }}>
                    {r.outcome}
                  </span>
                </td>
                <td>
                  {r.resource_ids.length === 0 ? <span style={{ color: 'var(--text-muted)' }}>None</span> : (
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                      {r.resource_ids.map((rid: string, i: number) => {
                        const name = r.resource_names?.[i]
                        const display = name && name !== rid ? `${name} (${rid.substring(0,8)})` : rid.substring(0,8)
                        return (
                          <span key={i} style={{ background: 'rgba(255,255,255,0.1)', padding: '2px 6px', borderRadius: 4, fontSize: 12 }} title={rid}>
                            {display}
                          </span>
                        )
                      })}
                    </div>
                  )}
                </td>
                <td>
                  <div style={{ display: 'grid', gap: 4, fontFamily: 'monospace', fontSize: 11, color: 'var(--text-muted)' }}>
                    <div><span style={{ color: '#64748b' }}>P:</span> {r.hash_prev.slice(0, 16)}…</div>
                    <div style={{ color: '#94a3b8' }}><span style={{ color: '#64748b' }}>C:</span> {r.hash_curr.slice(0, 16)}…</div>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {isAdmin && (
        <div className="small" style={{ marginTop: 20, color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 6 }}>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>
          Restricted to Admin personnel.
        </div>
      )}
    </div>
  )
}
