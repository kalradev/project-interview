import { useState } from 'react'
import { useInterviewConfig } from '../context/InterviewConfig'
import './SetupScreen.css'

export function SetupScreen({ onStart }) {
  const { config, setConfig, isConnected } = useInterviewConfig()
  const [apiBaseUrl, setApiBaseUrl] = useState(config.apiBaseUrl)
  const [sessionId, setSessionId] = useState(config.sessionId)
  const [authToken, setAuthToken] = useState(config.authToken)
  const [error, setError] = useState('')

  const handleSaveAndStart = () => {
    setConfig({
      apiBaseUrl: apiBaseUrl.trim() || 'http://localhost:8000',
      sessionId: sessionId.trim(),
      authToken: authToken.trim(),
    })
    setError('')
    onStart()
  }

  const handleStandalone = () => {
    setConfig({ apiBaseUrl: '', sessionId: '', authToken: '' })
    setError('')
    onStart()
  }

  const canConnect = apiBaseUrl.trim() && sessionId.trim() && authToken.trim()

  return (
    <div className="setup-screen">
      <div className="setup-card">
        <h1>Interview setup</h1>
        <p className="setup-desc">
          Connect to the interview backend (optional). If you skip, the app runs in standalone mode and only tracks leaving the screen locally.
        </p>

        <label className="setup-label">
          API base URL
          <input
            type="url"
            className="setup-input"
            placeholder="http://localhost:8000"
            value={apiBaseUrl}
            onChange={(e) => setApiBaseUrl(e.target.value)}
          />
        </label>
        <label className="setup-label">
          Session ID (UUID)
          <input
            type="text"
            className="setup-input"
            placeholder="Session ID from backend"
            value={sessionId}
            onChange={(e) => setSessionId(e.target.value)}
          />
        </label>
        <label className="setup-label">
          Auth token (JWT)
          <input
            type="password"
            className="setup-input"
            placeholder="Bearer token (Admin/Interviewer)"
            value={authToken}
            onChange={(e) => setAuthToken(e.target.value)}
          />
        </label>

        {error && <p className="setup-error">{error}</p>}

        <div className="setup-actions">
          <button
            type="button"
            className="btn btn-primary"
            onClick={handleSaveAndStart}
            disabled={!canConnect}
          >
            Save and start (connected)
          </button>
          <button type="button" className="btn btn-secondary" onClick={handleStandalone}>
            Start in standalone mode
          </button>
        </div>

        {isConnected && (
          <p className="setup-hint">Current config is saved. Start connected to log events to the backend.</p>
        )}
      </div>
    </div>
  )
}
