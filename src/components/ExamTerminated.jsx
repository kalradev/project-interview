import './ExamTerminated.css'

export function ExamTerminated() {
  return (
    <div className="exam-terminated">
      <div className="exam-terminated-card">
        <span className="exam-terminated-icon">🚫</span>
        <h1>Exam terminated</h1>
        <p>This exam was terminated due to a policy violation (e.g. exiting full screen or switching tabs too many times).</p>
        <p className="exam-terminated-note">If you believe this was an error, please contact support.</p>
      </div>
    </div>
  )
}
