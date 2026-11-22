import { useEffect, useState } from 'react'
import { getJson } from './api'
import BookingForm from './BookingForm'

function toIso(d) {
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}-${month}-${day}`
}

const TODAY = new Date()
const LAST_DAY = new Date()
LAST_DAY.setDate(LAST_DAY.getDate() + 30)

const pageStyle = {
  maxWidth: 520,
  margin: '2rem auto',
  padding: '0 1rem',
  fontFamily: 'sans-serif',
  textAlign: 'left',
}

function choiceStyle(active) {
  return {
    padding: '0.5rem 0.9rem',
    margin: '0 0.5rem 0.5rem 0',
    border: '1px solid #888',
    borderRadius: 6,
    background: active ? '#1d4ed8' : 'white',
    color: active ? 'white' : 'black',
    cursor: 'pointer',
    fontSize: '1rem',
  }
}

function App() {
  const [services, setServices] = useState([])
  const [service, setService] = useState(null)
  const [providers, setProviders] = useState(null)
  const [provider, setProvider] = useState(null)
  const [date, setDate] = useState(toIso(TODAY))
  const [slots, setSlots] = useState(null)
  const [slot, setSlot] = useState(null)
  const [refresh, setRefresh] = useState(0)
  const [notice, setNotice] = useState('')
  const [confirmation, setConfirmation] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let ignore = false
    getJson('/api/services/')
      .then((data) => {
        if (!ignore) setServices(data)
      })
      .catch((e) => {
        if (!ignore) setError(e.message)
      })
    return () => {
      ignore = true
    }
  }, [])

  useEffect(() => {
    if (!service) return
    let ignore = false
    getJson(`/api/providers/?service=${service.id}`)
      .then((data) => {
        if (!ignore) setProviders(data)
      })
      .catch((e) => {
        if (!ignore) setError(e.message)
      })
    return () => {
      ignore = true
    }
  }, [service])

  useEffect(() => {
    if (!service || !provider || !date) return
    let ignore = false
    getJson(`/api/slots/?provider=${provider.id}&service=${service.id}&date=${date}`)
      .then((data) => {
        if (!ignore) setSlots(data.slots)
      })
      .catch((e) => {
        if (!ignore) setError(e.message)
      })
    return () => {
      ignore = true
    }
  }, [service, provider, date, refresh])

  function chooseService(selected) {
    if (service?.id === selected.id) return
    setError('')
    setNotice('')
    setService(selected)
    setProviders(null)
    setProvider(null)
    setSlots(null)
    setSlot(null)
  }

  function chooseProvider(selected) {
    if (provider?.id === selected.id) return
    setError('')
    setNotice('')
    setProvider(selected)
    setSlots(null)
    setSlot(null)
  }

  function changeDate(value) {
    if (!value || value === date) return
    setError('')
    setNotice('')
    setDate(value)
    setSlots(null)
    setSlot(null)
  }

  function chooseSlot(selected) {
    setNotice('')
    setSlot(selected)
  }

  function handleSlotTaken(message) {
    setNotice(message)
    setSlot(null)
    setSlots(null)
    setRefresh((n) => n + 1)
  }

  function handleBooked(booking) {
    setConfirmation({
      code: booking.code,
      service: booking.service,
      provider: booking.provider,
      date,
      time: slot.time,
    })
  }

  function startOver() {
    setService(null)
    setProviders(null)
    setProvider(null)
    setDate(toIso(TODAY))
    setSlots(null)
    setSlot(null)
    setNotice('')
    setError('')
    setConfirmation(null)
  }

  if (confirmation) {
    return (
      <main style={pageStyle}>
        <h1>ClinicQ</h1>
        <h2>Booking confirmed</h2>
        <p>Your booking code is:</p>
        <p style={{ fontSize: '2rem', fontWeight: 'bold', letterSpacing: '0.2rem' }}>
          {confirmation.code}
        </p>
        <p>
          {confirmation.service} with {confirmation.provider}
          <br />
          {confirmation.date} at {confirmation.time}
        </p>
        <p>
          <strong>Write this code down.</strong> You need it, with your phone number,
          to cancel or to follow your place in the queue.
        </p>
        <button style={choiceStyle(true)} onClick={startOver}>
          Make another booking
        </button>
      </main>
    )
  }

  return (
    <main style={pageStyle}>
      <h1>ClinicQ</h1>
      {error && <p style={{ color: 'crimson' }}>Something went wrong: {error}</p>}

      <h2>1. Choose a service</h2>
      {services.map((s) => (
        <button
          key={s.id}
          style={choiceStyle(service?.id === s.id)}
          onClick={() => chooseService(s)}
        >
          {s.name} ({s.slot_minutes} min)
        </button>
      ))}

      {service && (
        <>
          <h2>2. Choose a provider</h2>
          {providers === null && <p>Loading...</p>}
          {providers && providers.length === 0 && (
            <p>No provider offers this service yet.</p>
          )}
          {providers &&
            providers.map((p) => (
              <button
                key={p.id}
                style={choiceStyle(provider?.id === p.id)}
                onClick={() => chooseProvider(p)}
              >
                {p.name}
              </button>
            ))}
        </>
      )}

      {provider && (
        <>
          <h2>3. Choose a day</h2>
          <input
            type="date"
            value={date}
            min={toIso(TODAY)}
            max={toIso(LAST_DAY)}
            onChange={(e) => changeDate(e.target.value)}
            style={{ fontSize: '1rem', padding: '0.4rem' }}
          />

          <h2>4. Choose a time</h2>
          {notice && <p style={{ color: '#b45309' }}>{notice} Please choose another time.</p>}
          {slots === null && <p>Loading...</p>}
          {slots && slots.length === 0 && (
            <p>No free times on this day. Try another day.</p>
          )}
          {slots &&
            slots.map((s) => (
              <button
                key={s.start_at}
                style={choiceStyle(slot?.start_at === s.start_at)}
                onClick={() => chooseSlot(s)}
              >
                {s.time}
              </button>
            ))}
        </>
      )}

      {slot && (
        <BookingForm
          provider={provider}
          service={service}
          slot={slot}
          date={date}
          onBooked={handleBooked}
          onSlotTaken={handleSlotTaken}
        />
      )}
    </main>
  )
}

export default App