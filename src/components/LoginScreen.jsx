import { useState } from 'react'
import { login, getCandidateMe, getOrCreateSession } from '../api/client'
import { useInterviewConfig } from '../context/InterviewConfig'
import './LoginScreen.css'

export function LoginScreen({ onLoggedInAsCandidate, onSkipToSetup }) {
  const { config, setConfig } = useInterviewConfig()
  const [apiBaseUrl, setApiBaseUrl] = useState(config.apiBaseUrl || 'http://localhost:8000')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

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
    <div className="login-screen">
      <div className="login-card">
        <div className="login-logo-wrap">
          <img src="/agent.png" alt="Interview Agent" className="login-logo" />
        </div>
        <h1>Interview Agent</h1>
        <p className="login-desc">Log in with the email and password sent to you for the interview.</p>
        <form onSubmit={handleLogin}>
          <label className="login-label">
            API URL
            <input
              type="url"
              className="login-input"
              value={apiBaseUrl}
              onChange={(e) => setApiBaseUrl(e.target.value)}
              placeholder="http://localhost:8000"
            />
          </label>
          <label className="login-label">
            Email
            <input
              type="email"
              className="login-input"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              placeholder="your@email.com"
            />
          </label>
          <label className="login-label">
            Password
            <div className="login-password-wrap">
              <input
                type={showPassword ? 'text' : 'password'}
                className="login-input login-input-password"
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
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Logging in…' : 'Log in & start interview'}
            </button>
            <button type="button" className="btn btn-secondary" onClick={onSkipToSetup}>
              Skip to setup (manual session)
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
