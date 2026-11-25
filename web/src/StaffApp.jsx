import { useCallback, useEffect, useState } from 'react'
import { getResult, postJson } from './api'
import ProviderScreen from './ProviderScreen.jsx'
import ReceptionScreen from './ReceptionScreen.jsx'

const pageStyle = {
  maxWidth: 860,
  margin: '2rem auto',
  padding: '0 1rem',
  fontFamily: 'sans-serif',
  textAlign: 'left',
}
const formStyle = { maxWidth: 520 }
const fieldStyle = {
  display: 'block',
  width: '100%',
  boxSizing: 'border-box',
  padding: '0.5rem',
  fontSize: '1rem',
  marginTop: '0.25rem',
}
const labelStyle = { display: 'block', marginBottom: '0.9rem' }
const errorStyle = { color: 'crimson', margin: '0.25rem 0 0.75rem' }

function buttonStyle(color, busy) {
  return {
    padding: '0.6rem 1.2rem',
    fontSize: '1rem',
    border: 'none',
    borderRadius: 6,
    background: color,
    color: 'white',
    cursor: busy ? 'wait' : 'pointer',
  }
}

const ROLE_TEXT = {
  admin: 'Administrator',
  receptionist: 'Receptionist',
  provider: 'Provider',
}

function StaffApp() {
  // undefined = still asking the server, null = signed out, object = signed in
  const [user, setUser] = useState(undefined)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [message, setMessage] = useState('')

  useEffect(() => {
    let ignore = false
    getResult('/api/auth/me/')
      .then((result) => {
        if (!ignore) setUser(result.ok ? result.body : null)
      })
      .catch(() => {
        if (!ignore) {
          setUser(null)
          setMessage('Cannot reach the server. Check your connection and try again.')
        }
      })
    return () => {
      ignore = true
    }
  }, [])

  const handleSessionEnded = useCallback(() => {
    setUser(null)
    setMessage('Your session has ended. Please sign in again.')
  }, [])

  async function handleLogin(event) {
    event.preventDefault()
    if (submitting) return
    setSubmitting(true)
    setMessage('')
    try {
      const result = await postJson('/api/auth/login/', {
        email: email.trim(),
        password,
      })
      if (result.ok) {
        setUser(result.body)
        setPassword('')
      } else if (result.status === 401) {
        setMessage('Wrong email or password.')
      } else if (result.status === 400) {
        setMessage('Enter a valid email address and your password.')
      } else if (result.status === 429) {
        setMessage('Too many attempts. Please wait a while and try again.')
      } else if (result.status === 403) {
        setMessage('The request was refused. Reload the page and try again.')
      } else {
        setMessage('Something went wrong. Please try again.')
      }
    } catch {
      setMessage('Cannot reach the server. Check your connection and try again.')
    } finally {
      setSubmitting(false)
    }
  }

  async function handleLogout() {
    if (submitting) return
    setSubmitting(true)
    setMessage('')
    try {
      const result = await postJson('/api/auth/logout/')
      if (result.ok) {
        setUser(null)
      } else {
        setMessage('Could not sign out. Please try again.')
      }
    } catch {
      setMessage('Cannot reach the server. Check your connection and try again.')
    } finally {
      setSubmitting(false)
    }
  }

  if (user === undefined) {
    return (
      <main style={pageStyle}>
        <h1>ClinicQ</h1>
        <p>Loading...</p>
      </main>
    )
  }

  if (user) {
    const isFrontDesk = user.role === 'admin' || user.role === 'receptionist'
    return (
      <main style={pageStyle}>
        <h1>ClinicQ</h1>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: '0.5rem',
          }}
        >
          <p style={{ margin: 0 }}>
            Signed in as <strong>{user.email}</strong> (
            {ROLE_TEXT[user.role] || user.role})
          </p>
          <button
            style={buttonStyle('#555', submitting)}
            onClick={handleLogout}
            disabled={submitting}
          >
            {submitting ? 'Signing out...' : 'Sign out'}
          </button>
        </div>
        {message && <p style={errorStyle}>{message}</p>}

        {isFrontDesk && <ReceptionScreen onSessionEnded={handleSessionEnded} />}
        {user.role === 'provider' && (
          <ProviderScreen onSessionEnded={handleSessionEnded} />
        )}
      </main>
    )
  }

  return (
    <main style={pageStyle}>
      <div style={formStyle}>
        <h1>ClinicQ</h1>
        <h2>Staff sign in</h2>
        <form onSubmit={handleLogin}>
          <label style={labelStyle}>
            Email
            <input
              style={fieldStyle}
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="username"
            />
          </label>
          <label style={labelStyle}>
            Password
            <input
              style={fieldStyle}
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              maxLength={128}
              autoComplete="current-password"
            />
          </label>
          {message && <p style={errorStyle}>{message}</p>}
          <button
            type="submit"
            style={buttonStyle('#1d4ed8', submitting)}
            disabled={submitting}
          >
            {submitting ? 'Signing in...' : 'Sign in'}
          </button>
        </form>
      </div>
    </main>
  )
}

export default StaffApp