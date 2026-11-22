import { useState } from 'react'
import { postJson } from './api'

const labelStyle = { display: 'block', marginBottom: '0.9rem' }
const fieldStyle = {
  display: 'block',
  width: '100%',
  boxSizing: 'border-box',
  padding: '0.5rem',
  fontSize: '1rem',
  marginTop: '0.25rem',
}
const errorStyle = { color: 'crimson', margin: '0.25rem 0 0' }

function messages(value) {
  return [].concat(value).join(' ')
}

function BookingForm({ provider, service, slot, date, onBooked, onSlotTaken }) {
  const [name, setName] = useState('')
  const [phone, setPhone] = useState('')
  const [email, setEmail] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState('')
  const [fieldErrors, setFieldErrors] = useState({})

  async function handleSubmit(event) {
    event.preventDefault()
    if (submitting) return
    setSubmitting(true)
    setFormError('')
    setFieldErrors({})
    try {
      const result = await postJson('/api/bookings/', {
        provider: provider.id,
        service: service.id,
        start_at: slot.start_at,
        patient_name: name.trim(),
        patient_phone: phone.trim(),
        patient_email: email.trim(),
      })
      if (result.ok) {
        onBooked(result.body)
      } else if (result.status === 409) {
        onSlotTaken(result.body?.detail || 'Sorry, that time is no longer available.')
      } else if (result.status === 400 && result.body) {
        const { detail, ...fields } = result.body
        setFieldErrors(fields)
        if (detail) setFormError(detail)
      } else if (result.status === 429) {
        setFormError('Too many attempts. Please wait a while and try again.')
      } else {
        setFormError('Something went wrong. Please try again.')
      }
    } catch {
      setFormError('Cannot reach the server. Check your connection and try again.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <h2>5. Your details</h2>
      <p>
        {service.name} with {provider.name} on {date} at {slot.time}
      </p>

      <label style={labelStyle}>
        Your name
        <input
          style={fieldStyle}
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
          maxLength={100}
          autoComplete="name"
        />
        {fieldErrors.patient_name && (
          <p style={errorStyle}>{messages(fieldErrors.patient_name)}</p>
        )}
      </label>

      <label style={labelStyle}>
        Phone number
        <input
          style={fieldStyle}
          type="tel"
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
          placeholder="+235 66 12 34 56"
          required
          maxLength={30}
          autoComplete="tel"
        />
        {fieldErrors.patient_phone && (
          <p style={errorStyle}>{messages(fieldErrors.patient_phone)}</p>
        )}
      </label>

      <label style={labelStyle}>
        Email (optional, for reminders)
        <input
          style={fieldStyle}
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          autoComplete="email"
        />
        {fieldErrors.patient_email && (
          <p style={errorStyle}>{messages(fieldErrors.patient_email)}</p>
        )}
      </label>

      {formError && <p style={errorStyle}>{formError}</p>}

      <button
        type="submit"
        disabled={submitting}
        style={{
          padding: '0.6rem 1.2rem',
          fontSize: '1rem',
          border: 'none',
          borderRadius: 6,
          background: '#1d4ed8',
          color: 'white',
          cursor: submitting ? 'wait' : 'pointer',
        }}
      >
        {submitting ? 'Booking...' : 'Book this time'}
      </button>
    </form>
  )
}

export default BookingForm