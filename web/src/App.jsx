import { useEffect, useState } from 'react'

function App() {
  const [services, setServices] = useState([])
  const [error, setError] = useState('')

  useEffect(() => {
    fetch('/api/services/')
      .then((response) => {
        if (!response.ok) throw new Error('The server answered ' + response.status)
        return response.json()
      })
      .then(setServices)
      .catch((err) => setError(err.message))
  }, [])

  return (
    <main style={{ maxWidth: 480, margin: '2rem auto', fontFamily: 'sans-serif' }}>
      <h1>ClinicQ</h1>
      <h2>Our services</h2>
      {error && <p style={{ color: 'crimson' }}>Could not load services: {error}</p>}
      <ul>
        {services.map((service) => (
          <li key={service.id}>
            {service.name} ({service.slot_minutes} minutes)
          </li>
        ))}
      </ul>
    </main>
  )
}

export default App