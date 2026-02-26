import { useTabSwitchMonitor } from './hooks/useTabSwitchMonitor'
import './App.css'

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

function InterviewPage() {
  return (
    <div className="interview-page">
      <header className="interview-header">
        <h1>Interview in progress</h1>
        <p className="subtitle">
          Do not leave this window. Leaving the screen will result in a warning, then disqualification.
        </p>
      </header>
      <main className="interview-main">
        <div className="interview-placeholder">
          <p>Interview content will appear here (e.g. questions, timer, camera).</p>
          <p>This app runs in fullscreen. Do not switch to other apps or you will be warned, then disqualified.</p>
        </div>
      </main>
    </div>
  )
}

export default function App() {
  const { showWarning, isDisqualified, dismissWarning } = useTabSwitchMonitor()

  if (isDisqualified) {
    return <DisqualifiedScreen />
  }

  return (
    <>
      <InterviewPage />
      {showWarning && <WarningModal onDismiss={dismissWarning} />}
    </>
  )
}
