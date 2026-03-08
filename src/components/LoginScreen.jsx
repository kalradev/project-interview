import { useState, useRef, useEffect } from 'react'
import { login, getCandidateMe, getOrCreateSession } from '../api/client'
import { useInterviewConfig } from '../context/InterviewConfig'
import LightRays from './LightRays'
import './LoginScreen.css'

export function LoginScreen({ onLoggedInAsCandidate, onSkipToSetup }) {
  const { config, setConfig } = useInterviewConfig()
  const [apiBaseUrl, setApiBaseUrl] = useState(config.apiBaseUrl || 'http://localhost:8000')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [cursor, setCursor] = useState({ x: 50, y: 50 })
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

  const handleLogin = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const base = apiBaseUrl.trim() || 'http://localhost:8000'
      const { access_token } = await login(base, email.trim(), password)
      const profile = await getCandidateMe(base, access_token)
      if (profile && profile.job_role) {
        const sessionData = await getOrCreateSession(base, access_token)
        setConfig({
          apiBaseUrl: base,
          sessionId: sessionData.session_id,
          authToken: access_token,
          jobRole: sessionData.job_role || '',
          techStack: sessionData.tech_stack || [],
        })
        onLoggedInAsCandidate({
          jobRole: sessionData.job_role,
          techStack: sessionData.tech_stack || [],
          email: profile.email,
          interviewScheduledAt: profile.interview_scheduled_at || null,
        })
        return
      }
      setError('No candidate profile found. Use Setup to enter session manually, or contact support.')
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
          <img src={`${import.meta.env.BASE_URL}agent.png`} alt="Interview Agent" className="login-logo" />
        </div>
        <h1>Interview Agent</h1>
        <p className="login-welcome">Welcome</p>
        <p className="login-desc">Log in with the email and password sent to you for the interview.</p>
        <form onSubmit={handleLogin}>
          <label>
            API URL
            <input
              type="url"
              value={apiBaseUrl}
              onChange={(e) => setApiBaseUrl(e.target.value)}
              placeholder="http://localhost:8000"
            />
          </label>
          <label>
            Email
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              placeholder="your@email.com"
            />
          </label>
          <label>
            Password
            <div className="login-password-wrap">
              <input
                type={showPassword ? 'text' : 'password'}
                className="login-input-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                placeholder="Password from invite email"
              />
              <button
                type="button"
                className="login-password-toggle"
                onClick={() => setShowPassword((v) => !v)}
                aria-label={showPassword ? 'Hide password' : 'Show password'}
                title={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? (
                  <span className="login-password-icon" aria-hidden>🙈</span>
                ) : (
                  <span className="login-password-icon" aria-hidden>👁</span>
                )}
              </button>
            </div>
          </label>
          {error && <p className="login-error">{error}</p>}
          <div className="login-actions">
            <button type="submit" className="btn-primary" disabled={loading}>
              {loading ? 'Logging in…' : 'Log in'}
            </button>
            <button type="button" className="btn-secondary" onClick={onSkipToSetup}>
              Skip to setup (manual session)
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
