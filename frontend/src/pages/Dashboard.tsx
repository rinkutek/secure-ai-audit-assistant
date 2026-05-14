import React, { useState, useEffect, useRef } from 'react'
import { apiQuery, apiUploadDocument, apiQueryHistory, apiGetChatSession, apiRenameSession, apiDeleteSession } from '../api'
import { getAccessToken, getUserRoles } from '../auth'

export default function Dashboard() {
  const [query, setQuery] = useState('')
  const [sessions, setSessions] = useState<any[]>([])
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<any[]>([])
  const [debug, setDebug] = useState<any | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const roles = getUserRoles()
  const isAdmin = roles.includes('admin')

  const [uploadFile, setUploadFile] = useState<File | null>(null)
  const [uploadTitle, setUploadTitle] = useState('')
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [uploadBusy, setUploadBusy] = useState(false)
  const [uploadedDocId, setUploadedDocId] = useState<string | null>(null)

  async function loadSessions() {
    try {
      const token = getAccessToken()
      if (token) setSessions(await apiQueryHistory(token))
    } catch (e) { console.error(e) }
  }

  useEffect(() => { loadSessions() }, [])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function selectSession(id: string) {
    setActiveSessionId(id)
    setMessages([])
    setDebug(null)
    setError(null)
    try {
      const token = getAccessToken()
      if (token) {
        const sess = await apiGetChatSession(token, id)
        setMessages(sess.messages)
      }
    } catch (e) { console.error(e) }
  }

  async function renameSession(id: string, currentTitle: string) {
    const newTitle = prompt('Enter new session name:', currentTitle)
    if (!newTitle || newTitle === currentTitle) return
    try {
      const token = getAccessToken()
      if (!token) return
      await apiRenameSession(token, id, newTitle)
      loadSessions()
    } catch (e) { console.error(e) }
  }

  async function deleteSession(id: string) {
    if (!confirm('Are you sure you want to delete this session?')) return
    try {
      const token = getAccessToken()
      if (!token) return
      await apiDeleteSession(token, id)
      if (activeSessionId === id) {
        setActiveSessionId(null)
        setMessages([])
      }
      loadSessions()
    } catch (e) { console.error(e) }
  }

  async function handleUpload(e: React.FormEvent) {
    e.preventDefault()
    if (!uploadFile) return
    setUploadBusy(true); setUploadError(null); setUploadedDocId(null)
    try {
      const token = getAccessToken()
      if (!token) throw new Error('Please login first.')
      const res = await apiUploadDocument(token, uploadFile, uploadTitle || uploadFile.name)
      setUploadedDocId(res.doc_id)
      setUploadFile(null); setUploadTitle('')
      const fileInput = document.getElementById('file-upload') as HTMLInputElement
      if (fileInput) fileInput.value = ''
    } catch (e: any) { setUploadError(e.message || 'Upload failed') }
    finally { setUploadBusy(false) }
  }

  async function sendQuery() {
    if (!query.trim() || busy) return
    const q = query
    setQuery('')
    setMessages(prev => [...prev, { role: 'user', content: q }])
    setBusy(true); setError(null); setDebug(null);
    try {
      const token = getAccessToken()
      if (!token) throw new Error('Please login first.')
      const res = await apiQuery(token, q, activeSessionId || undefined)
      if (!activeSessionId) {
        setActiveSessionId(res.session_id)
        loadSessions()
      }
      setMessages(prev => [...prev, { role: 'assistant', content: res.answer, citations: res.citations }])
      setDebug(res.debug || null)
    } catch (e: any) { setError(e.message || 'Query failed') }
    finally { setBusy(false) }
  }

  return (
    <div style={{ display: 'flex', gap: 24, height: 'calc(100vh - 140px)', alignItems: 'stretch' }}>
      {/* Left Sidebar */}
      <div style={{ width: 280, display: 'flex', flexDirection: 'column', gap: 16, overflowY: 'auto' }}>
        <button className="btn primary" onClick={() => { setActiveSessionId(null); setMessages([]); setDebug(null); setError(null) }} style={{ padding: '12px', justifyContent: 'center', fontWeight: 600 }}>
          + New Secure Chat
        </button>

        <div className="card" style={{ flex: 1, overflowY: 'auto', padding: 12, display: 'flex', flexDirection: 'column', gap: 8 }}>
          <h4 style={{ margin: '0 0 8px 4px', color: 'var(--text-muted)' }}>Recent Sessions</h4>
          {sessions.length === 0 && <div className="small" style={{ opacity: 0.5, textAlign: 'center', marginTop: 20 }}>No past sessions.</div>}
          {sessions.map(s => (
            <div key={s.id} className="session-item" style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 12px', borderRadius: 8, cursor: 'pointer',
              background: s.id === activeSessionId ? 'rgba(16, 185, 129, 0.15)' : 'transparent',
              color: s.id === activeSessionId ? 'var(--success)' : 'var(--text-main)',
              fontWeight: s.id === activeSessionId ? 600 : 400,
              borderLeft: s.id === activeSessionId ? '3px solid var(--success)' : '3px solid transparent'
            }} onClick={() => selectSession(s.id)}>
              <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1 }}>{s.title}</span>
              <div className="session-actions" style={{ display: 'flex', gap: 6, marginLeft: 8 }}>
                <button className="btn secondary" onClick={(e) => { e.stopPropagation(); renameSession(s.id, s.title) }} style={{ padding: 4, background: 'transparent', border: 'none', color: 'var(--text-muted)' }} title="Rename">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 20h9"></path><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path></svg>
                </button>
                <button className="btn secondary" onClick={(e) => { e.stopPropagation(); deleteSession(s.id) }} style={{ padding: 4, background: 'transparent', border: 'none', color: 'var(--danger)' }} title="Delete">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
                </button>
              </div>
            </div>
          ))}
        </div>

        {isAdmin && (
          <div className="card" style={{ padding: 16, borderLeft: '4px solid var(--accent)', background: 'linear-gradient(to right, rgba(139, 92, 246, 0.05), transparent)' }}>
            <h5 style={{ marginTop: 0, marginBottom: 12, display: 'flex', alignItems: 'center', gap: 6 }}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="17 8 12 3 7 8"></polyline><line x1="12" y1="3" x2="12" y2="15"></line></svg>
              Upload to Vault
            </h5>
            <form onSubmit={handleUpload} style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <input className="input" type="file" id="file-upload" onChange={e => setUploadFile(e.target.files?.[0] || null)} required style={{ padding: '6px' }} />
              <button className="btn primary" disabled={uploadBusy || !uploadFile} type="submit" style={{ padding: '6px' }}>
                {uploadBusy ? 'Encrypting...' : 'Upload'}
              </button>
            </form>
            {uploadError && <div className="small" style={{ color: 'var(--danger)', marginTop: 8 }}>{uploadError}</div>}
            {uploadedDocId && (
              <div className="small" style={{ color: 'var(--success)', marginTop: 8, fontWeight: 500, display: 'flex', alignItems: 'center', gap: 6 }}>
                <span>Success! ID: <code>{uploadedDocId.substring(0,8)}...</code></span>
                <button className="btn secondary" onClick={() => navigator.clipboard.writeText(uploadedDocId)} style={{ padding: 4, background: 'transparent', border: 'none', color: 'var(--success)', cursor: 'pointer' }} title="Copy Full ID">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Main Chat Area */}
      <div className="card" style={{ flex: 1, display: 'flex', flexDirection: 'column', padding: 0, overflow: 'hidden' }}>
        <div style={{ flex: 1, overflowY: 'auto', padding: 24, display: 'flex', flexDirection: 'column', gap: 24 }}>
          {messages.length === 0 ? (
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', opacity: 0.5 }}>
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round" style={{ marginBottom: 16 }}><circle cx="12" cy="12" r="10"></circle><path d="M12 16v-4"></path><path d="M12 8h.01"></path></svg>
              <h3>Secure AI Audit Assistant</h3>
              <p>Start a conversation to search across your authorized security policies and logs.</p>
            </div>
          ) : (
            messages.map((m, i) => (
              <div key={i} style={{ display: 'flex', flexDirection: 'column', alignItems: m.role === 'user' ? 'flex-end' : 'flex-start' }}>
                <div style={{
                  maxWidth: '80%', padding: '12px 16px', borderRadius: 12,
                  background: m.role === 'user' ? 'var(--primary)' : 'rgba(0,0,0,0.2)',
                  color: m.role === 'user' ? '#fff' : 'var(--text-main)',
                  border: m.role === 'assistant' ? '1px solid var(--border-subtle)' : 'none',
                  whiteSpace: 'pre-wrap', lineHeight: 1.6
                }}>
                  {m.content}
                </div>
                {m.role === 'assistant' && m.citations && m.citations.length > 0 && (
                  <div style={{ marginTop: 8, padding: '8px 12px', background: 'rgba(16, 185, 129, 0.05)', border: '1px solid var(--success)', borderRadius: 8, maxWidth: '80%', fontSize: 13 }}>
                    <div style={{ fontWeight: 600, color: 'var(--success)', marginBottom: 4 }}>Cryptographic Citations:</div>
                    {m.citations.map((c: any, j: number) => (
                      <div key={j} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <span style={{ fontWeight: 500, color: 'var(--text-main)' }}>
                          {c.title && c.title !== 'Untitled' ? c.title : (c.filename || 'Unknown Document')}
                        </span>
                        <code style={{ opacity: 0.7, fontSize: '0.9em' }}>({c.doc_id.substring(0,8)})</code>
                        
                        {c.filename && (
                          <a href="#" onClick={async (e) => {
                            e.preventDefault()
                            try {
                              const token = getAccessToken()
                              if (!token) return
                              const { apiDownloadDocument } = await import('../api')
                              await apiDownloadDocument(token, c.doc_id, c.filename)
                            } catch (err: any) { alert(err.message || 'Download failed') }
                          }} style={{ textDecoration: 'none', color: 'var(--primary)', display: 'flex', alignItems: 'center', marginLeft: 4 }} title="Download Document">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
                          </a>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))
          )}
          {busy && (
            <div style={{ display: 'flex', alignItems: 'flex-start' }}>
              <div style={{ padding: '12px 16px', borderRadius: 12, background: 'rgba(0,0,0,0.2)', border: '1px solid var(--border-subtle)' }}>
                <div style={{ width: 16, height: 16, border: '2px solid var(--primary)', borderTopColor: 'transparent', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div style={{ padding: '16px 24px', borderTop: '1px solid var(--border-main)', background: 'var(--bg-card)' }}>
          {error && <div className="small" style={{ color: 'var(--danger)', marginBottom: 12 }}>{error}</div>}
          {debug && (
            <div className="small" style={{ display: 'flex', gap: 16, background: 'rgba(0,0,0,0.3)', padding: '6px 12px', borderRadius: 6, marginBottom: 12 }}>
              <span><span style={{ color: 'var(--text-muted)' }}>Vector Hits:</span> {debug.retrieved_total}</span>
              <span><span style={{ color: 'var(--text-muted)' }}>RBAC Authorized:</span> <span style={{ color: 'var(--success)', fontWeight: 600 }}>{debug.authorized_total}</span></span>
            </div>
          )}
          <div style={{ display: 'flex', gap: 12 }}>
            <textarea
              className="input"
              style={{ flex: 1, minHeight: 60, resize: 'none', lineHeight: 1.5 }}
              placeholder="Ask a question..."
              value={query}
              onChange={e => setQuery(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  sendQuery()
                }
              }}
            />
            <button className="btn primary" disabled={busy || !query.trim()} onClick={sendQuery} style={{ alignSelf: 'flex-end', height: 44, width: 44, padding: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', borderRadius: '50%' }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
