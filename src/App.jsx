import { useState, useCallback, useEffect } from 'react'
import { useTabSwitchMonitor, WARNINGS_BEFORE_DISQUALIFY } from './hooks/useTabSwitchMonitor'
import { InterviewConfigProvider, useInterviewConfig } from './context/InterviewConfig'
import { LoginScreen } from './components/LoginScreen'
import { SetupScreen } from './components/SetupScreen'
import { PhotoCapture } from './components/PhotoCapture'
import { WaitForInterview } from './components/WaitForInterview'
import { InterviewFlow } from './components/InterviewFlow'
import { logEvent, endSession, computeIntegrity } from './api/client'
import './App.css'

const EVENT_TAB_SWITCH = 'tab_switch'
const EVENT_COPY = 'copy_event'

function WarningModal({ onDismiss, leaveCount }) {
  const which = Math.min(leaveCount, WARNINGS_BEFORE_DISQUALIFY)
  const remaining = WARNINGS_BEFORE_DISQUALIFY - which
  return (
    <div className="modal-overlay" role="dialog" aria-modal="true" aria-labelledby="warning-title">
      <div className="modal">
        <h2 id="warning-title" className="modal-title">⚠️ Warning {which} of {WARNINGS_BEFORE_DISQUALIFY}</h2>
        <p className="modal-text">
          You attempted to leave the interview (e.g. Alt+F4 or clicking outside the window). Do not do this again.
        </p>
        <p className="modal-text modal-text-highlight">
          {remaining > 0 ? (
            <strong>You will get {remaining} more warning{remaining !== 1 ? 's' : ''} before disqualification.</strong>
          ) : (
            <strong>Next time you will be disqualified.</strong>
          )}
        </p>
        <button type="button" className="btn btn-primary" onClick={onDismiss}>
          I understand
        </button>
      </div>
    </div>
  )
}

function DisqualifiedScreen() {
  const handleClose = () => {
    if (window.electronAPI?.requestCloseInterview) {
      window.electronAPI.requestCloseInterview()
    }
  }
  return (
    <div className="disqualified-screen">
      <div className="disqualified-card">
        <span className="disqualified-icon">🚫</span>
        <h1>Disqualified</h1>
        <p>You have been disqualified for leaving the interview screen more than {WARNINGS_BEFORE_DISQUALIFY} times.</p>
        <p className="disqualified-note">Please contact support if you believe this was an error.</p>
        {window.electronAPI?.requestCloseInterview && (
          <button type="button" className="btn btn-primary disqualified-close-btn" onClick={handleClose}>
            Close interview
          </button>
        )}
      </div>
    </div>
  )
}

function InterviewApp() {
  const { config, isConnected } = useInterviewConfig()
  const [screen, setScreen] = useState('login') // login | setup | photo | ready | interview
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

  // Only count "leave screen" during the actual interview; ignore blur on login/setup/photo so candidate cannot be disqualified before logging in
  const interviewActive = screen === 'interview'
  const { showWarning, isDisqualified, dismissWarning, tabSwitchCount } = useTabSwitchMonitor({ onLeave, enabled: interviewActive })

  useEffect(() => {
    if (screen === 'interview' && window.electronAPI?.enterInterviewMode) {
      window.electronAPI.enterInterviewMode()
    }
  }, [screen])

  // Prevent copy/cut and log as suspicious when in interview (reduces cheating via copy-paste/extensions)
  useEffect(() => {
    if (screen !== 'interview' || !config.apiBaseUrl || !config.sessionId || !config.authToken) return
    const handleCopy = (e) => {
      e.preventDefault()
      if (isConnected) {
        logEvent(config.apiBaseUrl, config.sessionId, EVENT_COPY, config.authToken, { action: 'copy' }, 'high').catch(() => {})
      }
    }
    const handleCut = (e) => {
      e.preventDefault()
      if (isConnected) {
        logEvent(config.apiBaseUrl, config.sessionId, EVENT_COPY, config.authToken, { action: 'cut' }, 'high').catch(() => {})
      }
    }
    const handleContextMenu = (e) => e.preventDefault()
    document.addEventListener('copy', handleCopy)
    document.addEventListener('cut', handleCut)
    document.addEventListener('contextmenu', handleContextMenu)
    return () => {
      document.removeEventListener('copy', handleCopy)
      document.removeEventListener('cut', handleCut)
      document.removeEventListener('contextmenu', handleContextMenu)
    }
  }, [screen, config.apiBaseUrl, config.sessionId, config.authToken, isConnected])

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
        onDone={() => setScreen('ready')}
      />
    )
  }

  if (screen === 'ready') {
    return (
      <WaitForInterview
        candidateInfo={candidateInfo}
        onJoin={() => setScreen('interview')}
      />
    )
  }

  return (
    <>
      <div className="interview-container">
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
      </div>
      {showWarning && <WarningModal onDismiss={dismissWarning} leaveCount={tabSwitchCount} />}
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
