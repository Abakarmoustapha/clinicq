import { useCallback, useEffect, useRef, useState } from 'react'
import { getJson, getResult, postJson } from './api'

const POLL_MS = 30000

const STATUS_TEXT = {
  booked: 'Booked',
  checked_in: 'Checked in',
  in_progress: 'With the provider',
  done: 'Done',
  cancelled: 'Cancelled',
  no_show: 'No-show',
}

const fieldStyle = {
  display: 'block',
  width: '100%',
  boxSizing: 'border-box',
  padding: '0.5rem',
  fontSize: '1rem',
  marginTop: '0.25rem',
}
const labelStyle = { display: 'block', marginBottom: '0.75rem' }
const errorStyle = { color: 'crimson', margin: '0.25rem 0 0.5rem' }
const cardStyle = {
  border: '1px solid #bbb',
  borderRadius: 8,
  padding: '0.75rem 1rem',
  margin: '0 0 0.75rem',
}

function buttonStyle(color, busy) {
  return {
    padding: '0.5rem 1rem',
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

function messages(value) {
  return [].concat(value).join(' ')
}

function WalkInForm({ services, onAdded }) {
  const [serviceId, setServiceId] = useState('')
  const [providers, setProviders] = useState(null)
  const [providerId, setProviderId] = useState('')
  const [name, setName] = useState('')
  const [phone, setPhone] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState('')
  const [fieldErrors, setFieldErrors] = useState({})

  useEffect(() => {
    if (!serviceId) return undefined
    let ignore = false
    getJson(`/api/providers/?service=${serviceId}`)
      .then((data) => {
        if (!ignore) setProviders(data)
      })
      .catch(() => {
        if (!ignore) setFormError('Could not load the providers.')
      })
    return () => {
      ignore = true
    }
  }, [serviceId])

  function chooseService(value) {
    setServiceId(value)
    setProviders(null)
    setProviderId('')
    setFormError('')
    setFieldErrors({})
  }

  async function handleSubmit(event) {
    event.preventDefault()
    if (submitting) return
    setSubmitting(true)
    setFormError('')
    setFieldErrors({})
    try {
      const result = await postJson('/api/staff/walk-ins/', {
        provider: Number(providerId),
        service: Number(serviceId),
        patient_name: name.trim(),
        patient_phone: phone.trim(),
      })
      if (result.ok) {
        onAdded(result.body)
        setName('')
        setPhone('')
      } else if (result.status === 400 && result.body) {
        const { detail, ...fields } = result.body
        setFieldErrors(fields)
        if (detail) setFormError(detail)
      } else if (result.status === 409) {
        setFormError(result.body?.detail || 'This walk-in cannot be added.')
      } else if (result.status === 403) {
        setFormError('You are not allowed to add walk-ins, or your session has ended.')
      } else {
        setFormError('Something went wrong. Please try again.')
      }
    } catch {
      setFormError('Cannot reach the server. Check your connection and try again.')
    } finally {
      setSubmitting(false)
    }
  }

  const ready = serviceId && providerId && name.trim() && phone.trim()

  return (
    <form onSubmit={handleSubmit} style={{ ...cardStyle, background: '#f8fafc' }}>
      <h3 style={{ marginTop: 0 }}>Add a walk-in</h3>

      <label style={labelStyle}>
        Service
        <select
          style={fieldStyle}
          value={serviceId}
          onChange={(e) => chooseService(e.target.value)}
        >
          <option value="">Choose a service</option>
          {services.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </select>
        {fieldErrors.service && <p style={errorStyle}>{messages(fieldErrors.service)}</p>}
      </label>

      {serviceId && (
        <label style={labelStyle}>
          Provider
          <select
            style={fieldStyle}
            value={providerId}
            onChange={(e) => setProviderId(e.target.value)}
            disabled={providers === null}
          >
            <option value="">
              {providers === null ? 'Loading...' : 'Choose a provider'}
            </option>
            {(providers || []).map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
          {providers && providers.length === 0 && (
            <p style={errorStyle}>No provider offers this service.</p>
          )}
          {fieldErrors.provider && (
            <p style={errorStyle}>{messages(fieldErrors.provider)}</p>
          )}
        </label>
      )}

      <label style={labelStyle}>
        Patient name
        <input
          style={fieldStyle}
          value={name}
          onChange={(e) => setName(e.target.value)}
          maxLength={100}
          autoComplete="off"
        />
        {fieldErrors.patient_name && (
          <p style={errorStyle}>{messages(fieldErrors.patient_name)}</p>
        )}
      </label>

      <label style={labelStyle}>
        Patient phone
        <input
          style={fieldStyle}
          type="tel"
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
          placeholder="+235 66 12 34 56"
          maxLength={30}
          autoComplete="off"
        />
        {fieldErrors.patient_phone && (
          <p style={errorStyle}>{messages(fieldErrors.patient_phone)}</p>
        )}
      </label>

      {formError && <p style={errorStyle}>{formError}</p>}

      <button
        type="submit"
        disabled={submitting || !ready}
        style={buttonStyle('#1d4ed8', submitting)}
      >
        {submitting ? 'Adding...' : 'Add to the queue'}
      </button>
    </form>
  )
}

function ReceptionScreen({ onSessionEnded }) {
  const [day, setDay] = useState('')
  const [list, setList] = useState(null)
  const [serverToday, setServerToday] = useState(null)
  const [updatedAt, setUpdatedAt] = useState(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState(null)
  const [busyCode, setBusyCode] = useState(null)
  const [services, setServices] = useState([])
  const [showWalkIn, setShowWalkIn] = useState(false)
  const requestRef = useRef(0)

  const load = useCallback(
    async (selectedDay) => {
      requestRef.current += 1
      const requestId = requestRef.current
      const url = selectedDay
        ? `/api/staff/bookings/?date=${encodeURIComponent(selectedDay)}`
        : '/api/staff/bookings/'
      try {
        const result = await getResult(url)
        if (requestId !== requestRef.current) return
        if (result.ok) {
          setList(result.body)
          setUpdatedAt(new Date())
          setError('')
          if (!selectedDay) setServerToday(result.body.date)
        } else if (result.status === 401 || result.status === 403) {
          onSessionEnded()
        } else if (result.status === 400) {
          setError('That date is not valid.')
        } else {
          setError('Could not load the list. We will try again.')
        }
      } catch {
        if (requestId === requestRef.current) {
          setError('Cannot reach the server. We will try again.')
        }
      }
    },
    [onSessionEnded],
  )

  // The first load always asks for "today" so we learn the clinic's date from the server.
  useEffect(() => {
    if (serverToday === null && day !== '') load('')
  }, [serverToday, day, load])

  useEffect(() => {
    load(day)
    const timer = setInterval(() => {
      if (!document.hidden) load(day)
    }, POLL_MS)
    return () => clearInterval(timer)
  }, [day, load])

  useEffect(() => {
    let ignore = false
    getJson('/api/services/')
      .then((data) => {
        if (!ignore) setServices(data)
      })
      .catch(() => {})
    return () => {
      ignore = true
    }
  }, [])

  async function act(booking, action, doneText) {
    if (busyCode) return
    setBusyCode(booking.code)
    setNotice(null)
    try {
      const result = await postJson(
        `/api/staff/bookings/${encodeURIComponent(booking.code)}/${action}/`,
      )
      if (result.ok) {
        setNotice({ ok: true, text: `${booking.patient_name}: ${doneText}` })
      } else if (result.status === 409) {
        setNotice({ ok: false, text: result.body?.detail || 'This is not possible now.' })
      } else if (result.status === 404) {
        setNotice({ ok: false, text: 'This booking was not found.' })
      } else if (result.status === 403) {
        setNotice({
          ok: false,
          text: 'You are not allowed to do this, or your session has ended.',
        })
      } else if (result.status === 429) {
        setNotice({ ok: false, text: 'Too many attempts. Please wait a moment.' })
      } else {
        setNotice({ ok: false, text: 'Something went wrong. Please try again.' })
      }
      await load(day)
    } catch {
      setNotice({ ok: false, text: 'Cannot reach the server. Please try again.' })
    } finally {
      setBusyCode(null)
    }
  }

  function handleAdded(walkIn) {
    setNotice({
      ok: true,
      text: `${walkIn.patient_name} was added to the queue. Code: ${walkIn.code}`,
    })
    load(day)
  }

  function changeDay(value) {
    setNotice(null)
    setDay(value)
  }

  const shownDate = list ? list.date : day
  const known = list !== null && serverToday !== null
  // Dates are written as YYYY-MM-DD, so comparing the text compares the days.
  const isToday = known && list.date === serverToday
  const isTodayOrPast = known && list.date <= serverToday

  return (
    <section>
      <h2>Reception</h2>

      <p>
        <label>
          Day{' '}
          <input
            type="date"
            value={shownDate}
            onChange={(e) => e.target.value && changeDay(e.target.value)}
            style={{ fontSize: '1rem', padding: '0.4rem' }}
          />
        </label>{' '}
        <button style={buttonStyle('#555', false)} onClick={() => changeDay('')}>
          Today
        </button>
        <button style={buttonStyle('#555', false)} onClick={() => load(day)}>
          Refresh
        </button>
      </p>

      {updatedAt && (
        <p style={{ color: '#555', fontSize: '0.9rem', margin: '0 0 0.5rem' }}>
          Last updated at {updatedAt.toLocaleTimeString()}
        </p>
      )}

      {error && <p style={errorStyle}>{error}</p>}
      {notice && (
        <p style={{ color: notice.ok ? '#166534' : 'crimson' }} aria-live="polite">
          {notice.text}
        </p>
      )}

      <p>
        <button
          style={buttonStyle('#1d4ed8', false)}
          onClick={() => setShowWalkIn(!showWalkIn)}
        >
          {showWalkIn ? 'Hide the walk-in form' : 'Add a walk-in'}
        </button>
      </p>
      {showWalkIn && <WalkInForm services={services} onAdded={handleAdded} />}

      {list === null && !error && <p>Loading...</p>}
      {list && list.bookings.length === 0 && (
        <p>No bookings on {list.date}. Use the day box to look at another day.</p>
      )}
      {list && list.bookings.length > 0 && (
        <p style={{ color: '#555' }}>
          {list.bookings.length} booking{list.bookings.length === 1 ? '' : 's'} on{' '}
          {list.date}. This list updates by itself every 30 seconds.
        </p>
      )}

      {list &&
        list.bookings.map((b) => (
          <div key={b.code} style={cardStyle}>
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                flexWrap: 'wrap',
                gap: '0.5rem',
              }}
            >
              <strong>
                {b.is_walk_in
                  ? `Walk-in, arrived ${clinicTime(b.checked_in_at)}`
                  : clinicTime(b.start_at)}
              </strong>
              <span>{STATUS_TEXT[b.status] || b.status}</span>
            </div>
            <div>
              {b.patient_name}{' '}
              <a href={`tel:${b.patient_phone}`}>{b.patient_phone}</a>
            </div>
            <div style={{ color: '#555', fontSize: '0.9rem', marginBottom: '0.5rem' }}>
              {b.service} with {b.provider}. Code {b.code}
            </div>

            {b.status === 'booked' && isTodayOrPast && (
              <div>
                {isToday && (
                  <button
                    style={buttonStyle('#1d4ed8', busyCode === b.code)}
                    disabled={busyCode !== null}
                    onClick={() => act(b, 'check-in', 'checked in.')}
                  >
                    Check in
                  </button>
                )}
                <button
                  style={buttonStyle('#b45309', busyCode === b.code)}
                  disabled={busyCode !== null}
                  onClick={() => act(b, 'no-show', 'marked as a no-show.')}
                >
                  No-show
                </button>
              </div>
            )}
          </div>
        ))}
    </section>
  )
}

export default ReceptionScreen