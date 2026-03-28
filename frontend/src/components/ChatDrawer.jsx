import React, { useState, useRef, useEffect } from 'react'

// ── Persistence helpers ──────────────────────────────────────────────────────

function chatKey(sessionId) { return sessionId ? `chat:${sessionId}` : null }

function loadHistory(sessionId) {
  const key = chatKey(sessionId)
  if (!key) return []
  try { return JSON.parse(localStorage.getItem(key) || '[]') }
  catch { return [] }
}

function persistHistory(sessionId, history) {
  const key = chatKey(sessionId)
  if (key) localStorage.setItem(key, JSON.stringify(history))
}

function loadSavedChats() {
  try { return JSON.parse(localStorage.getItem('saved_chats') || '[]') }
  catch { return [] }
}

function persistSavedChats(chats) {
  localStorage.setItem('saved_chats', JSON.stringify(chats))
}

// ── Small UI components ──────────────────────────────────────────────────────

const pillBtn = {
  fontSize: 11, color: 'var(--text-light)',
  background: 'none', border: '1px solid var(--border)',
  borderRadius: 999, padding: '4px 12px', cursor: 'pointer',
  transition: 'color 0.1s',
}

function SourcePills({ sources }) {
  if (!sources || sources.length === 0) return null
  return (
    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 8 }}>
      {sources.map((s, i) => (
        <span key={i} style={{
          fontSize: 11, padding: '3px 10px',
          background: 'var(--pill-bg)', borderRadius: 999,
          color: 'var(--text-muted)', border: '1px solid var(--border)',
          whiteSpace: 'nowrap',
        }}>
          {s.filename} · sida {s.page}
        </span>
      ))}
    </div>
  )
}

function Message({ msg }) {
  const isUser = msg.role === 'user'
  return (
    <div style={{
      display: 'flex', flexDirection: 'column',
      alignItems: isUser ? 'flex-end' : 'flex-start',
      marginBottom: 20,
    }}>
      <div style={{
        maxWidth: '82%', padding: '11px 15px',
        borderRadius: isUser ? '16px 16px 4px 16px' : '4px 16px 16px 16px',
        background: isUser ? 'var(--text)' : '#fff',
        color: isUser ? '#fff' : 'var(--text)',
        border: isUser ? 'none' : '1px solid var(--border)',
        fontSize: 13, lineHeight: 1.65,
        whiteSpace: 'pre-wrap', wordBreak: 'break-word',
        boxShadow: 'var(--shadow-sm)',
      }}>
        {msg.content}
      </div>
      {!isUser && <SourcePills sources={msg.sources} />}
    </div>
  )
}

// ── Saved chats panel ────────────────────────────────────────────────────────

function SavedChatsPanel({ onBack, onOpen }) {
  const [chats, setChats] = useState(loadSavedChats)

  function handleDelete(id) {
    const next = chats.filter(c => c.id !== id)
    persistSavedChats(next)
    setChats(next)
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{
        display: 'flex', alignItems: 'center', gap: 10,
        padding: '20px 24px', borderBottom: '1px solid var(--border)', flexShrink: 0,
      }}>
        <button onClick={onBack} style={{
          background: 'none', border: 'none', fontSize: 18,
          color: 'var(--text-muted)', cursor: 'pointer', lineHeight: 1, padding: 0,
        }}>
          ←
        </button>
        <div style={{ fontFamily: 'var(--font-serif)', fontSize: 18, fontWeight: 400, color: 'var(--text)' }}>
          Saved Chats
        </div>
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: '16px 24px' }}>
        {chats.length === 0 && (
          <div style={{ textAlign: 'center', padding: '48px 20px', color: 'var(--text-light)', fontSize: 13 }}>
            No saved chats yet.
          </div>
        )}
        {chats.map(chat => {
          const preview = chat.messages.find(m => m.role === 'user')?.content || '(empty)'
          return (
            <div key={chat.id} style={{
              padding: '12px 14px', marginBottom: 8,
              background: '#fff', border: '1px solid var(--border)',
              borderRadius: 10, boxShadow: 'var(--shadow-sm)',
              cursor: 'pointer', transition: 'border-color 0.1s',
            }}
              onMouseEnter={e => e.currentTarget.style.borderColor = '#a0a09c'}
              onMouseLeave={e => e.currentTarget.style.borderColor = 'var(--border)'}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', gap: 8 }}>
                <div style={{ flex: 1, minWidth: 0 }} onClick={() => onOpen(chat)}>
                  <div style={{ fontSize: 11, color: 'var(--text-light)', marginBottom: 4 }}>
                    {chat.date}
                  </div>
                  <div style={{
                    fontSize: 13, color: 'var(--text)',
                    overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                  }}>
                    {preview.slice(0, 80)}
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--text-light)', marginTop: 3 }}>
                    {chat.messages.length} messages
                  </div>
                </div>
                <button
                  onClick={e => { e.stopPropagation(); handleDelete(chat.id) }}
                  style={{
                    background: 'none', border: 'none', padding: '2px 6px',
                    fontSize: 14, color: 'var(--text-light)', cursor: 'pointer',
                    flexShrink: 0, lineHeight: 1, transition: 'color 0.1s',
                  }}
                  onMouseEnter={e => e.currentTarget.style.color = '#c0392b'}
                  onMouseLeave={e => e.currentTarget.style.color = 'var(--text-light)'}
                >
                  ×
                </button>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ── Read-only view of a saved chat ───────────────────────────────────────────

function SavedChatView({ chat, onBack }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{
        display: 'flex', alignItems: 'center', gap: 10,
        padding: '20px 24px', borderBottom: '1px solid var(--border)', flexShrink: 0,
      }}>
        <button onClick={onBack} style={{
          background: 'none', border: 'none', fontSize: 18,
          color: 'var(--text-muted)', cursor: 'pointer', lineHeight: 1, padding: 0,
        }}>
          ←
        </button>
        <div>
          <div style={{ fontFamily: 'var(--font-serif)', fontSize: 16, fontWeight: 400, color: 'var(--text)' }}>
            Saved Chat
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-light)' }}>{chat.date}</div>
        </div>
      </div>
      <div style={{ flex: 1, overflow: 'auto', padding: '24px 24px 8px' }}>
        {chat.messages.map((msg, i) => <Message key={i} msg={msg} />)}
      </div>
    </div>
  )
}

// ── Main drawer ──────────────────────────────────────────────────────────────

export default function ChatDrawer({ open, onClose, sessionId }) {
  const [history, setHistory]       = useState([])
  const [input, setInput]           = useState('')
  const [loading, setLoading]       = useState(false)
  const [saveConfirm, setSaveConfirm] = useState(false)
  const [view, setView]             = useState('chat') // 'chat' | 'list' | 'saved'
  const [viewedChat, setViewedChat] = useState(null)
  const bottomRef = useRef(null)
  const inputRef  = useRef(null)

  // Load history when sessionId changes
  useEffect(() => {
    setHistory(loadHistory(sessionId))
    setView('chat')
    setViewedChat(null)
  }, [sessionId])

  function saveHistory(h) {
    setHistory(h)
    persistHistory(sessionId, h)
  }

  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 320)
      bottomRef.current?.scrollIntoView({ behavior: 'instant' })
    }
  }, [open])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [history, loading])

  function handleSaveChat() {
    if (history.length === 0) return
    const saved = loadSavedChats()
    saved.unshift({
      id: Date.now().toString(),
      date: new Date().toLocaleString(),
      session_id: sessionId,
      messages: history,
    })
    persistSavedChats(saved)
    setSaveConfirm(true)
    setTimeout(() => setSaveConfirm(false), 2000)
  }

  async function handleSend() {
    const msg = input.trim()
    if (!msg || loading || !sessionId) return
    setInput('')

    const userMsg    = { role: 'user', content: msg }
    const apiHistory = history.map(h => ({ role: h.role, content: h.content }))
    const newHistory = [...history, userMsg]
    saveHistory(newHistory)
    setLoading(true)

    try {
      const res  = await fetch(`/session/${sessionId}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: msg, history: apiHistory }),
      })
      const data = await res.json()
      saveHistory([...newHistory, {
        role: 'assistant', content: data.response, sources: data.sources || [],
      }])
    } catch (e) {
      saveHistory([...newHistory, { role: 'assistant', content: `[Error: ${e.message}]`, sources: [] }])
    } finally {
      setLoading(false)
      inputRef.current?.focus()
    }
  }

  function handleKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() }
    if (e.key === 'Escape') onClose()
  }

  // Determine what to render inside the drawer
  function renderContent() {
    if (view === 'list') {
      return (
        <SavedChatsPanel
          onBack={() => setView('chat')}
          onOpen={chat => { setViewedChat(chat); setView('saved') }}
        />
      )
    }
    if (view === 'saved' && viewedChat) {
      return <SavedChatView chat={viewedChat} onBack={() => setView('list')} />
    }

    // Default: live chat view
    return (
      <>
        {/* Header */}
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '20px 24px', borderBottom: '1px solid var(--border)', flexShrink: 0,
        }}>
          <div>
            <div style={{ fontFamily: 'var(--font-serif)', fontSize: 18, fontWeight: 400, color: 'var(--text)' }}>
              Research Assistant
            </div>
            <div style={{ fontSize: 11, color: 'var(--text-light)', marginTop: 1 }}>
              Ask questions about your documents
            </div>
          </div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <button onClick={() => setView('list')} style={pillBtn} title="Saved chats">
              History
            </button>
            {history.length > 0 && (
              <>
                <button onClick={handleSaveChat} style={pillBtn}>
                  {saveConfirm ? '✓ Saved' : 'Save'}
                </button>
                <button onClick={() => saveHistory([])} style={pillBtn}>
                  Clear
                </button>
              </>
            )}
            <button
              onClick={onClose}
              style={{
                width: 32, height: 32, borderRadius: '50%',
                background: 'var(--pill-bg)', border: 'none',
                fontSize: 18, color: 'var(--text-muted)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                cursor: 'pointer', lineHeight: 1, transition: 'background 0.1s',
              }}
              onMouseEnter={e => e.currentTarget.style.background = 'var(--border)'}
              onMouseLeave={e => e.currentTarget.style.background = 'var(--pill-bg)'}
            >
              ×
            </button>
          </div>
        </div>

        {/* Messages */}
        <div style={{ flex: 1, overflow: 'auto', padding: '24px 24px 8px' }}>
          {history.length === 0 && (
            <div style={{ textAlign: 'center', padding: '48px 20px', color: 'var(--text-light)', fontSize: 13 }}>
              <div style={{ fontSize: 28, marginBottom: 12, fontFamily: 'var(--font-serif)', fontStyle: 'italic' }}>
                Ask anything.
              </div>
              Frågor om dina uppladdade dokument besvaras med källhänvisning.
            </div>
          )}
          {history.map((msg, i) => <Message key={i} msg={msg} />)}
          {loading && (
            <div style={{ color: 'var(--text-light)', fontSize: 12, marginBottom: 16 }}>
              <span className="spin" style={{ marginRight: 6 }}>◌</span>
              Searching documents…
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <div style={{
          padding: '12px 16px 20px', borderTop: '1px solid var(--border)',
          display: 'flex', gap: 8, alignItems: 'flex-end', flexShrink: 0,
        }}>
          <textarea
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKey}
            placeholder="Ask a question…"
            rows={2}
            style={{
              flex: 1, padding: '10px 14px',
              background: 'var(--bg)', border: '1px solid var(--border)',
              borderRadius: 12, color: 'var(--text)', fontSize: 13,
              fontFamily: 'var(--font-sans)', resize: 'none', outline: 'none', lineHeight: 1.5,
            }}
            onFocus={e => e.target.style.borderColor = '#a0a09c'}
            onBlur={e => e.target.style.borderColor = 'var(--border)'}
          />
          <button
            onClick={handleSend}
            disabled={loading || !input.trim()}
            style={{
              width: 40, height: 40, borderRadius: '50%', flexShrink: 0,
              background: loading || !input.trim() ? 'var(--pill-bg)' : 'var(--text)',
              color: loading || !input.trim() ? 'var(--text-light)' : '#fff',
              border: 'none', fontSize: 16,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              cursor: loading || !input.trim() ? 'not-allowed' : 'pointer',
              transition: 'background 0.15s', lineHeight: 1,
            }}
          >
            {loading ? <span className="spin" style={{ fontSize: 13 }}>◌</span> : '↑'}
          </button>
        </div>
      </>
    )
  }

  return (
    <>
      {/* Backdrop */}
      <div
        onClick={onClose}
        style={{
          position: 'fixed', inset: 0, zIndex: 200,
          background: 'rgba(0,0,0,0.18)',
          opacity: open ? 1 : 0,
          pointerEvents: open ? 'auto' : 'none',
          transition: 'opacity 0.3s ease',
        }}
      />

      {/* Drawer */}
      <div style={{
        position: 'fixed', top: 0, right: 0, bottom: 0,
        width: 'min(440px, 100vw)',
        background: 'var(--bg-drawer)',
        borderRadius: '16px 0 0 16px',
        boxShadow: 'var(--shadow-drawer)',
        zIndex: 201,
        display: 'flex', flexDirection: 'column',
        transform: open ? 'translateX(0)' : 'translateX(100%)',
        transition: 'transform 0.3s ease',
      }}>
        {renderContent()}
      </div>
    </>
  )
}
