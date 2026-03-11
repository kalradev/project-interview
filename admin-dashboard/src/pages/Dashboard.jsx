import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { getToken, logout } from '../App'
import { listCandidates, addCandidate, getReport, candidateAction, deleteCandidate, extractResumeDetails, extractResumeFromFile, apiBase } from '../api'
import Orb from '../components/Orb'
import './Dashboard.css'

const CANDIDATES_CACHE_KEY = 'dashboard_candidates_cache'
const CANDIDATES_CACHE_TTL_MS = 2 * 60 * 1000 // 2 minutes

function getCachedCandidates(statusFilter) {
  try {
    const key = `${CANDIDATES_CACHE_KEY}_${statusFilter || 'all'}`
    const raw = sessionStorage.getItem(key)
    if (!raw) return null
    const { data, at } = JSON.parse(raw)
    if (!Array.isArray(data) || Date.now() - at > CANDIDATES_CACHE_TTL_MS) return null
    return data
  } catch {
    return null
  }
}

function setCachedCandidates(statusFilter, data) {
  try {
    const key = `${CANDIDATES_CACHE_KEY}_${statusFilter || 'all'}`
    sessionStorage.setItem(key, JSON.stringify({ data, at: Date.now() }))
  } catch (_) {}
}

function formatDate(d) {
  if (!d) return '—'
  return new Date(d).toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' })
}

export default function Dashboard() {
  const token = getToken()
  const [candidates, setCandidates] = useState(() => getCachedCandidates('') ?? [])
  const [loading, setLoading] = useState(!getCachedCandidates(''))
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState('')
  const [report, setReport] = useState(null)
  const [statusFilter, setStatusFilter] = useState('')

  // Add resume form
  const [showForm, setShowForm] = useState(false)
  const [formEmail, setFormEmail] = useState('')
  const [formName, setFormName] = useState('')
  const [formJobRole, setFormJobRole] = useState('')
  const [formTechStack, setFormTechStack] = useState('')
  const [formResumeText, setFormResumeText] = useState('')
  const [formResumeUrl, setFormResumeUrl] = useState('')
  const [formLinksGitHub, setFormLinksGitHub] = useState('')
  const [formLinksLinkedIn, setFormLinksLinkedIn] = useState('')
  const [formLinksPortfolio, setFormLinksPortfolio] = useState('')
  const [formLinksOther, setFormLinksOther] = useState('')
  const [formProjects, setFormProjects] = useState([]) // string[]: one item per project (multi-line allowed)
  const [formCertificates, setFormCertificates] = useState('')
  const [formExperience, setFormExperience] = useState([]) // string[]: one item per experience entry
  const [formAtsScore, setFormAtsScore] = useState(null) // ATS score 0–100 from extract (null until extracted)
  const [formJobDescription, setFormJobDescription] = useState('') // Optional job description for ATS scoring
  const [formMatchedSkills, setFormMatchedSkills] = useState([])
  const [formMissingSkills, setFormMissingSkills] = useState([])
  const [formSuggestions, setFormSuggestions] = useState([])
  const [sendInvite, setSendInvite] = useState(true) // Toggle: admin decides to take interview
  const [formInterviewScheduledAt, setFormInterviewScheduledAt] = useState('') // Optional: interview date/time (datetime-local string, empty = next slot)
  const [formSubmitting, setFormSubmitting] = useState(false)
  const [formExtractLoading, setFormExtractLoading] = useState(false)
  const [formExtractFileLoading, setFormExtractFileLoading] = useState(false)
  const [formUploadedFile, setFormUploadedFile] = useState(null) // selected file for upload
  const [formExtractSuccess, setFormExtractSuccess] = useState(false) // show "Details extracted" after parse
  const [formSuccess, setFormSuccess] = useState('')
  const [deletingId, setDeletingId] = useState(null)

  const loadCandidates = async (background = false) => {
    const cached = getCachedCandidates(statusFilter)
    if (!background) {
      setLoading(!cached)
      setError('')
    } else {
      setRefreshing(true)
    }
    try {
      const params = statusFilter ? { status: statusFilter } : {}
      const data = await listCandidates(token, params)
      setCandidates(data)
      setCachedCandidates(statusFilter, data)
    } catch (err) {
      if (!background) setError(err.message || 'Failed to load candidates')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => {
    const cached = getCachedCandidates(statusFilter)
    if (cached && cached.length >= 0) {
      setCandidates(cached)
      setLoading(false)
      loadCandidates(true)
    } else {
      setCandidates([])
      loadCandidates(false)
    }
  }, [token, statusFilter])

  function clearExtractedFormFields() {
    setFormEmail('')
    setFormName('')
    setFormJobRole('')
    setFormTechStack('')
    setFormLinksGitHub('')
    setFormLinksLinkedIn('')
    setFormLinksPortfolio('')
    setFormLinksOther('')
    setFormProjects([])
    setFormCertificates('')
    setFormExperience([])
    setFormAtsScore(null)
    setFormMatchedSkills([])
    setFormMissingSkills([])
    setFormSuggestions([])
  }

  function fillFormFromExtract(data) {
    setFormEmail(data.email ?? '')
    setFormName(data.full_name ?? '')
    setFormJobRole(data.job_role ?? '')
    setFormTechStack(Array.isArray(data.tech_stack) ? data.tech_stack.join(', ') : (data.tech_stack ?? ''))
    setFormLinksGitHub(Array.isArray(data.links_github) ? data.links_github.join('\n') : (data.links_github ?? ''))
    setFormLinksLinkedIn(Array.isArray(data.links_linkedin) ? data.links_linkedin.join('\n') : (data.links_linkedin ?? ''))
    setFormLinksPortfolio(Array.isArray(data.links_portfolio) ? data.links_portfolio.join('\n') : (data.links_portfolio ?? ''))
    setFormLinksOther(Array.isArray(data.links_other) ? data.links_other.join('\n') : (data.links_other ?? ''))
    setFormProjects(Array.isArray(data.projects) ? data.projects : (data.projects ? [data.projects] : []))
    setFormCertificates(Array.isArray(data.certificates) ? data.certificates.join('\n') : (data.certificates ?? ''))
    setFormExperience(Array.isArray(data.experience) ? data.experience : (data.experience ? [data.experience] : []))
    if (data.resume_text) setFormResumeText(data.resume_text)
    setFormAtsScore(typeof data.ats_score === 'number' ? data.ats_score : null)
    setFormMatchedSkills(Array.isArray(data.matched_skills) ? data.matched_skills : [])
    setFormMissingSkills(Array.isArray(data.missing_skills) ? data.missing_skills : [])
    setFormSuggestions(Array.isArray(data.suggestions) ? data.suggestions : [])
    setFormExtractSuccess(true)
  }

  async function handleExtractResume() {
    if (!formResumeText.trim()) {
      setError('Paste resume text first, then click Extract.')
      return
    }
    setFormExtractLoading(true)
    setError('')
    setFormExtractSuccess(false)
    clearExtractedFormFields()
    try {
      const data = await extractResumeDetails(token, formResumeText, formJobDescription)
      fillFormFromExtract(data)
    } catch (err) {
      setError(err.message || 'Extract failed')
    } finally {
      setFormExtractLoading(false)
    }
  }

  async function handleExtractFromFile() {
    if (!formUploadedFile) {
      setError('Select a PDF or DOCX file first.')
      return
    }
    setFormExtractFileLoading(true)
    setError('')
    setFormExtractSuccess(false)
    clearExtractedFormFields()
    try {
      const data = await extractResumeFromFile(getToken(), formUploadedFile, formJobDescription)
      fillFormFromExtract(data)
      setFormUploadedFile(null)
    } catch (err) {
      setError(err.message || 'Extract from file failed')
    } finally {
      setFormExtractFileLoading(false)
    }
  }

  async function handleAddResume(e) {
    e.preventDefault()
    setFormSubmitting(true)
    setFormSuccess('')
    setError('')
    try {
      const res = await addCandidate(token, {
        email: formEmail,
        full_name: formName || undefined,
        job_role: formJobRole,
        tech_stack: formTechStack ? formTechStack.split(',').map((s) => s.trim()).filter(Boolean) : undefined,
        resume_text: formResumeText || undefined,
        resume_url: formResumeUrl || undefined,
        links: (() => {
          const trim = (s) => s.trim()
          const urls = [
            ...(formLinksGitHub ? formLinksGitHub.split('\n').map(trim).filter(Boolean) : []),
            ...(formLinksLinkedIn ? formLinksLinkedIn.split('\n').map(trim).filter(Boolean) : []),
            ...(formLinksPortfolio ? formLinksPortfolio.split('\n').map(trim).filter(Boolean) : []),
            ...(formLinksOther ? formLinksOther.split('\n').map(trim).filter(Boolean) : []),
          ]
          return urls.length ? urls : undefined
        })(),
        projects: formProjects.length ? formProjects.map((s) => s.trim()).filter(Boolean) : undefined,
        certificates: formCertificates ? formCertificates.split('\n').map((s) => s.trim()).filter(Boolean) : undefined,
        experience: formExperience.length ? formExperience.map((s) => s.trim()).filter(Boolean) : undefined,
        source: 'manual',
        send_email: sendInvite,
        interview_scheduled_at: formInterviewScheduledAt ? new Date(formInterviewScheduledAt).toISOString() : undefined,
        ats_score: formAtsScore != null ? formAtsScore : undefined,
        matched_skills: formMatchedSkills?.length ? formMatchedSkills : undefined,
        missing_skills: formMissingSkills?.length ? formMissingSkills : undefined,
        suggestions: formSuggestions?.length ? formSuggestions : undefined,
      })
      if (res.email_sent === false && (sendInvite || (formAtsScore != null && formAtsScore > 60))) {
        setFormSuccess('Candidate added but invite email could not be sent. Check Brevo/SMTP in server .env.')
      } else if (res.email_sent) {
        setFormSuccess('Candidate added and invite email sent to ' + formEmail + '.')
      } else {
        setFormSuccess('Candidate added. No invite sent.')
      }
      setFormEmail('')
      setFormName('')
      setFormJobRole('')
      setFormTechStack('')
      setFormResumeText('')
      setFormResumeUrl('')
      setFormLinksGitHub('')
      setFormLinksLinkedIn('')
      setFormLinksPortfolio('')
      setFormLinksOther('')
      setFormProjects([])
      setFormCertificates('')
      setFormExperience([])
      setFormAtsScore(null)
      setFormMatchedSkills([])
      setFormMissingSkills([])
      setFormSuggestions([])
      setFormInterviewScheduledAt('')
      setFormUploadedFile(null)
      setFormExtractSuccess(false)
      setShowForm(false)
      loadCandidates()
    } catch (err) {
      setError(err.message || 'Failed to add candidate')
    } finally {
      setFormSubmitting(false)
    }
  }

  async function openReport(id) {
    setReport(null)
    try {
      const data = await getReport(token, id)
      setReport(data != null ? data : { none: true })
    } catch {
      setReport({ none: true })
    }
  }

  async function handleAction(candidateId, status) {
    try {
      await candidateAction(token, candidateId, status)
      loadCandidates()
      if (report && report.candidate_id === candidateId) setReport(null)
    } catch (err) {
      setError(err.message || 'Action failed')
    }
  }

  async function handleDelete(candidateId) {
    const name = candidates.find((x) => x.id === candidateId)?.full_name ||
      candidates.find((x) => x.id === candidateId)?.email?.split('@')[0] || 'this candidate'
    if (!window.confirm(`Remove ${name}? This will delete their profile, user account, and all interview data.`)) return
    setDeletingId(candidateId)
    setError('')
    try {
      await deleteCandidate(token, candidateId)
      await loadCandidates()
      if (report && report.candidate_id === candidateId) setReport(null)
    } catch (err) {
      setError(err.message || 'Delete failed')
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <div className="dashboard">
      <div className="dashboard-bg-animation" aria-hidden="true">
        <div className="dashboard-bg-blob dashboard-bg-blob-1" />
        <div className="dashboard-bg-blob dashboard-bg-blob-2" />
      </div>
      <div className="dashboard-header-bar">
        <header className="dashboard-header">
          <h1>
            <span className="header-brand-wrap">
            <img src="/agent.png" alt="Interview Admin" className="header-brand" />
          </span>
            Resumes &amp; Candidates
          </h1>
          <div className="header-actions">
          <button type="button" className="btn btn-primary" onClick={() => setShowForm(!showForm)}>
            {showForm ? 'Cancel' : '+ Add resume'}
          </button>
          <Link to="/dashboard/profile" className="btn btn-outline">Profile</Link>
          <button type="button" className="btn btn-outline" onClick={logout}>
            Log out
          </button>
        </div>
        </header>
      </div>

      <main className="dashboard-main">
      {showForm && (
        <section className="add-resume-card">
          <h2>Add resume</h2>
          <p className="card-hint">
            Upload a resume (PDF/DOCX), then click Extract. The form will be filled automatically; edit any field and save to database.
          </p>

          {formExtractSuccess && !formExtractLoading && !formExtractFileLoading && (
            <>
              <p className="form-extract-success">Details extracted. Edit the fields below if needed, then click Add candidate to save.</p>
              {formAtsScore != null && (
                <div className="form-ats-details">
                  <div className="form-ats-block">
                    <span className="form-ats-label">ATS score (calculated after extract)</span>
                    <span className="form-ats-value">{Number(formAtsScore).toFixed(1)}%</span>
                  </div>
                  {(formMatchedSkills.length > 0 || formMissingSkills.length > 0) && (
                    <div className="form-ats-skills">
                      {formMatchedSkills.length > 0 && (
                        <p className="form-ats-skills-row">
                          <strong>Matched skills:</strong> {formMatchedSkills.join(', ')}
                        </p>
                      )}
                      {formMissingSkills.length > 0 && (
                        <p className="form-ats-skills-row form-ats-missing">
                          <strong>Missing skills:</strong> {formMissingSkills.join(', ')}
                        </p>
                      )}
                    </div>
                  )}
                  {formSuggestions.length > 0 && (
                    <ul className="form-ats-suggestions">
                      {formSuggestions.map((s, i) => (
                        <li key={i}>{s}</li>
                      ))}
                    </ul>
                  )}
                </div>
              )}
            </>
          )}

          <form onSubmit={handleAddResume}>
            <label className="form-job-desc-label">
              Job description (optional — for ATS scoring)
              <textarea
                className="form-job-desc-input"
                value={formJobDescription}
                onChange={(e) => setFormJobDescription(e.target.value)}
                placeholder="Paste the job description here to get dynamic ATS score, matched/missing skills, and improvement suggestions."
                rows={3}
              />
            </label>
            <div className="upload-row">
              <label className="upload-label">
                Upload resume (PDF or DOCX)
                <input
                  type="file"
                  accept=".pdf,.docx"
                  onChange={(e) => setFormUploadedFile(e.target.files?.[0] ?? null)}
                  className="file-input"
                />
                <span className="file-name">{formUploadedFile ? formUploadedFile.name : 'No file chosen'}</span>
              </label>
              <button type="button" className="btn btn-outline" onClick={handleExtractFromFile} disabled={formExtractFileLoading || !formUploadedFile}>
                {formExtractFileLoading ? 'Extracting…' : 'Extract from file'}
              </button>
            </div>

            <hr className="form-divider" />
            <p className="card-hint form-fields-hint">Edit any field below if needed, then use toggles and click Add candidate to save.</p>

            <div className="form-row">
              <label>
                Email <span className="req">*</span>
                <input
                  type="email"
                  value={formEmail}
                  onChange={(e) => setFormEmail(e.target.value)}
                  placeholder="candidate@example.com"
                  required
                />
              </label>
              <label>
                Full name
                <input
                  type="text"
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                  placeholder="John Doe"
                />
              </label>
            </div>
            <div className="form-row">
              <label>
                Job role <span className="req">*</span>
                <input
                  type="text"
                  value={formJobRole}
                  onChange={(e) => setFormJobRole(e.target.value)}
                  placeholder="Software Engineer"
                  required
                />
              </label>
              <label>
                Tech stack (comma-separated)
                <input
                  type="text"
                  value={formTechStack}
                  onChange={(e) => setFormTechStack(e.target.value)}
                  placeholder="React, Node.js, Python"
                />
              </label>
            </div>
            {formAtsScore != null && (
              <p className="form-ats-score form-ats-inline">
                <strong>ATS score:</strong> {Number(formAtsScore).toFixed(1)}%
              </p>
            )}
            <div className="links-by-platform">
              <span className="links-by-platform-label">Links (from resume)</span>
              <div className="links-by-platform-grid">
                <label>
                  GitHub
                  <textarea
                    value={formLinksGitHub}
                    onChange={(e) => setFormLinksGitHub(e.target.value)}
                    placeholder="https://github.com/…"
                    rows={2}
                  />
                </label>
                <label>
                  LinkedIn
                  <textarea
                    value={formLinksLinkedIn}
                    onChange={(e) => setFormLinksLinkedIn(e.target.value)}
                    placeholder="https://linkedin.com/in/…"
                    rows={2}
                  />
                </label>
                <label>
                  Portfolio
                  <textarea
                    value={formLinksPortfolio}
                    onChange={(e) => setFormLinksPortfolio(e.target.value)}
                    placeholder="https://…"
                    rows={2}
                  />
                </label>
                <label>
                  Other (LeetCode, etc.)
                  <textarea
                    value={formLinksOther}
                    onChange={(e) => setFormLinksOther(e.target.value)}
                    placeholder="https://…"
                    rows={2}
                  />
                </label>
              </div>
            </div>

            <div className="form-section">
              <span className="form-section-label">Projects — one column per project</span>
              {(formProjects.length === 0 ? [''] : formProjects).map((text, i) => (
                <div key={i} className="form-project-row">
                  <label>
                    Project {i + 1}
                    <textarea
                      value={text}
                      onChange={(e) => {
                        const next = [...(formProjects.length ? formProjects : [''])]
                        next[i] = e.target.value
                        setFormProjects(next)
                      }}
                      placeholder="Project name or short description"
                      rows={3}
                    />
                  </label>
                  <button type="button" className="btn btn-outline btn-remove" onClick={() => setFormProjects(formProjects.length ? formProjects.filter((_, j) => j !== i) : [])}>
                    Remove
                  </button>
                </div>
              ))}
              <button type="button" className="btn btn-outline" onClick={() => setFormProjects([...(formProjects.length ? formProjects : []), ''])}>
                Add project
              </button>
            </div>

            <label>
              Certificates — one per line (all in one column)
              <textarea
                value={formCertificates}
                onChange={(e) => setFormCertificates(e.target.value)}
                placeholder="e.g. MongoDB – ICT Academy"
                rows={3}
              />
            </label>

            <div className="form-section form-section-experience">
              <span className="form-section-label">Experience — one entry per card</span>
              <div className="form-experience-list">
                {(formExperience.length === 0 ? [''] : formExperience).map((text, i) => (
                  <div key={i} className="form-experience-card">
                    <div className="form-experience-card-header">
                      <span className="form-experience-card-title">Experience {i + 1}</span>
                      <button type="button" className="btn btn-outline btn-remove" onClick={() => setFormExperience(formExperience.length ? formExperience.filter((_, j) => j !== i) : [])}>
                        Remove
                      </button>
                    </div>
                    <textarea
                      className="form-experience-textarea"
                      value={text}
                      onChange={(e) => {
                        const next = [...(formExperience.length ? formExperience : [''])]
                        next[i] = e.target.value
                        setFormExperience(next)
                      }}
                      placeholder={'e.g. Software Developer | Company Name | Jun 2024 – Present | Location\n\n• Key responsibility or achievement\n• Another point...'}
                      rows={6}
                      aria-label={`Experience ${i + 1}`}
                    />
                  </div>
                ))}
              </div>
              <button type="button" className="btn btn-outline form-experience-add" onClick={() => setFormExperience([...(formExperience.length ? formExperience : []), ''])}>
                Add experience
              </button>
            </div>

            {/* Interview date/time: when set, email shows this time; matches dashboard when INTERVIEW_TIMEZONE matches admin's zone */}
            {sendInvite && (
              <>
                <div className="form-row">
                  <label>
                    Interview date &amp; time (optional)
                    <input
                      type="datetime-local"
                      value={formInterviewScheduledAt}
                      onChange={(e) => setFormInterviewScheduledAt(e.target.value)}
                      min={new Date().toISOString().slice(0, 16)}
                      title="Leave empty to use next available slot. This time will appear in the invite email and in the dashboard."
                    />
                  </label>
                </div>
                <p className="toggle-hint" style={{ marginTop: '-8px', marginBottom: 8 }}>Leave empty for next available slot. The time you set here is what the candidate will see in the email and in the dashboard.</p>
              </>
            )}

            {/* Toggles: add more entries here to show additional admin options */}
            <div className="toggles-section">
              <span className="toggles-heading">Options</span>
              <div className="toggle-row">
                <label className="toggle-label">
                  <input
                    type="checkbox"
                    checked={sendInvite}
                    onChange={(e) => setSendInvite(e.target.checked)}
                  />
                  <span className="toggle-switch" />
                  <span className="toggle-text">Send invite &amp; schedule interview</span>
                </label>
                <p className="toggle-hint">
                  {sendInvite
                    ? 'Candidate will receive an email with login credentials and interview setup link.'
                    : 'Candidate is added only; no email will be sent.'}
                </p>
              </div>
              {/* Add more toggle rows here when needed, e.g.:
              <div className="toggle-row">
                <label className="toggle-label">
                  <input type="checkbox" checked={notifyRecruiter} onChange={(e) => setNotifyRecruiter(e.target.checked)} />
                  <span className="toggle-switch" /><span className="toggle-text">Notify recruiter</span>
                </label>
                <p className="toggle-hint">...</p>
              </div>
              */}
            </div>

            {formSuccess && <p className="form-success">{formSuccess}</p>}
            {error && <p className="form-error">{error}</p>}
            <button type="submit" className="btn btn-primary" disabled={formSubmitting}>
              {formSubmitting ? 'Adding…' : 'Add candidate'}
            </button>
          </form>
        </section>
      )}

      {error && !showForm && <p className="dashboard-error">{error}</p>}

      <section className="candidates-section">
        <div className="candidates-section-header">
          <h2>
            Candidates
            {loading && candidates.length === 0 ? (
              <span className="candidates-count-loading"> …</span>
            ) : (
              <span className="candidates-count"> ({candidates.length})</span>
            )}
            {refreshing && candidates.length > 0 && (
              <span className="candidates-updating" aria-hidden> Updating…</span>
            )}
          </h2>
          <label className="candidates-section-filter">
            Status
            <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
              <option value="">All</option>
              <option value="invited">Invited</option>
              <option value="scheduled">Scheduled</option>
              <option value="in_progress">In progress</option>
              <option value="completed">Completed</option>
              <option value="next_round">Next round</option>
              <option value="selected">Selected</option>
              <option value="rejected">Rejected</option>
            </select>
          </label>
        </div>
        {loading && candidates.length === 0 ? (
          <div className="candidates-loading-skeleton" aria-busy="true" aria-label="Loading candidates">
            <div className="table-wrap">
              <table className="candidates-table candidates-table-skeleton">
                <thead>
                  <tr>
                    <th>Photo</th>
                    <th>Name</th>
                    <th>Email</th>
                    <th>Job role</th>
                    <th>ATS</th>
                    <th>Status</th>
                    <th>Invited</th>
                    <th>Interview</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {[1, 2, 3, 4, 5].map((i) => (
                    <tr key={i}>
                      <td><span className="skeleton-box" /></td>
                      <td><span className="skeleton-line" /></td>
                      <td><span className="skeleton-line" /></td>
                      <td><span className="skeleton-line" /></td>
                      <td><span className="skeleton-box" style={{ width: '2.5rem' }} /></td>
                      <td><span className="skeleton-line" style={{ width: '4rem' }} /></td>
                      <td><span className="skeleton-line" /></td>
                      <td><span className="skeleton-line" /></td>
                      <td><span className="skeleton-line" style={{ width: '6rem' }} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : candidates.length === 0 ? (
          <p className="empty">No candidates yet. Use “Add resume” to add one.</p>
        ) : (
          <div className="table-wrap">
            <table className="candidates-table">
              <thead>
                <tr>
                  <th>Photo</th>
                  <th>Name</th>
                  <th>Email</th>
                  <th>Job role</th>
                  <th>ATS</th>
                  <th>Status</th>
                  <th>Invited</th>
                  <th>Interview</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {candidates.map((c) => (
                  <tr key={c.id}>
                    <td className="photo-cell">
                      {c.photo_url ? (
                        <img src={`${apiBase}${c.photo_url}`} alt="" className="candidate-thumb" />
                      ) : (
                        <span className="no-photo">—</span>
                      )}
                    </td>
                    <td>{(c.full_name && c.full_name.trim().toLowerCase() !== 'candidate') ? c.full_name : (c.email && c.email.includes('@') ? c.email.split('@')[0] : '—')}</td>
                    <td>{c.email}</td>
                    <td>{c.job_role}</td>
                    <td>{c.ats_score != null ? c.ats_score : '—'}</td>
                    <td><span className={`status-badge status-${c.status}`}>{c.status}</span></td>
                    <td>{formatDate(c.invited_at)}</td>
                    <td>{c.interview_scheduled_at ? formatDate(c.interview_scheduled_at) : '—'}</td>
                    <td className="actions-cell">
                      <div className="actions-buttons">
                        <Link to={`/dashboard/candidates/${c.id}`} className="btn-action btn-action-profile" title="View full profile">
                          Profile
                        </Link>
                        <button type="button" className="btn-action btn-action-report" onClick={() => openReport(c.id)} title="View report">
                          Report
                        </button>
                        {(c.status === 'completed' || c.status === 'next_round') && (
                          <>
                            <button type="button" className="btn-action btn-action-next" onClick={() => handleAction(c.id, 'next_round')} title="Advance to next round">
                              Next round
                            </button>
                            <button type="button" className="btn-action btn-action-select" onClick={() => handleAction(c.id, 'selected')} title="Select candidate">
                              Select
                            </button>
                            <button type="button" className="btn-action btn-action-reject" onClick={() => handleAction(c.id, 'rejected')} title="Reject candidate">
                              Reject
                            </button>
                          </>
                        )}
                        <button
                          type="button"
                          className="btn-action btn-action-delete"
                          onClick={() => handleDelete(c.id)}
                          disabled={deletingId === c.id}
                          title="Remove candidate"
                          aria-label="Remove candidate"
                        >
                          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                            <polyline points="3 6 5 6 21 6" />
                            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                            <line x1="10" y1="11" x2="10" y2="17" />
                            <line x1="14" y1="11" x2="14" y2="17" />
                          </svg>
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {report && (
        <div className="modal" onClick={() => setReport(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <button type="button" className="modal-close" onClick={() => setReport(null)} aria-label="Close">
              ×
            </button>
            {report.none ? (
              <p>No report yet for this candidate.</p>
            ) : (
              <>
                <h3>Report: {report.candidate_email}</h3>
                <p><strong>Job role:</strong> {report.job_role}</p>

                {report.agent_report && (
                  <div className="report-agent-block">
                    <h4>Agent result (accuracy &amp; communication)</h4>
                    {report.agent_report.accuracy_score != null && (
                      <p><strong>Accuracy (agent):</strong> {report.agent_report.accuracy_score}%</p>
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
                  <p><strong>Face &amp; lip check (cheating):</strong> <span className={`face-lip face-lip-${report.face_lip_status}`}>{report.face_lip_status}</span></p>
                )}

                {report.integrity_score != null && <p><strong>Integrity score:</strong> {report.integrity_score}</p>}
                {report.integrity_risk && <p><strong>Risk:</strong> {report.integrity_risk}</p>}
                {report.summary && !report.agent_report?.summary && <p><strong>Summary:</strong> {report.summary}</p>}

                <div className="report-photos">
                  <h4>Photos (stored on admin dashboard)</h4>
                  {report.photo_url ? (
                    <div className="report-photo-block">
                      <span>Before interview</span>
                      <img src={`${apiBase}${report.photo_url}`} alt="Before interview" />
                    </div>
                  ) : (
                    <p className="photo-placeholder">No before-interview photo.</p>
                  )}
                  <div className="report-photo-block">
                    <span>During interview (captured by agent)</span>
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
          </div>
        </div>
      )}
      </main>

      {(formExtractLoading || formExtractFileLoading) && (
        <div className="extraction-loading-fullscreen" role="status" aria-label="Extracting resume details">
          <div className="extraction-orb-wrap">
            <Orb
              hoverIntensity={2}
              rotateOnHover
              hue={0}
              forceHoverState={false}
              backgroundColor="#0f172a"
            />
          </div>
          <p className="extraction-loading-text extraction-loading-text-overlay">Extracting details from resume…</p>
        </div>
      )}
    </div>
  )
}
