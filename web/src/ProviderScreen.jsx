import { useCallback, useEffect, useRef, useState } from 'react'
import { getResult, postJson } from './api'

const POLL_MS = 15000

const errorStyle = { color: 'crimson', margin: '0.25rem 0 0.5rem' }
const cardStyle = {
  border: '1px solid #bbb',
  borderRadius: 8,
  padding: '0.75rem 1rem',
  margin: '0 0 0.75rem',
}
const roomStyle = { ...cardStyle, background: '#ecfdf5', border: '2px solid #16a34a' }

function buttonStyle(color, busy) {
  return {
    padding: '0.6rem 1.2rem',
    marginRight: '0.5rem',
    fontSize: '1rem',
    border: 'none',
    borderRadius: 6,
    background: color,
    color: 'white',
    cursor: busy ? 'wait' : 'pointer',
  }
}

// The server sends clinic time, for example 2026-11-24T09:00:00+01:00.
// We cut the text and never convert it, so everyone sees the clinic's hour.
function clinicTime(iso) {
  return iso ? iso.slice(11, 16) : ''
}

function ProviderScreen({ onSessionEnded }) {
  const [queue, setQueue] = useState(null)
  const [updatedAt, setUpdatedAt] = useState(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState(null)
  const [busy, setBusy] = useState(false)
  const [confirmDone, setConfirmDone] = useState(false)
  const requestRef = useRef(0)

  const load = useCallback(async () => {
    requestRef.current += 1
    const requestId = requestRef.current
    try {
      const result = await getResult('/api/staff/queue/')
      if (requestId !== requestRef.current) return
      if (result.ok) {
        setQueue(result.body)
        setUpdatedAt(new Date())
        setError('')
      } else if (result.status === 401 || result.status === 403) {
        onSessionEnded()
      } else if (result.status === 409) {
        setError(
          (result.body?.detail || 'This account is not linked to a provider.') +
            ' Ask an administrator to link your account to a provider.',
        )
      } else {
        setError('Could not load the queue. We will try again.')
      }
    } catch {
      if (requestId === requestRef.current) {
        setError('Cannot reach the server. We will try again.')
      }
    }
  }, [onSessionEnded])

  useEffect(() => {
    load()
    const timer = setInterval(() => {
      if (!document.hidden) load()
    }, POLL_MS)
    function loadWhenVisible() {
      if (!document.hidden) load()
    }
    document.addEventListener('visibilitychange', loadWhenVisible)
    return () => {
      clearInterval(timer)
      document.removeEventListener('visibilitychange', loadWhenVisible)
    }
  }, [load])

  function explain(result, fallback) {
    if (result.status === 409) {
      return result.body?.detail || fallback
    }
    if (result.status === 404) return 'This booking was not found.'
    if (result.status === 403) {
      return 'You are not allowed to do this, or your session has ended.'
    }
    if (result.status === 429) return 'Too many attempts. Please wait a moment.'
    return 'Something went wrong. Please try again.'
  }

  async function callNext() {
    if (busy) return
    setBusy(true)
    setNotice(null)
    setConfirmDone(false)
    try {
      const result = await postJson('/api/staff/queue/call-next/')
      if (result.ok) {
        setNotice({ ok: true, text: `Called ${result.body.patient_name}.` })
      } else {
        setNotice({ ok: false, text: explain(result, 'This is not possible now.') })
      }
      await load()
    } catch {
      setNotice({ ok: false, text: 'Cannot reach the server. Please try again.' })
    } finally {
      setBusy(false)
    }
  }

  async function finishCurrent() {
    if (busy || !queue || !queue.in_progress) return
    const patient = queue.in_progress
    setBusy(true)
    setNotice(null)
    try {
      const result = await postJson(
        `/api/staff/bookings/${encodeURIComponent(patient.code)}/done/`,
      )
      if (result.ok) {
        setNotice({ ok: true, text: `${patient.patient_name}: consultation finished.` })
      } else {
        setNotice({ ok: false, text: explain(result, 'This is not possible now.') })
      }
      setConfirmDone(false)
      await load()
    } catch {
      setNotice({ ok: false, text: 'Cannot reach the server. Please try again.' })
    } finally {
      setBusy(false)
    }
  }

  const inRoom = queue ? queue.in_progress : null
  const waiting = queue ? queue.waiting : []
  const canCallNext = !busy && queue !== null && !inRoom && waiting.length > 0

  return (
    <section>
      <h2>{queue ? `Queue of ${queue.provider}` : 'Your queue'}</h2>

      <p>
        <button style={buttonStyle('#555', false)} onClick={load}>
          Refresh
        </button>
        {updatedAt && (
          <span style={{ color: '#555', fontSize: '0.9rem' }}>
            Last updated at {updatedAt.toLocaleTimeString()}. Updates by itself every 15
            seconds.
          </span>
        )}
      </p>

      {error && <p style={errorStyle}>{error}</p>}
      {notice && (
        <p style={{ color: notice.ok ? '#166534' : 'crimson' }} aria-live="polite">
          {notice.text}
        </p>
      )}

      {queue === null && !error && <p>Loading...</p>}

      {queue && (
        <>
          <h3>With you now</h3>
          {inRoom ? (
            <div style={roomStyle}>
              <strong>{inRoom.patient_name}</strong>{' '}
              <a href={`tel:${inRoom.patient_phone}`}>{inRoom.patient_phone}</a>
              <div style={{ color: '#555', fontSize: '0.9rem', margin: '0.25rem 0 0.75rem' }}>
                {inRoom.service}. Arrived {clinicTime(inRoom.checked_in_at)}. Code{' '}
                {inRoom.code}
              </div>
              {!confirmDone && (
                <button
                  style={buttonStyle('#15803d', busy)}
                  disabled={busy}
                  onClick={() => setConfirmDone(true)}
                >
                  Done
                </button>
              )}
              {confirmDone && (
                <div>
                  <p style={{ margin: '0 0 0.5rem' }}>
                    <strong>Finish this consultation? This cannot be undone.</strong>
                  </p>
                  <button
                    style={buttonStyle('#15803d', busy)}
                    disabled={busy}
                    onClick={finishCurrent}
                  >
                    {busy ? 'Saving...' : 'Yes, it is done'}
                  </button>
                  <button
                    style={buttonStyle('#555', false)}
                    disabled={busy}
                    onClick={() => setConfirmDone(false)}
                  >
                    No, go back
                  </button>
                </div>
              )}
            </div>
          ) : (
            <p>Nobody is with you now.</p>
          )}

          <p>
            <button
              style={{
                ...buttonStyle('#1d4ed8', busy),
                opacity: canCallNext ? 1 : 0.5,
                cursor: canCallNext ? 'pointer' : 'not-allowed',
              }}
              disabled={!canCallNext}
              onClick={callNext}
            >
              Call next patient
            </button>
            {inRoom && (
              <span style={{ color: '#555' }}>Finish the current patient first.</span>
            )}
            {!inRoom && waiting.length === 0 && (
              <span style={{ color: '#555' }}>No patients are waiting.</span>
            )}
          </p>

          <h3>
            Waiting ({waiting.length}), in order of arrival
          </h3>
          {waiting.length === 0 && <p>The waiting list is empty.</p>}
          {waiting.map((p) => (
            <div key={p.code} style={cardStyle}>
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  flexWrap: 'wrap',
                  gap: '0.5rem',
                }}
              >
                <strong>
                  {p.position}. {p.patient_name}
                </strong>
                <span>
                  Arrived {clinicTime(p.checked_in_at)}
                  {p.is_walk_in ? ', walk-in' : ''}
                </span>
              </div>
              <div>
                <a href={`tel:${p.patient_phone}`}>{p.patient_phone}</a>
              </div>
              <div style={{ color: '#555', fontSize: '0.9rem' }}>
                {p.service}. Code {p.code}
              </div>
            </div>
          ))}
        </>
      )}
    </section>
  )
}

export default ProviderScreen