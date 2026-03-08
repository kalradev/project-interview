import { useState, useEffect } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getToken } from '../App'
import { getCandidate, getReport, candidateAction, apiBase } from '../api'
import './CandidateProfile.css'

function formatDate(d) {
  if (!d) return '—'
  return new Date(d).toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' })
}

function formatDuration(startedAt, endedAt) {
  if (!startedAt || !endedAt) return null
  const start = new Date(startedAt).getTime()
  const end = new Date(endedAt).getTime()
  const mins = Math.round((end - start) / 60000)
  if (mins < 60) return `${mins} min`
  const h = Math.floor(mins / 60)
  const m = mins % 60
  return m ? `${h}h ${m}min` : `${h}h`
}

/** Prefer real name; if missing or generic "Candidate", use email prefix. */
function displayName(candidate) {
  const name = (candidate?.full_name || '').trim()
  if (name && name.toLowerCase() !== 'candidate') return name
  if (candidate?.email && candidate.email.includes('@')) return candidate.email.split('@')[0]
  return '—'
}

export default function CandidateProfile() {
  const { id } = useParams()
  const token = getToken()
  const [candidate, setCandidate] = useState(null)
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [actioning, setActioning] = useState(false)

  useEffect(() => {
    let cancelled = false
    async function load() {
      if (!id) return
      setLoading(true)
      setError('')
      try {
        const [c, r] = await Promise.all([
          getCandidate(token, id),
          getReport(token, id).catch(() => null),
        ])
        if (!cancelled) {
          setCandidate(c)
          setReport(r)
        }
      } catch (err) {
        if (!cancelled) setError(err.message || 'Failed to load candidate')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [id, token])

  async function handleAction(status) {
    setActioning(true)
    setError('')
    try {
      await candidateAction(token, id, status)
      if (candidate) setCandidate({ ...candidate, status })
    } catch (err) {
      setError(err.message || 'Action failed')
    } finally {
      setActioning(false)
    }
  }

  if (loading) {
    return (
      <div className="candidate-profile-page">
        <div className="candidate-profile-header-bar">
          <header className="candidate-profile-header">
            <h1>Candidate profile</h1>
            <Link to="/dashboard" className="btn btn-outline">← Resumes &amp; Candidates</Link>
          </header>
        </div>
        <main className="candidate-profile-main">
          <p className="candidate-profile-loading">Loading…</p>
        </main>
      </div>
    )
  }

  if (error && !candidate) {
    return (
      <div className="candidate-profile-page">
        <div className="candidate-profile-header-bar">
          <header className="candidate-profile-header">
            <h1>Candidate profile</h1>
            <Link to="/dashboard" className="btn btn-outline">← Resumes &amp; Candidates</Link>
          </header>
        </div>
        <main className="candidate-profile-main">
          <p className="candidate-profile-error">{error}</p>
        </main>
      </div>
    )
  }

  if (!candidate) {
    return (
      <div className="candidate-profile-page">
        <div className="candidate-profile-header-bar">
          <header className="candidate-profile-header">
            <h1>Candidate profile</h1>
            <Link to="/dashboard" className="btn btn-outline">← Resumes &amp; Candidates</Link>
          </header>
        </div>
        <main className="candidate-profile-main">
          <p className="candidate-profile-error">Candidate not found.</p>
        </main>
      </div>
    )
  }

  return (
    <div className="candidate-profile-page">
      <div className="candidate-profile-header-bar">
        <header className="candidate-profile-header">
          <h1>Candidate profile</h1>
          <Link to="/dashboard" className="btn btn-outline">← Resumes &amp; Candidates</Link>
        </header>
      </div>

      <main className="candidate-profile-main">
        {error && <p className="candidate-profile-error">{error}</p>}

        <section className="candidate-profile-card candidate-details-card">
          <h2>Candidate details</h2>
          <div className="candidate-details-grid">
            <div className="candidate-photo-block">
              {candidate.photo_url ? (
                <img src={`${apiBase}${candidate.photo_url}`} alt="" className="candidate-profile-photo" />
              ) : (
                <div className="candidate-profile-photo-placeholder">No photo</div>
              )}
            </div>
            <div className="candidate-details-fields">
              <p><strong>Name:</strong> {displayName(candidate)}</p>
              <p><strong>Email:</strong> {candidate.email}</p>
              <p><strong>Job role:</strong> {candidate.job_role}</p>
              <p><strong>Status:</strong> <span className={`status-badge status-${candidate.status}`}>{candidate.status}</span></p>
              {candidate.ats_score != null && <p><strong>ATS score:</strong> {candidate.ats_score}</p>}
              <p><strong>Invited:</strong> {formatDate(candidate.invited_at)}</p>
              {candidate.tech_stack?.length > 0 && (
                <p className="tech-stack-wrap">
                  <strong>Tech stack:</strong>
                  <span className="tech-stack-pills">
                    {candidate.tech_stack.map((tech, i) => (
                      <span key={i} className="tech-stack-pill">{tech.trim()}</span>
                    ))}
                  </span>
                </p>
              )}
              {candidate.links?.length > 0 && (
                <p><strong>Links:</strong>{' '}
                  {candidate.links.map((url, i) => (
                    <a key={i} href={url} target="_blank" rel="noopener noreferrer">{url}</a>
                  ))}
                </p>
              )}
            </div>
          </div>
          {candidate.projects?.length > 0 && (
            <div className="candidate-detail-block">
              <strong>Projects</strong>
              <ul>{candidate.projects.map((p, i) => <li key={i}>{p}</li>)}</ul>
            </div>
          )}
          {candidate.certificates?.length > 0 && (
            <div className="candidate-detail-block">
              <strong>Certificates</strong>
              <ul>{candidate.certificates.map((cert, i) => <li key={i}>{cert}</li>)}</ul>
            </div>
          )}
          {candidate.experience?.length > 0 && (
            <div className="candidate-detail-block">
              <strong>Experience</strong>
              <ul>{candidate.experience.map((e, i) => <li key={i}>{e}</li>)}</ul>
            </div>
          )}
          {(candidate.status === 'completed' || candidate.status === 'invited') && (
            <div className="candidate-actions-row">
              <button type="button" className="btn btn-outline btn-sm" onClick={() => handleAction('next_round')} disabled={actioning}>Next round</button>
              <button type="button" className="btn btn-sm green" onClick={() => handleAction('selected')} disabled={actioning}>Select</button>
              <button type="button" className="btn btn-sm red" onClick={() => handleAction('rejected')} disabled={actioning}>Reject</button>
            </div>
          )}
        </section>

        {(candidate.ats_details?.matched_skills?.length > 0 || candidate.ats_details?.missing_skills?.length > 0 || candidate.ats_details?.suggestions?.length > 0) && (
          <section className="candidate-profile-card candidate-ats-card">
            <h2>ATS analysis</h2>
            <div className="candidate-ats-details">
              {candidate.ats_details.matched_skills?.length > 0 && (
                <p><strong>Matched skills:</strong> {candidate.ats_details.matched_skills.join(', ')}</p>
              )}
              {candidate.ats_details.missing_skills?.length > 0 && (
                <p><strong>Missing skills:</strong> {candidate.ats_details.missing_skills.join(', ')}</p>
              )}
              {candidate.ats_details.suggestions?.length > 0 && (
                <>
                  <p><strong>Suggestions:</strong></p>
                  <ul>{candidate.ats_details.suggestions.map((s, i) => <li key={i}>{s}</li>)}</ul>
                </>
              )}
            </div>
          </section>
        )}

        <section className="candidate-profile-card interview-report-card">
          <h2>Interview &amp; report</h2>
          {!report ? (
            <p className="no-report-msg">No interview report yet for this candidate.</p>
          ) : (
            <>
              <p><strong>Job role (interview):</strong> {report.job_role}</p>

              <div className="report-timing-block">
                <h4>Interview timing</h4>
                {candidate.interview_scheduled_at && (
                  <p><strong>Scheduled:</strong> {formatDate(candidate.interview_scheduled_at)}</p>
                )}
                {report.started_at && <p><strong>Started:</strong> {formatDate(report.started_at)}</p>}
                {report.ended_at && <p><strong>Ended:</strong> {formatDate(report.ended_at)}</p>}
                {formatDuration(report.started_at, report.ended_at) && (
                  <p><strong>Duration:</strong> {formatDuration(report.started_at, report.ended_at)}</p>
                )}
              </div>

              {report.agent_report && (
                <div className="report-agent-block">
                  <h4>Agent result (accuracy &amp; communication)</h4>
                  {report.agent_report.accuracy_score != null && (
                    <p><strong>Accuracy:</strong> {report.agent_report.accuracy_score}%</p>
                  )}
                  {report.agent_report.communication_score != null && (
                    <p><strong>Communication score:</strong> {report.agent_report.communication_score}%</p>
                  )}
                  {report.agent_report.summary && (
                    <p><strong>Summary:</strong> {report.agent_report.summary}</p>
                  )}
                  {report.agent_report.interrupt_count != null && report.agent_report.interrupt_count > 0 && (
                    <p><strong>Times user cut agent:</strong> {report.agent_report.interrupt_count}</p>
                  )}
                </div>
              )}

              {report.face_lip_status && (
                <p><strong>Face &amp; lip check:</strong> <span className={`face-lip face-lip-${report.face_lip_status}`}>{report.face_lip_status}</span></p>
              )}
              {report.integrity_score != null && <p><strong>Integrity score:</strong> {report.integrity_score}</p>}
              {report.integrity_risk && <p><strong>Risk:</strong> {report.integrity_risk}</p>}
              {report.summary && !report.agent_report?.summary && <p><strong>Summary:</strong> {report.summary}</p>}

              <div className="report-photos">
                <h4>Photos</h4>
                {report.photo_url ? (
                  <div className="report-photo-block">
                    <span>Before interview</span>
                    <img src={`${apiBase}${report.photo_url}`} alt="Before interview" />
                  </div>
                ) : (
                  <p className="photo-placeholder">No before-interview photo.</p>
                )}
                <div className="report-photo-block">
                  <span>During interview</span>
                  {report.session_photos?.length > 0 ? (
                    <div className="session-photos-grid">
                      {report.session_photos.map((p) => (
                        <img key={p.id} src={`${apiBase}${p.photo_url}`} alt={`Captured ${p.captured_at}`} />
                      ))}
                    </div>
                  ) : (
                    <p className="photo-placeholder">No photos captured during interview yet.</p>
                  )}
                </div>
              </div>

              {report.video_url && (
                <div className="report-video">
                  <h4>Interview video</h4>
                  <video controls src={`${apiBase}${report.video_url}`} style={{ maxWidth: '100%' }}>
                    Your browser does not support video.
                  </video>
                </div>
              )}

              {report.exchanges?.length > 0 && (
                <div className="report-exchanges">
                  <h4>Q&amp;A</h4>
                  {report.exchanges.map((ex, i) => (
                    <div key={i} className="exchange">
                      <p><strong>Q:</strong> {ex.question_text}</p>
                      <p><strong>A:</strong> {ex.answer_text}</p>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </section>
      </main>
    </div>
  )
}
