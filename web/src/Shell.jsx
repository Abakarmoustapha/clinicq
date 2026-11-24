import { useState } from 'react'
import App from './App.jsx'
import ManageBooking from './ManageBooking.jsx'
import StaffApp from './StaffApp.jsx'

function tabStyle(active) {
  return {
    padding: '0.5rem 1rem',
    border: 'none',
    borderBottom: active ? '3px solid #1d4ed8' : '3px solid transparent',
    background: 'none',
    fontSize: '1rem',
    fontWeight: active ? 'bold' : 'normal',
    cursor: 'pointer',
  }
}

function Shell() {
  const [view, setView] = useState('book')

  return (
    <>
      <nav
        style={{
          maxWidth: 520,
          margin: '1rem auto 0',
          padding: '0 1rem',
          fontFamily: 'sans-serif',
          textAlign: 'left',
        }}
      >
        <button style={tabStyle(view === 'book')} onClick={() => setView('book')}>
          Book a visit
        </button>
        <button style={tabStyle(view === 'manage')} onClick={() => setView('manage')}>
          My booking
        </button>
        <button style={tabStyle(view === 'staff')} onClick={() => setView('staff')}>
          Staff
        </button>
      </nav>
      <div hidden={view !== 'book'}>
        <App />
      </div>
      <div hidden={view !== 'manage'}>
        <ManageBooking />
      </div>
      {view === 'staff' && <StaffApp />}
    </>
  )
}

export default Shell