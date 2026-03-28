import React from 'react'

export default function FileList({ docs, onDelete }) {
  if (!docs || docs.length === 0) return null

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6, width: '100%', maxWidth: 360 }}>
      {docs.map(doc => (
        <div
          key={doc.id}
          style={{
            display: 'flex', alignItems: 'center', gap: 10,
            padding: '9px 14px',
            background: '#fff',
            border: '1px solid var(--border)',
            borderRadius: 999,
            boxShadow: 'var(--shadow-sm)',
          }}
        >
          <span style={{ fontSize: 13, flexShrink: 0 }}>
            {doc.filename.endsWith('.pdf') ? '📄' : '📝'}
          </span>
          <span style={{
            flex: 1, fontSize: 13, color: 'var(--text)',
            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          }}>
            {doc.filename}
          </span>
          <span style={{ fontSize: 11, color: 'var(--text-light)', flexShrink: 0 }}>
            {doc.n_chunks} chunks
          </span>
          <button
            onClick={() => onDelete(doc.id)}
            style={{
              background: 'none', border: 'none', padding: '0 2px',
              fontSize: 14, color: 'var(--text-light)', flexShrink: 0,
              lineHeight: 1, transition: 'color 0.1s',
            }}
            onMouseEnter={e => e.currentTarget.style.color = 'var(--text)'}
            onMouseLeave={e => e.currentTarget.style.color = 'var(--text-light)'}
          >
            ×
          </button>
        </div>
      ))}
    </div>
  )
}
