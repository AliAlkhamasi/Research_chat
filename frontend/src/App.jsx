import React, { useState, useEffect, useRef } from 'react'
import Hero from './components/Hero.jsx'
import ChatDrawer from './components/ChatDrawer.jsx'

const LS_SESSION_KEY = 'research_chat_session_id'

export default function App() {
  const [sessionId, setSessionId] = useState(null)
  const [docs, setDocs]           = useState([])
  const [uploading, setUploading] = useState(false)
  const [uploadMsg, setUploadMsg] = useState(null)
  const [chatOpen, setChatOpen]   = useState(false)
  const fileRef = useRef(null)

  // Always create a fresh session on mount
  useEffect(() => {
    async function initSession() {
      // Clean up old session if one exists
      const oldSession = localStorage.getItem(LS_SESSION_KEY)
      if (oldSession) {
        localStorage.removeItem(`chat:${oldSession}`)
        fetch(`/session/${oldSession}/cleanup`, { method: 'POST' }).catch(() => {})
      }
      try {
        const res = await fetch('/session', { method: 'POST' })
        const data = await res.json()
        localStorage.setItem(LS_SESSION_KEY, data.session_id)
        setSessionId(data.session_id)
        setDocs([])
      } catch {}
    }
    initSession()
  }, [])

  // Cleanup session on tab close
  useEffect(() => {
    function cleanup() {
      if (sessionId) {
        localStorage.removeItem(`chat:${sessionId}`)
        navigator.sendBeacon(`/session/${sessionId}/cleanup`)
      }
    }
    window.addEventListener('beforeunload', cleanup)
    return () => window.removeEventListener('beforeunload', cleanup)
  }, [sessionId])

  async function fetchDocs() {
    if (!sessionId) return
    try {
      const res = await fetch(`/session/${sessionId}/documents`)
      setDocs(await res.json())
    } catch {}
  }

  async function handleUpload(e) {
    const file = e.target.files[0]
    if (!file || !sessionId) return
    setUploading(true)
    setUploadMsg(null)
    const form = new FormData()
    form.append('file', file)
    try {
      const res  = await fetch(`/session/${sessionId}/documents/upload`, { method: 'POST', body: form })
      const data = await res.json()
      if (!res.ok) {
        setUploadMsg({ ok: false, text: data.detail || 'Upload failed' })
      } else {
        setUploadMsg({ ok: true, text: `${data.filename} — ${data.n_chunks} chunks` })
        await fetchDocs()
      }
    } catch (err) {
      setUploadMsg({ ok: false, text: err.message })
    } finally {
      setUploading(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  async function handleDelete(id) {
    if (!sessionId) return
    await fetch(`/session/${sessionId}/documents/${id}`, { method: 'DELETE' })
    fetchDocs()
  }

  return (
    <>
      <Hero
        docs={docs}
        uploading={uploading}
        uploadMsg={uploadMsg}
        fileRef={fileRef}
        onUpload={handleUpload}
        onDelete={handleDelete}
      />

      {/* Floating chat button */}
      <button
        onClick={() => setChatOpen(true)}
        className={docs.length > 0 ? 'pulse' : ''}
        style={{
          position: 'fixed', bottom: 32, right: 32,
          display: 'flex', alignItems: 'center', gap: 8,
          padding: '14px 24px',
          background: 'var(--text)', color: '#fff',
          border: 'none', borderRadius: 999,
          fontSize: 14, fontWeight: 500, letterSpacing: '0.01em',
          cursor: 'pointer', zIndex: 100,
          transition: 'transform 0.15s, opacity 0.15s',
        }}
        onMouseEnter={e => e.currentTarget.style.transform = 'scale(1.04)'}
        onMouseLeave={e => e.currentTarget.style.transform = 'scale(1)'}
      >
        <span style={{ fontSize: 12 }}>◆</span> Ask
      </button>

      <ChatDrawer open={chatOpen} onClose={() => setChatOpen(false)} sessionId={sessionId} />
    </>
  )
}