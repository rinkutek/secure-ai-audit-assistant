const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080'
export type Tokens = { access_token: string; refresh_token: string; token_type: string }

export async function apiLogin(email: string, password: string): Promise<Tokens> {
  const r = await fetch(`${API_BASE}/auth/login`, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({email,password}) })
  if (!r.ok) throw new Error((await r.json()).detail || 'Login failed')
  return r.json()
}

export async function apiQuery(accessToken: string, query: string) {
  const r = await fetch(`${API_BASE}/query`, { method:'POST', headers:{'Content-Type':'application/json', Authorization:`Bearer ${accessToken}`}, body: JSON.stringify({query}) })
  if (!r.ok) throw new Error((await r.json()).detail || 'Query failed')
  return r.json()
}

export async function apiAuditLogs(accessToken: string) {
  const r = await fetch(`${API_BASE}/audit-logs`, { headers:{Authorization:`Bearer ${accessToken}`}})
  if (!r.ok) throw new Error((await r.json()).detail || 'Failed logs')
  return r.json()
}

export async function apiVerifyAudit(accessToken: string) {
  const r = await fetch(`${API_BASE}/audit-logs/verify`, { method:'POST', headers:{Authorization:`Bearer ${accessToken}`}})
  if (!r.ok) throw new Error((await r.json()).detail || 'Verify failed')
  return r.json()
}

export async function apiUsers(accessToken: string) {
  const r = await fetch(`${API_BASE}/admin/users`, { headers:{Authorization:`Bearer ${accessToken}`}})
  if (!r.ok) throw new Error((await r.json()).detail || 'Users failed')
  return r.json()
}

export async function apiPolicies(accessToken: string) {
  const r = await fetch(`${API_BASE}/admin/policies`, { headers:{Authorization:`Bearer ${accessToken}`}})
  if (!r.ok) throw new Error((await r.json()).detail || 'Policies failed')
  return r.json()
}

export async function apiUploadDocument(accessToken: string, file: File, title: string) {
  const fd = new FormData()
  fd.append('file', file)
  fd.append('title', title)
  const r = await fetch(`${API_BASE}/documents/upload`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${accessToken}` },
    body: fd
  })
  if (!r.ok) throw new Error((await r.json()).detail || 'Upload failed')
  return r.json()
}
