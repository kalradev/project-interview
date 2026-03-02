import { useState, useCallback } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { signup } from '../api'
import { setToken } from '../App'
import './Signup.css'

const GRID_COLS = 24
const GRID_ROWS = 18

export default function Signup() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [fullName, setFullName] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [mouse, setMouse] = useState({ x: 0, y: 0 })

  const handleMouseMove = useCallback((e) => {
    setMouse({ x: e.clientX, y: e.clientY })
  }, [])

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const { access_token } = await signup(email, password, fullName)
      setToken(access_token)
      navigate('/dashboard')
    } catch (err) {
      setError(err.message || 'Sign up failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      className="signup-page"
      onMouseMove={handleMouseMove}
      style={
        {
          '--mouse-x': `${mouse.x}px`,
          '--mouse-y': `${mouse.y}px`,
        }
      }
    >
      {/* Chess-board grid background */}
      <div className="signup-grid-bg" aria-hidden>
        {Array.from({ length: GRID_ROWS * GRID_COLS }, (_, i) => {
          const row = Math.floor(i / GRID_COLS)
          const col = i % GRID_COLS
          const isLight = (row + col) % 2 === 0
          return (
            <div
              key={i}
              className={`signup-grid-cell ${isLight ? 'signup-grid-cell--light' : 'signup-grid-cell--dark'}`}
            />
          )
        })}
      </div>
      {/* Cursor-following glow */}
      <div className="signup-cursor-glow" aria-hidden />

      <div className="signup-card">
        <div className="signup-logo-wrap">
          <img src="/agent.png" alt="Interview Admin" className="signup-logo" />
        </div>
        <h1>Create account</h1>
        <p className="signup-sub">Register as the first administrator</p>
        <form onSubmit={handleSubmit}>
          <label>
            Full name (optional)
            <input
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="Jane Doe"
              autoComplete="name"
            />
          </label>
          <label>
            Email <span className="req">*</span>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="admin@example.com"
              required
              autoComplete="email"
            />
          </label>
          <label>
            Password <span className="req">*</span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
              autoComplete="new-password"
              minLength={6}
            />
          </label>
          {error && <p className="signup-error">{error}</p>}
          <button type="submit" disabled={loading}>
            {loading ? 'Creating account…' : 'Sign up'}
          </button>
        </form>
        <p className="signup-footer">
          Already have an account? <Link to="/">Sign in</Link>
        </p>
      </div>
    </div>
  )
}
