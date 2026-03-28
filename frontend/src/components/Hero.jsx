import React from 'react'
import FileList from './FileList.jsx'

export default function Hero({ docs, uploading, uploadMsg, fileRef, onUpload, onDelete }) {
  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '80px 24px 120px',
    }}>
      {/* Wordmark */}
      <div style={{
        fontSize: 11, fontWeight: 500, letterSpacing: '0.14em',
        textTransform: 'uppercase', color: 'var(--text-light)',
        marginBottom: 56,
      }}>
        Research Chat
      </div>

      {/* Title */}
      <h1 style={{
        fontFamily: 'var(--font-serif)',
        fontSize: 'clamp(40px, 6vw, 72px)',
        fontWeight: 400,
        lineHeight: 1.15,
        color: 'var(--text)',
        textAlign: 'center',
        maxWidth: 600,
        marginBottom: 12,
      }}>
        Ask anything about<br />
        <em>your research.</em>
      </h1>

      <p style={{
        fontSize: 15, color: 'var(--text-muted)', fontWeight: 300,
        textAlign: 'center', maxWidth: 380, marginBottom: 48, lineHeight: 1.7,
      }}>
        Upload PDFs or text files. Ask questions in chat.
        Sources cited automatically.
      </p>

      {/* Upload */}
      <input
        ref={fileRef}
        id="file-input"
        type="file"
        accept=".pdf,.txt"
        onChange={onUpload}
        style={{ display: 'none' }}
      />
      <label
        htmlFor="file-input"
        style={{
          display: 'inline-flex', alignItems: 'center', gap: 8,
          padding: '13px 28px',
          background: uploading ? 'var(--pill-bg)' : 'var(--text)',
          color: uploading ? 'var(--text-muted)' : '#fff',
          borderRadius: 999,
          fontSize: 14, fontWeight: 500,
          cursor: uploading ? 'not-allowed' : 'pointer',
          letterSpacing: '0.01em',
          transition: 'background 0.15s, color 0.15s',
          boxShadow: uploading ? 'none' : 'var(--shadow-card)',
          marginBottom: 20,
          userSelect: 'none',
        }}
        onMouseEnter={e => { if (!uploading) e.currentTarget.style.background = '#1a1a1a' }}
        onMouseLeave={e => { if (!uploading) e.currentTarget.style.background = 'var(--text)' }}
      >
        {uploading ? (
          <>
            <span className="spin" style={{ fontSize: 13 }}>◌</span>
            Indexing…
          </>
        ) : (
          <>
            <span style={{ fontSize: 16, lineHeight: 1 }}>+</span>
            Upload documents
          </>
        )}
      </label>

      {/* Upload status */}
      {uploadMsg && (
        <p style={{
          fontSize: 12, marginBottom: 20,
          color: uploadMsg.ok ? '#3a7a52' : '#b03a2e',
        }}>
          {uploadMsg.ok ? '✓ ' : '✕ '}{uploadMsg.text}
        </p>
      )}

      {/* File list */}
      <FileList docs={docs} onDelete={onDelete} />

      {/* Empty hint */}
      {docs.length === 0 && !uploadMsg && (
        <p style={{ fontSize: 12, color: 'var(--text-light)', marginTop: 16 }}>
          No documents yet — upload one to get started.
        </p>
      )}
    </div>
  )
}
