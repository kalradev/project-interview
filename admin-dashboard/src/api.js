/**
 * Admin dashboard API client.
 * Uses VITE_API_URL in dev (e.g. http://localhost:8000) or relative /api when proxied.
 */

const BASE = import.meta.env.VITE_API_URL || ''

function headers(token) {
  const h = { 'Content-Type': 'application/json' }
  if (token) h['Authorization'] = `Bearer ${token}`
  return h
}

export async function login(email, password) {
  const res = await fetch(`${BASE}/api/v1/auth/login`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify({ email, password }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Login failed')
  }
  return res.json()
}

export async function listCandidates(token, params = {}) {
  const q = new URLSearchParams(params).toString()
  const res = await fetch(`${BASE}/api/v1/admin/candidates${q ? `?${q}` : ''}`, {
    headers: headers(token),
  })
  if (!res.ok) throw new Error('Failed to fetch candidates')
  return res.json()
}

export async function addCandidate(token, data) {
  const res = await fetch(`${BASE}/api/v1/admin/candidates`, {
    method: 'POST',
    headers: headers(token),
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Failed to add candidate')
  }
  return res.json()
}

export async function getReport(token, candidateId) {
  const res = await fetch(`${BASE}/api/v1/admin/candidates/${candidateId}/report`, {
    headers: headers(token),
  })
  if (!res.ok) {
    if (res.status === 404) return null
    throw new Error('Failed to fetch report')
  }
  return res.json()
}

export async function candidateAction(token, candidateId, status) {
  const res = await fetch(`${BASE}/api/v1/admin/candidates/${candidateId}/action`, {
    method: 'POST',
    headers: headers(token),
    body: JSON.stringify({ status }),
  })
  if (!res.ok) throw new Error('Action failed')
  return res.json()
}

/** Extract details from resume text for form pre-fill. */
export async function extractResumeDetails(token, resumeText) {
  const res = await fetch(`${BASE}/api/v1/admin/resumes/extract`, {
    method: 'POST',
    headers: headers(token),
    body: JSON.stringify({ resume_text: resumeText }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Extract failed')
  }
  return res.json()
}

/** Upload resume file (PDF or DOCX); returns extracted details for form pre-fill. */
export async function extractResumeFromFile(token, file) {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${BASE}/api/v1/admin/resumes/extract-file`, {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: form,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Extract from file failed')
  }
  return res.json()
}

/** Submit resume from job platform; shortlists if ATS >= 85 and sends invite email. */
export async function submitResumeFromPlatform(token, data) {
  const res = await fetch(`${BASE}/api/v1/admin/resumes/from-platform`, {
    method: 'POST',
    headers: headers(token),
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Submit failed')
  }
  return res.json()
}

export const apiBase = BASE || (typeof window !== 'undefined' ? window.location.origin : '')
