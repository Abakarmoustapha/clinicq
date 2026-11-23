import { useEffect, useState } from 'react'
import { getResult, postJson } from './api'

const POLL_MS = 30000
const LIVE_STATUSES = ['checked_in', 'in_progress']

const pageStyle = {
  maxWidth: 520,
  margin: '2rem auto',
  padding: '0 1rem',
  fontFamily: 'sans-serif',
  textAlign: 'left',
}
const fieldStyle = {
  display: 'block',
  width: '100%',
  boxSizing: 'border-box',
  padding: '0.5rem',
  fontSize: '1rem',
  marginTop: '0.25rem',
}
const errorStyle = { color: 'crimson', margin: '0.25rem 0 0.75rem' }
const noteStyle = { color: '#555', fontSize: '0.9rem', margin: '0.25rem 0' }
const queueBoxStyle = {
  background: '#eef2ff',
  borderRadius: 8,
  padding: '0.75rem 1rem',
  margin: '0.75rem 0',
}

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

const STATUS_TEXT = {
  booked: 'Booked',
  checked_in: 'Checked in, waiting to be called',
  in_progress: 'With the provider now',
  done: 'Done',
  cancelled: 'Cancelled',
  no_show: 'Marked as a no-show',
}

// The server sends clinic time, for example 2026-11-24T09:00:00+01:00.
// We cut the text and never convert it, so every patient sees the clinic's hour.
function clinicDate(iso) {
  return iso.slice(0, 10)
}
function clinicTime(iso) {
  return iso.slice(11, 16)
}

function ManageBooking() {
  const [code, setCode] = useState('')
  const [booking, setBooking] = useState(null)
  const [message, setMessage] = useState('')
  const [looking, setLooking] = useState(false)
  const [phone, setPhone] = useState('')
  const [phoneError, setPhoneError] = useState('')
  const [confirming, setConfirming] = useState(false)
  const [cancelling, setCancelling] = useState(false)
  const [cancelMessage, setCancelMessage] = useState('')
  const [liveNote, setLiveNote] = useState('')

  const bookingCode = booking ? booking.code : null
  const isLive = booking ? LIVE_STATUSES.includes(booking.status) : false

  // While the patient is waiting, ask the server for fresh numbers every 30 seconds.
  useEffect(() => {
    if (!bookingCode || !isLive) return undefined
    let stopped = false

    async function refresh() {
      if (document.hidden) return
      try {
        const result = await getResult(
          `/api/bookings/${encodeURIComponent(bookingCode)}/queue/`,
        )
        if (stopped) return
        if (result.ok) {
          setBooking(result.body)
          setLiveNote('')
        } else if (result.status === 429) {
          setLiveNote('Updates are paused for a while. Please try again later.')
        } else {
          setLiveNote('Could not refresh. We will try again.')
        }
      } catch {
        if (!stopped) setLiveNote('No connection. We will try again.')
      }
    }

    function refreshWhenVisible() {
      if (!document.hidden) refresh()
    }

    const timer = setInterval(refresh, POLL_MS)
    document.addEventListener('visibilitychange', refreshWhenVisible)
    return () => {
      stopped = true
      clearInterval(timer)
      document.removeEventListener('visibilitychange', refreshWhenVisible)
    }
  }, [bookingCode, isLive])

  function resetCancel() {
    setPhone('')
    setPhoneError('')
    setConfirming(false)
    setCancelMessage('')
  }

  async function handleLookup(event) {
    event.preventDefault()
    const clean = code.trim().toUpperCase()
    if (!clean || looking) return
    setLooking(true)
    setMessage('')
    setLiveNote('')
    setBooking(null)
    resetCancel()
    try {
      const result = await getResult(`/api/bookings/${encodeURIComponent(clean)}/queue/`)
      if (result.ok) {
        setBooking(result.body)
      } else if (result.status === 404) {
        setMessage('No booking found with this code. Check the code and try again.')
      } else if (result.status === 429) {
        setMessage('Too many attempts. Please wait a while and try again.')
      } else {
        setMessage('Something went wrong. Please try again.')
      }
    } catch {
      setMessage('Cannot reach the server. Check your connection and try again.')
    } finally {
      setLooking(false)
    }
  }

  function askToConfirm() {
    setPhoneError('')
    setCancelMessage('')
    if (!phone.trim()) {
      setPhoneError('Enter the phone number you used when you booked.')
      return
    }
    setConfirming(true)
  }

  async function handleCancel() {
    if (cancelling) return
    setCancelling(true)
    setPhoneError('')
    setCancelMessage('')
    try {
      const result = await postJson(
        `/api/bookings/${encodeURIComponent(booking.code)}/cancel/`,
        { patient_phone: phone.trim() },
      )
      if (result.ok) {
        setBooking({
          ...booking,
          ...result.body,
          position: null,
          people_ahead: null,
          estimated_wait_minutes: null,
        })
        setConfirming(false)
      } else if (result.status === 400 && result.body?.patient_phone) {
        setPhoneError([].concat(result.body.patient_phone).join(' '))
        setConfirming(false)
      } else if (result.status === 404) {
        setCancelMessage(
          'We could not cancel this booking. Check the phone number you used when you booked.',
        )
        setConfirming(false)
      } else if (result.status === 409) {
        setCancelMessage(result.body?.detail || 'This booking can no longer be cancelled.')
        setConfirming(false)
      } else if (result.status === 429) {
        setCancelMessage('Too many attempts. Please wait a while and try again.')
        setConfirming(false)
      } else {
        setCancelMessage('Something went wrong. Please try again.')
        setConfirming(false)
      }
    } catch {
      setCancelMessage('Cannot reach the server. Check your connection and try again.')
      setConfirming(false)
    } finally {
      setCancelling(false)
    }
  }

  return (
    <main style={pageStyle}>
      <h1>ClinicQ</h1>
      <h2>Find my booking</h2>

      <form onSubmit={handleLookup}>
        <label>
          Booking code
          <input
            style={fieldStyle}
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder="For example 455J7SH3"
            maxLength={20}
            autoComplete="off"
          />
        </label>
        <p>
          <button type="submit" disabled={looking} style={buttonStyle('#1d4ed8', looking)}>
            {looking ? 'Looking...' : 'Look up'}
          </button>
        </p>
      </form>

      {message && <p style={errorStyle}>{message}</p>}

      {booking && (
        <section style={{ border: '1px solid #bbb', borderRadius: 8, padding: '1rem' }}>
          <p style={{ fontSize: '1.5rem', fontWeight: 'bold', letterSpacing: '0.15rem', margin: 0 }}>
            {booking.code}
          </p>
          <p>
            {booking.service} with {booking.provider}
            <br />
            {clinicDate(booking.start_at)} at {clinicTime(booking.start_at)}
          </p>
          <p>
            <strong>Status:</strong> {STATUS_TEXT[booking.status] || booking.status}
          </p>

          {booking.status === 'checked_in' && booking.people_ahead !== null && (
            <div style={queueBoxStyle} aria-live="polite">
              <p style={{ margin: 0, fontWeight: 'bold' }}>
                {booking.people_ahead === 0
                  ? 'You are next.'
                  : booking.people_ahead === 1
                    ? '1 person is ahead of you.'
                    : `${booking.people_ahead} people are ahead of you.`}
              </p>
              {booking.people_ahead > 0 && (
                <p style={{ margin: '0.25rem 0 0' }}>
                  Estimated wait: about {booking.estimated_wait_minutes} minutes. This is
                  only an estimate.
                </p>
              )}
            </div>
          )}

          {booking.status === 'in_progress' && (
            <div style={queueBoxStyle} aria-live="polite">
              <p style={{ margin: 0, fontWeight: 'bold' }}>
                It is your turn. Please go to {booking.provider}.
              </p>
            </div>
          )}

          {booking.status === 'done' && <p>Your visit is finished. Thank you.</p>}

          {isLive && <p style={noteStyle}>This page updates by itself every 30 seconds.</p>}
          {liveNote && <p style={noteStyle}>{liveNote}</p>}

          {booking.status === 'cancelled' && (
            <p>This booking is cancelled. The time is free for other patients.</p>
          )}

          {booking.status === 'booked' && (
            <>
              <label>
                Phone number used for the booking
                <input
                  style={fieldStyle}
                  type="tel"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="+235 66 12 34 56"
                  maxLength={30}
                  autoComplete="tel"
                />
              </label>
              {phoneError && <p style={errorStyle}>{phoneError}</p>}
              {cancelMessage && <p style={errorStyle}>{cancelMessage}</p>}

              {!confirming && (
                <p>
                  <button style={buttonStyle('#b91c1c', false)} onClick={askToConfirm}>
                    Cancel this booking
                  </button>
                </p>
              )}

              {confirming && (
                <div>
                  <p>
                    <strong>
                      Are you sure? You will lose this time and cannot undo it.
                    </strong>
                  </p>
                  <button
                    style={buttonStyle('#b91c1c', cancelling)}
                    onClick={handleCancel}
                    disabled={cancelling}
                  >
                    {cancelling ? 'Cancelling...' : 'Yes, cancel it'}
                  </button>
                  <button
                    style={buttonStyle('#555', false)}
                    onClick={() => setConfirming(false)}
                    disabled={cancelling}
                  >
                    No, keep it
                  </button>
                </div>
              )}
            </>
          )}
        </section>
      )}
    </main>
  )
}

export default ManageBooking