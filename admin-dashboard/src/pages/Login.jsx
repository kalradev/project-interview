import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { login, pingBackend } from '../api'
import { setToken } from '../App'
import LightRays from '../components/LightRays'
import './Login.css'

const SLOW_LOGIN_THRESHOLD_MS = 6000

export default function Login() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [slowMessage, setSlowMessage] = useState(false)
  const [cursor, setCursor] = useState({ x: 50, y: 50 })
  const [allowInput, setAllowInput] = useState(false)
  const pageRef = useRef(null)

  useEffect(() => {
    pingBackend()
  }, [])

  useEffect(() => {
    const el = pageRef.current
    if (!el) return
    function handleMove(e) {
      const rect = el.getBoundingClientRect()
      const x = ((e.clientX - rect.left) / rect.width) * 100
      const y = ((e.clientY - rect.top) / rect.height) * 100
      setCursor({ x, y })
    }
    el.addEventListener('mousemove', handleMove, { passive: true })
    return () => el.removeEventListener('mousemove', handleMove)
  }, [])

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setSlowMessage(false)
    setLoading(true)
    const slowTimer = setTimeout(() => setSlowMessage(true), SLOW_LOGIN_THRESHOLD_MS)
    try {
      const { access_token } = await login(email, password)
      setToken(access_token)
      navigate('/dashboard')
    } catch (err) {
      setError(err.message || 'Login failed')
    } finally {
      clearTimeout(slowTimer)
      setSlowMessage(false)
      setLoading(false)
    }
  }

  return (
    <div
      ref={pageRef}
      className="login-page"
      style={{ '--cursor-x': `${cursor.x}%`, '--cursor-y': `${cursor.y}%` }}
    >
      <div className="login-page-cursor-glow" aria-hidden />
      <div className="login-stars" aria-hidden>
        {(() => {
          const count = 48
          const positions = [
            [5, 12], [18, 8], [32, 15], [45, 6], [58, 22], [72, 11], [88, 18], [92, 35],
            [7, 28], [22, 42], [38, 38], [55, 52], [68, 45], [82, 58], [12, 55], [28, 62],
            [42, 72], [62, 68], [78, 75], [8, 78], [35, 85], [52, 82], [72, 88], [95, 65],
            [15, 92], [48, 95], [85, 42], [3, 45], [25, 25], [75, 28], [50, 35], [33, 48],
            [65, 55], [10, 65], [55, 78], [90, 82], [18, 35], [42, 18], [88, 52], [5, 58],
            [60, 12], [28, 72], [72, 38], [12, 48], [48, 62], [82, 22], [35, 92], [95, 78],
          ]
          return positions.slice(0, count).map(([left, top], i) => (
            <span
              key={i}
              className="login-star"
              style={{
                left: `${left}%`,
                top: `${top}%`,
                animationDelay: `${(i * 0.7 + (i % 5) * 2) % 12}s`,
                animationDuration: `${2.5 + (i % 4) * 0.8}s`,
              }}
            />
          ))
        })()}
      </div>
      <div className="login-balls" aria-hidden>
        {[...Array(36)].map((_, i) => (
          <span key={i} className={`login-ball login-ball-${i + 1}`} />
        ))}
      </div>
      <div className="login-bg-blob login-bg-blob-1" aria-hidden />
      <div className="login-bg-blob login-bg-blob-2" aria-hidden />
      <div className="login-bg-blob login-bg-blob-3" aria-hidden />
      <div className="login-bg-blob login-bg-blob-4" aria-hidden />
      <div className="login-page-cursor-glow login-page-cursor-glow-2" aria-hidden />
      <div className="login-page-light-rays">
        <LightRays
          raysOrigin="top-center"
          raysColor="#ffffff"
          raysSpeed={1.2}
          lightSpread={0.4}
          rayLength={2.6}
          followMouse={true}
          mouseInfluence={0.1}
          noiseAmount={0}
          distortion={0.02}
          className="login-rays"
          pulsating={true}
          fadeDistance={1}
          saturation={0.95}
        />
      </div>
      <div className="login-card">
        <div className="login-logo-wrap">
          <img src="/agent.png" alt="Interview Admin" className="login-logo" />
        </div>
        <h1>Interview Agent</h1>
        <p className="login-welcome">Welcome</p>
        <p className="login-sub">Sign in to manage candidates and resumes</p>
        <form onSubmit={handleSubmit} autoComplete="off">
          <label>
            Email
            <input
              type="email"
              name="login-email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              onFocus={() => setAllowInput(true)}
              placeholder="Enter your email"
              required
              autoComplete="off"
              readOnly={!allowInput}
              aria-readonly={!allowInput}
            />
          </label>
          <label className="login-password-wrap">
            Password
            <span className="login-password-field">
              <input
                type={showPassword ? 'text' : 'password'}
                name="login-pwd"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                onFocus={() => setAllowInput(true)}
                placeholder="Enter your password"
                required
                autoComplete="off"
                readOnly={!allowInput}
                aria-readonly={!allowInput}
              />
              <button
                type="button"
                className="login-password-toggle"
                onClick={() => setShowPassword((v) => !v)}
                tabIndex={0}
                aria-label={showPassword ? 'Hide password' : 'Show password'}
                title={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? (
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                    <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                    <line x1="1" y1="1" x2="23" y2="23" />
                  </svg>
                ) : (
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                    <circle cx="12" cy="12" r="3" />
                  </svg>
                )}
              </button>
            </span>
          </label>
          {error && <p className="login-error">{error}</p>}
          {loading && slowMessage && (
            <p className="login-slow-hint">Server is waking up — please wait a moment.</p>
          )}
          <button type="submit" disabled={loading}>
            {loading ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
      </div>
    </div>
  )
}
