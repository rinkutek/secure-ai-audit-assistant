import React, { useEffect, useState } from 'react'
import { apiUsers, apiPolicies, apiUploadDocument } from '../api'
import { getAccessToken } from '../auth'

export default function Admin() {
  const [users, setUsers] = useState<any[]>([])
  const [policies, setPolicies] = useState<any[]>([])
  const [error, setError] = useState<string | null>(null)
  const [uploadBusy, setUploadBusy] = useState(false)
  const [uploadTitle, setUploadTitle] = useState('')
  const [uploadFile, setUploadFile] = useState<File | null>(null)

  async function load() {
    setError(null)
    try {
      const token = getAccessToken()
      if (!token) throw new Error('Please login first.')
      const [u, p] = await Promise.all([apiUsers(token), apiPolicies(token)])
      setUsers(u); setPolicies(p)
    } catch (e:any) { setError(e.message || 'Failed') }
  }

  async function handleUpload(e: React.FormEvent) {
    e.preventDefault()
    if (!uploadFile) return
    setUploadBusy(true); setError(null)
    try {
      const token = getAccessToken()
      if (!token) throw new Error('Please login first.')
      await apiUploadDocument(token, uploadFile, uploadTitle || uploadFile.name)
      setUploadTitle(''); setUploadFile(null)
      alert('Upload successful!')
      load()
    } catch (e:any) { setError(e.message || 'Upload failed') }
    finally { setUploadBusy(false) }
  }

  useEffect(() => { load() }, [])

  return (
    <div style={{display:'grid', gap: 12}}>
      <div className="card">
        <div className="row" style={{justifyContent:'space-between'}}>
          <h3 style={{marginTop:0}}>Admin</h3>
          <button className="btn secondary" onClick={load}>Refresh</button>
        </div>
        {error && <div className="small" style={{color:'crimson'}}>{error}</div>}
        <div className="small">Manage users, policies, and documents.</div>
      </div>

      <div className="card">
        <h4 style={{marginTop:0}}>Upload Document</h4>
        <form onSubmit={handleUpload} style={{display:'grid', gap:8}}>
          <input className="input" placeholder="Document Title" value={uploadTitle} onChange={e => setUploadTitle(e.target.value)} />
          <input type="file" onChange={e => setUploadFile(e.target.files?.[0] || null)} />
          <button className="btn" type="submit" disabled={uploadBusy || !uploadFile}>
            {uploadBusy ? 'Uploading...' : 'Upload'}
          </button>
        </form>
      </div>

      <div className="card">
        <h4 style={{marginTop:0}}>Users</h4>
        <table className="table">
          <thead><tr><th>Email</th><th>Roles</th><th>Active</th><th>ID</th></tr></thead>
          <tbody>
            {users.map((u:any) => (
              <tr key={u.id}>
                <td>{u.email}</td>
                <td><span className="small">{(u.roles||[]).join(', ')}</span></td>
                <td>{u.is_active ? 'yes' : 'no'}</td>
                <td><span className="small"><code>{u.id}</code></span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card">
        <h4 style={{marginTop:0}}>Policies</h4>
        <table className="table">
          <thead><tr><th>Role</th><th>Doc</th><th>Perm</th><th>ID</th></tr></thead>
          <tbody>
            {policies.map((p:any) => (
              <tr key={p.id}>
                <td>{p.role_name}</td>
                <td><span className="small"><code>{p.doc_id}</code></span></td>
                <td><span className="badge">{p.permission}</span></td>
                <td><span className="small"><code>{p.id}</code></span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
