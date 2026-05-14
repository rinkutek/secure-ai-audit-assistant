/// <reference types="vite/client" />
const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080'
export type Tokens = { access_token: string; refresh_token: string; token_type: string }

function parseError(data: any, fallback: string) {
  if (data?.detail) {
    if (typeof data.detail === 'string') return data.detail
    if (Array.isArray(data.detail)) return data.detail.map((d: any) => d.msg).join(', ')
    return JSON.stringify(data.detail)
  }
  return fallback
}

export async function apiLogin(email: string, password: string): Promise<Tokens> {
  const r = await fetch(`${API_BASE}/auth/login`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email, password }) })
  if (!r.ok) throw new Error(parseError(await r.json(), 'Login failed'))
  return r.json()
}

export async function apiQuery(accessToken: string, query: string, sessionId?: string) {
  const body: any = { query }
  if (sessionId) body.session_id = sessionId
  const r = await fetch(`${API_BASE}/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${accessToken}` },
    body: JSON.stringify(body)
  })
  if (!r.ok) throw new Error(parseError(await r.json(), 'Query failed'))
  return r.json()
}

export async function apiQueryHistory(accessToken: string) {
  const r = await fetch(`${API_BASE}/chat/sessions`, {
    headers: { Authorization: `Bearer ${accessToken}` }
  })
  if (!r.ok) throw new Error(parseError(await r.json(), 'Failed to fetch chat sessions'))
  return r.json()
}

export async function apiGetChatSession(accessToken: string, sessionId: string) {
  const r = await fetch(`${API_BASE}/chat/session/${sessionId}`, {
    headers: { Authorization: `Bearer ${accessToken}` }
  })
  if (!r.ok) throw new Error(parseError(await r.json(), 'Failed to fetch chat session'))
  return r.json()
}

export async function apiRenameSession(accessToken: string, sessionId: string, title: string) {
  const r = await fetch(`${API_BASE}/chat/session/${sessionId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${accessToken}` },
    body: JSON.stringify({ title })
  })
  if (!r.ok) throw new Error(parseError(await r.json(), 'Failed to rename session'))
  return r.json()
}

export async function apiDeleteSession(accessToken: string, sessionId: string) {
  const r = await fetch(`${API_BASE}/chat/session/${sessionId}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${accessToken}` }
  })
  if (!r.ok) throw new Error(parseError(await r.json(), 'Failed to delete session'))
  return r.json()
}

export async function apiAuditLogs(accessToken: string) {
  const r = await fetch(`${API_BASE}/audit-logs`, { headers: { Authorization: `Bearer ${accessToken}` } })
  if (!r.ok) throw new Error(parseError(await r.json(), 'Failed logs'))
  return r.json()
}

export async function apiVerifyAudit(accessToken: string) {
  const r = await fetch(`${API_BASE}/audit-logs/verify`, { method: 'POST', headers: { Authorization: `Bearer ${accessToken}` } })
  if (!r.ok) throw new Error(parseError(await r.json(), 'Verify failed'))
  return r.json()
}

export async function apiFlushAuditLogs(accessToken: string) {
  const r = await fetch(`${API_BASE}/audit-logs/flush`, { method: 'DELETE', headers: { Authorization: `Bearer ${accessToken}` } })
  if (!r.ok) throw new Error(parseError(await r.json(), 'Flush failed'))
  return r.json()
}

export async function apiExportAuditLogs(accessToken: string, format: 'csv' | 'json' = 'csv') {
  const r = await fetch(`${API_BASE}/audit-logs/export?format=${format}`, {
    method: 'GET',
    headers: { Authorization: `Bearer ${accessToken}` }
  })
  if (!r.ok) throw new Error('Failed to export logs')
  
  const blob = await r.blob()
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `audit-logs-export.${format}`
  document.body.appendChild(a)
  a.click()
  window.URL.revokeObjectURL(url)
  document.body.removeChild(a)
}

export async function apiUsers(accessToken: string) {
  const r = await fetch(`${API_BASE}/admin/users`, { headers: { Authorization: `Bearer ${accessToken}` } })
  if (!r.ok) throw new Error(parseError(await r.json(), 'Users failed'))
  return r.json()
}

export async function apiPolicies(accessToken: string) {
  const r = await fetch(`${API_BASE}/admin/policies`, { headers: { Authorization: `Bearer ${accessToken}` } })
  if (!r.ok) throw new Error(parseError(await r.json(), 'Policies failed'))
  return r.json()
}

export async function apiGraph(accessToken: string) {
  const r = await fetch(`${API_BASE}/admin/graph`, { headers: { Authorization: `Bearer ${accessToken}` } })
  if (!r.ok) throw new Error(parseError(await r.json(), 'Graph failed'))
  return r.json()
}

export async function apiCreateUser(accessToken: string, email: string, password: string, roles: string[]) {
  const r = await fetch(`${API_BASE}/admin/users`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${accessToken}` },
    body: JSON.stringify({ email, password, roles })
  })
  if (!r.ok) throw new Error(parseError(await r.json(), 'Failed to create user'))
  return r.json()
}

export async function apiUpdateUserRoles(accessToken: string, userId: string, roles: string[]) {
  const r = await fetch(`${API_BASE}/admin/users/${userId}/roles`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${accessToken}` },
    body: JSON.stringify({ roles })
  })
  if (!r.ok) throw new Error(parseError(await r.json(), 'Failed to update user roles'))
  return r.json()
}

export async function apiDeleteUser(accessToken: string, userId: string) {
  const r = await fetch(`${API_BASE}/admin/users/${userId}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${accessToken}` }
  })
  if (!r.ok) throw new Error(parseError(await r.json(), 'Failed to delete user'))
  return r.json()
}

export async function apiCreateRole(accessToken: string, name: string) {
  const r = await fetch(`${API_BASE}/admin/roles`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${accessToken}` },
    body: JSON.stringify({ name })
  })
  if (!r.ok) throw new Error(parseError(await r.json(), 'Failed to create role'))
  return r.json()
}

export async function apiCreatePolicy(accessToken: string, role_name: string, doc_id: string, permission: string) {
  const r = await fetch(`${API_BASE}/admin/policies`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${accessToken}` },
    body: JSON.stringify({ role_name, doc_id, permission })
  })
  if (!r.ok) throw new Error(parseError(await r.json(), 'Failed to create policy'))
  return r.json()
}

export async function apiUploadDocument(accessToken: string, file: File, title: string) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('title', title)

  const r = await fetch(`${API_BASE}/documents/upload`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${accessToken}` },
    body: formData
  })
  if (!r.ok) throw new Error(parseError(await r.json(), 'Failed to upload document'))
  return r.json()
}

export async function apiDownloadDocument(accessToken: string, doc_id: string, filename: string) {
  const r = await fetch(`${API_BASE}/documents/${doc_id}/download`, {
    method: 'GET',
    headers: { Authorization: `Bearer ${accessToken}` }
  })
  if (!r.ok) {
    let msg = 'Failed to download document'
    try { msg = parseError(await r.json(), msg) } catch (e) { }
    throw new Error(msg)
  }
  const blob = await r.blob()
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  window.URL.revokeObjectURL(url)
  document.body.removeChild(a)
}

export async function apiDeleteDocument(accessToken: string, doc_id: string) {
  const r = await fetch(`${API_BASE}/documents/${doc_id}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${accessToken}` }
  })
  if (!r.ok) {
    let msg = 'Failed to delete document'
    try { msg = parseError(await r.json(), msg) } catch (e) { }
    throw new Error(msg)
  }
  return r.json()
}

export async function apiDocuments(accessToken: string) {
  const r = await fetch(`${API_BASE}/documents`, { headers: { Authorization: `Bearer ${accessToken}` } })
  if (!r.ok) throw new Error(parseError(await r.json(), 'Documents failed'))
  return r.json()
}

export async function apiTogglePolicy(accessToken: string, policy_id: string) {
  const r = await fetch(`${API_BASE}/admin/policies/${policy_id}/toggle`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${accessToken}` }
  })
  if (!r.ok) throw new Error(parseError(await r.json(), 'Failed to toggle policy'))
  return r.json()
}
