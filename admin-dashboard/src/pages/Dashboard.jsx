import { useState, useEffect } from 'react'
import { getToken, logout } from '../App'
import { listCandidates, addCandidate, getReport, candidateAction, deleteCandidate, submitResumeFromPlatform, extractResumeDetails, extractResumeFromFile, apiBase } from '../api'
import './Dashboard.css'

function formatDate(d) {
  if (!d) return '—'
  return new Date(d).toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' })
}

export default function Dashboard() {
  const token = getToken()
  const [candidates, setCandidates] = useState([])
  const [loading, setLoading] = useState(true)
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
  const [formProjectsList, setFormProjectsList] = useState(['']) // one box per project
  const [formCertificatesList, setFormCertificatesList] = useState(['']) // one box per certificate
  const [formExperience, setFormExperience] = useState('')
  const [sendInvite, setSendInvite] = useState(true) // Toggle: admin decides to take interview
  const [formSubmitting, setFormSubmitting] = useState(false)
  const [formExtractLoading, setFormExtractLoading] = useState(false)
  const [formExtractFileLoading, setFormExtractFileLoading] = useState(false)
  const [formUploadedFile, setFormUploadedFile] = useState(null) // selected file for upload
  const [formClearKey, setFormClearKey] = useState(0) // increment to reset file input on Clear
  const [formExtractSuccess, setFormExtractSuccess] = useState(false) // show "Details extracted" after parse
  const [formSuccess, setFormSuccess] = useState('')

  // From platform (ATS shortlist >= 85)
  const [showPlatformForm, setShowPlatformForm] = useState(false)
  const [platformResumeText, setPlatformResumeText] = useState('')
  const [platformJobRole, setPlatformJobRole] = useState('')
  const [platformName, setPlatformName] = useState('')
  const [platformSubmitting, setPlatformSubmitting] = useState(false)
  const [platformResult, setPlatformResult] = useState(null)

  const loadCandidates = async () => {
    setLoading(true)
    setError('')
    try {
      const params = statusFilter ? { status: statusFilter } : {}
      const data = await listCandidates(token, params)
      setCandidates(data)
    } catch (err) {
      setError(err.message || 'Failed to load candidates')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadCandidates()
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
    setFormProjectsList([''])
    setFormCertificatesList([''])
    setFormExperience('')
  }

  function clearForm() {
    clearExtractedFormFields()
    setFormResumeText('')
    setFormResumeUrl('')
    setFormUploadedFile(null)
    setFormClearKey((k) => k + 1)
    setFormExtractSuccess(false)
    setFormSuccess('')
    setError('')
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
    setFormProjectsList(
      (Array.isArray(data.projects) ? data.projects : (data.projects ?? '').toString().split('\n').map((s) => s.trim()).filter(Boolean)).length
        ? (Array.isArray(data.projects) ? data.projects : (data.projects ?? '').toString().split('\n').map((s) => s.trim()))
        : ['']
    )
    setFormCertificatesList(
      (Array.isArray(data.certificates) ? data.certificates : (data.certificates ?? '').toString().split('\n').map((s) => s.trim()).filter(Boolean)).length
        ? (Array.isArray(data.certificates) ? data.certificates : (data.certificates ?? '').toString().split('\n').map((s) => s.trim()))
        : ['']
    )
    setFormExperience(Array.isArray(data.experience) ? data.experience.join('\n') : (data.experience ?? ''))
    if (data.resume_text) setFormResumeText(data.resume_text)
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
      const data = await extractResumeDetails(token, formResumeText)
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
      const data = await extractResumeFromFile(token, formUploadedFile)
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
        projects: formProjectsList.filter((s) => s.trim()).length ? formProjectsList.map((s) => s.trim()).filter(Boolean) : undefined,
        certificates: formCertificatesList.filter((s) => s.trim()).length ? formCertificatesList.map((s) => s.trim()).filter(Boolean) : undefined,
        experience: formExperience ? formExperience.split('\n').map((s) => s.trim()).filter(Boolean) : undefined,
        source: 'manual',
        send_email: sendInvite,
      })
      if (sendInvite && res.email_sent === false) {
        setFormSuccess('Candidate added but invite email could not be sent. Check Brevo/SMTP in server .env.')
      } else if (sendInvite) {
        setFormSuccess('Candidate added and invite email sent.')
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
      setFormProjectsList([''])
      setFormCertificatesList([''])
      setFormExperience('')
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
      setReport(data)
    } catch {
      setReport({ none: true })
    }
  }

  async function handleDelete(candidateId, candidateName) {
    if (!window.confirm(`Delete candidate "${candidateName || 'this candidate'}"? This will remove their profile, user account, and all interview sessions.`)) {
      return
    }
    setError('')
    try {
      await deleteCandidate(token, candidateId)
      if (report && report.candidate_id === candidateId) setReport(null)
      loadCandidates()
    } catch (err) {
      setError(err.message || 'Failed to delete candidate')
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

  async function handlePlatformSubmit(e) {
    e.preventDefault()
    setPlatformSubmitting(true)
    setPlatformResult(null)
    setError('')
    try {
      const res = await submitResumeFromPlatform(token, {
        resume_text: platformResumeText,
        job_role: platformJobRole,
        full_name: platformName || undefined,
      })
      setPlatformResult(res)
      if (res.shortlisted) {
        setPlatformResumeText('')
        setPlatformJobRole('')
        setPlatformName('')
        loadCandidates()
      }
    } catch (err) {
      setError(err.message || 'Platform submit failed')
    } finally {
      setPlatformSubmitting(false)
    }
  }

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <h1>Resumes &amp; Candidates</h1>
        <div className="header-actions">
          <button type="button" className="btn btn-outline" onClick={() => setShowPlatformForm(!showPlatformForm)}>
            {showPlatformForm ? 'Cancel' : 'From platform'}
          </button>
          <button type="button" className="btn btn-primary" onClick={() => setShowForm(!showForm)}>
            {showForm ? 'Cancel' : '+ Add resume'}
          </button>
          <button type="button" className="btn btn-outline" onClick={logout}>
            Log out
          </button>
        </div>
      </header>

      {showPlatformForm && (
        <section className="add-resume-card platform-card">
          <h2>Resume from job platform (ATS ≥ 85 shortlisted)</h2>
          <p className="card-hint">Paste resume text. Email is extracted; if ATS score ≥ 85, candidate is shortlisted and invite email is sent.</p>
          <form onSubmit={handlePlatformSubmit}>
            <label>
              Job role <span className="req">*</span>
              <input
                type="text"
                value={platformJobRole}
                onChange={(e) => setPlatformJobRole(e.target.value)}
                placeholder="Software Engineer"
                required
              />
            </label>
            <label>
              Full name (optional)
              <input
                type="text"
                value={platformName}
                onChange={(e) => setPlatformName(e.target.value)}
                placeholder="John Doe"
              />
            </label>
            <label>
              Resume text <span className="req">*</span>
              <textarea
                value={platformResumeText}
                onChange={(e) => setPlatformResumeText(e.target.value)}
                placeholder="Paste full resume. Include email in text."
                rows={6}
                required
              />
            </label>
            {platformResult && (
              <div className={`platform-result ${platformResult.shortlisted ? 'shortlisted' : 'not-shortlisted'}`}>
                <p><strong>ATS score:</strong> {platformResult.ats_score}</p>
                <p>{platformResult.message}</p>
                {platformResult.email && <p>Email extracted: {platformResult.email}</p>}
              </div>
            )}
            <button type="submit" className="btn btn-primary" disabled={platformSubmitting}>
              {platformSubmitting ? 'Submitting…' : 'Submit from platform'}
            </button>
          </form>
        </section>
      )}

      {showForm && (
        <section className="add-resume-card">
          <h2>Add resume</h2>
          <p className="card-hint">
            Upload a resume (PDF/DOCX) or paste text below, then click Extract. The form will be filled automatically; edit any field and save to database.
          </p>

          {(formExtractLoading || formExtractFileLoading) && (
            <div className="extraction-loading" role="status" aria-label="Extracting resume details">
              <div className="extraction-loading-bar" />
              <p className="extraction-loading-text">Extracting details from resume…</p>
            </div>
          )}

          {formExtractSuccess && !formExtractLoading && !formExtractFileLoading && (
            <p className="form-extract-success">Details extracted. Edit the fields below if needed, then click Add candidate to save.</p>
          )}

          <form onSubmit={handleAddResume}>
            <div className="upload-row">
              <label className="upload-label">
                Upload resume (PDF or DOCX)
                <input
                  key={`file-${formClearKey}`}
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

            <label>
              Or paste resume text (then click Extract)
              <textarea
                value={formResumeText}
                onChange={(e) => setFormResumeText(e.target.value)}
                placeholder="Paste full resume content here…"
                rows={4}
              />
            </label>
            <button type="button" className="btn btn-outline" onClick={handleExtractResume} disabled={formExtractLoading || !formResumeText.trim()}>
              {formExtractLoading ? 'Extracting…' : 'Extract details from text'}
            </button>

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
            <label>
              Resume URL (optional)
              <input
                type="url"
                value={formResumeUrl}
                onChange={(e) => setFormResumeUrl(e.target.value)}
                placeholder="https://…"
              />
            </label>

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

            <div className="list-fields">
              <span className="list-fields-label">Projects — one box per project with all its details (name, description, tech stack)</span>
              <div className="list-fields-items">
                {formProjectsList.map((text, idx) => (
                  <div key={idx} className="list-field-box">
                    <label className="list-field-box-label">Project {idx + 1}</label>
                    <textarea
                      value={text}
                      onChange={(e) => {
                        const next = [...formProjectsList]
                        next[idx] = e.target.value
                        setFormProjectsList(next)
                      }}
                      placeholder="Project name, description, bullets, tech stack — all details for this project"
                      rows={5}
                    />
                    <button
                      type="button"
                      className="btn btn-outline btn-sm list-field-remove"
                      onClick={() => {
                        const next = formProjectsList.filter((_, i) => i !== idx)
                        setFormProjectsList(next.length ? next : [''])
                      }}
                      aria-label="Remove project"
                    >
                      Remove
                    </button>
                  </div>
                ))}
              </div>
              <button
                type="button"
                className="btn btn-outline btn-sm list-field-add"
                onClick={() => setFormProjectsList([...formProjectsList, ''])}
              >
                + Add project
              </button>
            </div>

            <div className="list-fields">
              <span className="list-fields-label">Certificates — one box per certificate</span>
              <div className="list-fields-items">
                {formCertificatesList.map((text, idx) => (
                  <div key={idx} className="list-field-box">
                    <label className="list-field-box-label">Certificate {idx + 1}</label>
                    <input
                      type="text"
                      value={text}
                      onChange={(e) => {
                        const next = [...formCertificatesList]
                        next[idx] = e.target.value
                        setFormCertificatesList(next)
                      }}
                      placeholder="e.g. MongoDB – ICT Academy"
                    />
                    <button
                      type="button"
                      className="btn btn-outline btn-sm list-field-remove"
                      onClick={() => {
                        const next = formCertificatesList.filter((_, i) => i !== idx)
                        setFormCertificatesList(next.length ? next : [''])
                      }}
                      aria-label="Remove certificate"
                    >
                      Remove
                    </button>
                  </div>
                ))}
              </div>
              <button
                type="button"
                className="btn btn-outline btn-sm list-field-add"
                onClick={() => setFormCertificatesList([...formCertificatesList, ''])}
              >
                + Add certificate
              </button>
            </div>

            <label>
              Experience — one entry per line
              <textarea
                value={formExperience}
                onChange={(e) => setFormExperience(e.target.value)}
                placeholder="Role, company, duration — one per line"
                rows={4}
              />
            </label>

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
            <div className="form-actions">
              <button type="submit" className="btn btn-primary" disabled={formSubmitting}>
                {formSubmitting ? 'Adding…' : 'Add candidate'}
              </button>
              <button type="button" className="btn btn-outline" onClick={clearForm}>
                Clear
              </button>
            </div>
          </form>
        </section>
      )}

      <div className="filters">
        <label>
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

      {error && !showForm && <p className="dashboard-error">{error}</p>}

      <section className="candidates-section">
        <h2>Candidates ({candidates.length})</h2>
        {loading ? (
          <p className="loading">Loading…</p>
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
                    <td>{c.full_name || '—'}</td>
                    <td>{c.email}</td>
                    <td>{c.job_role}</td>
                    <td>{c.ats_score != null ? c.ats_score : '—'}</td>
                    <td><span className={`status-badge status-${c.status}`}>{c.status}</span></td>
                    <td>{formatDate(c.invited_at)}</td>
                    <td className="actions-cell">
                      <div className="actions-buttons">
                        <button type="button" className="btn-action btn-action-report" onClick={() => openReport(c.id)} title="View report">
                          Report
                        </button>
                        {(c.status === 'completed' || c.status === 'invited') && (
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
                        <button type="button" className="btn-action btn-action-delete" onClick={() => handleDelete(c.id, c.full_name)} title="Delete candidate">
                          Delete
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
    </div>
  )
}
