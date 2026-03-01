import { useState, useCallback, useEffect } from 'react'
import { useTabSwitchMonitor } from './hooks/useTabSwitchMonitor'
import { InterviewConfigProvider, useInterviewConfig } from './context/InterviewConfig'
import { LoginScreen } from './components/LoginScreen'
import { SetupScreen } from './components/SetupScreen'
import { PhotoCapture } from './components/PhotoCapture'
import { InterviewFlow } from './components/InterviewFlow'
import { logEvent, endSession, computeIntegrity } from './api/client'
import './App.css'

const EVENT_TAB_SWITCH = 'tab_switch'

function WarningModal({ onDismiss }) {
  return (
    <div className="modal-overlay" role="dialog" aria-modal="true" aria-labelledby="warning-title">
      <div className="modal">
        <h2 id="warning-title" className="modal-title">⚠️ Warning</h2>
        <p className="modal-text">
          You left the interview screen. Do not leave again or you will be <strong>disqualified</strong>.
        </p>
        <button type="button" className="btn btn-primary" onClick={onDismiss}>
          I understand
        </button>
      </div>
    </div>
  )
}

function DisqualifiedScreen() {
  return (
    <div className="disqualified-screen">
      <div className="disqualified-card">
        <span className="disqualified-icon">🚫</span>
        <h1>Disqualified</h1>
        <p>You have been disqualified for leaving the interview screen.</p>
        <p className="disqualified-note">Please contact support if you believe this was an error.</p>
      </div>
    </div>
  )
}

function InterviewApp() {
  const { config, isConnected } = useInterviewConfig()
  const [screen, setScreen] = useState('login') // login | setup | photo | interview
  const [candidateInfo, setCandidateInfo] = useState(null)

  const onLeave = useCallback(
    async (count, isDisqualified) => {
      if (!isConnected || !config.apiBaseUrl || !config.sessionId || !config.authToken) return
      try {
        await logEvent(
          config.apiBaseUrl,
          config.sessionId,
          EVENT_TAB_SWITCH,
          config.authToken,
          { leave_count: count, disqualified: isDisqualified },
          'high'
        )
        if (isDisqualified) {
          try {
            await endSession(config.apiBaseUrl, config.sessionId, config.authToken)
          } catch (_) {}
          try {
            await computeIntegrity(config.apiBaseUrl, config.sessionId, config.authToken, 0)
          } catch (_) {}
        }
      } catch (_) {}
    },
    [isConnected, config.apiBaseUrl, config.sessionId, config.authToken]
  )

  const { showWarning, isDisqualified, dismissWarning } = useTabSwitchMonitor({ onLeave })

  useEffect(() => {
    if (screen === 'interview' && window.electronAPI?.enterInterviewMode) {
      window.electronAPI.enterInterviewMode()
    }
  }, [screen])

  if (isDisqualified) {
    return <DisqualifiedScreen />
  }

  if (screen === 'login') {
    return (
      <LoginScreen
        onLoggedInAsCandidate={(info) => {
          setCandidateInfo(info)
          setScreen('photo')
        }}
        onSkipToSetup={() => setScreen('setup')}
      />
    )
  }

  if (screen === 'setup') {
    return (
      <SetupScreen
        onStart={() => setScreen('interview')}
      />
    )
  }

  if (screen === 'photo') {
    return (
      <PhotoCapture
        onDone={() => setScreen('interview')}
      />
    )
  }

  return (
    <>
      {config.jobRole && config.sessionId && config.authToken ? (
        <InterviewFlow onEnd={() => {}} />
      ) : (
        <div className="interview-page">
          <header className="interview-header">
            <h1>Interview in progress</h1>
            <p className="subtitle">Do not leave this window.</p>
          </header>
          <main className="interview-main">
            <div className="interview-placeholder">
              <p>Connect via Setup (session + token) or log in as a candidate to see questions.</p>
            </div>
          </main>
        </div>
      )}
      {showWarning && <WarningModal onDismiss={dismissWarning} />}
    </>
  )
}

export default function App() {
  return (
    <InterviewConfigProvider>
      <InterviewApp />
    </InterviewConfigProvider>
  )
}
