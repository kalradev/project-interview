import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { login } from '../api'
import { setToken } from '../App'
import LightRays from '../components/LightRays'
import './Login.css'

export default function Login() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [cursor, setCursor] = useState({ x: 50, y: 50 })
  const [allowInput, setAllowInput] = useState(false)
  const pageRef = useRef(null)

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
    setLoading(true)
    try {
      const { access_token } = await login(email, password)
      setToken(access_token)
      navigate('/dashboard')
    } catch (err) {
      setError(err.message || 'Login failed')
    } finally {
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
          lightSpread={0.35}
          rayLength={3}
          followMouse={true}
          mouseInfluence={0.12}
          noiseAmount={0}
          distortion={0.03}
          className="login-rays"
          pulsating={true}
          fadeDistance={1.2}
          saturation={1}
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
              placeholder="admin@example.com"
              required
              autoComplete="off"
              readOnly={!allowInput}
              aria-readonly={!allowInput}
            />
          </label>
          <label>
            Password
            <input
              type="password"
              name="login-pwd"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              onFocus={() => setAllowInput(true)}
              placeholder="••••••••"
              required
              autoComplete="new-password"
              readOnly={!allowInput}
              aria-readonly={!allowInput}
            />
          </label>
          {error && <p className="login-error">{error}</p>}
          <button type="submit" disabled={loading}>
            {loading ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
      </div>
    </div>
  )
}
