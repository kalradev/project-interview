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

/** Ping backend health to wake cold-started services (e.g. Render). Call when login page loads. */
export function pingBackend() {
  const url = BASE ? `${BASE.replace(/\/$/, '')}/health` : '/health'
  fetch(url, { method: 'GET', keepalive: true }).catch(() => {})
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

/** Get current authenticated user (for admin profile). */
export async function getMe(token) {
  const res = await fetch(`${BASE}/api/v1/auth/me`, {
    headers: headers(token),
  })
  if (!res.ok) {
    if (res.status === 401) throw new Error('Session expired or invalid. Please sign in again.')
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Failed to load profile')
  }
  return res.json()
}

/** Change password for current user. */
export async function changePassword(token, currentPassword, newPassword) {
  const res = await fetch(`${BASE}/api/v1/auth/change-password`, {
    method: 'POST',
    headers: headers(token),
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
    }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Failed to change password')
  }
  return res.json()
}

/** Public signup (only works when no users exist – creates first admin). */
export async function signup(email, password, fullName = '') {
  const res = await fetch(`${BASE}/api/v1/auth/signup`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify({ email, password, full_name: fullName || undefined }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Sign up failed')
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

/** Get a single candidate by id (for profile page). */
export async function getCandidate(token, candidateId) {
  const res = await fetch(`${BASE}/api/v1/admin/candidates/${candidateId}`, {
    headers: headers(token),
  })
  if (!res.ok) {
    if (res.status === 404) return null
    throw new Error('Failed to fetch candidate')
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
  if (res.status === 204 || res.headers.get('content-length') === '0') return null
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

export async function deleteCandidate(token, candidateId) {
  const res = await fetch(`${BASE}/api/v1/admin/candidates/${candidateId}`, {
    method: 'DELETE',
    headers: headers(token),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Delete failed')
  }
  return res.json()
}

/** Extract details from resume text for form pre-fill. Optional jobDescription for dynamic ATS scoring. */
export async function extractResumeDetails(token, resumeText, jobDescription = '') {
  const res = await fetch(`${BASE}/api/v1/admin/resumes/extract`, {
    method: 'POST',
    headers: headers(token),
    body: JSON.stringify({ resume_text: resumeText, job_description: jobDescription || '' }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Extract failed')
  }
  return res.json()
}

/** Upload resume file (PDF or DOCX); returns extracted details for form pre-fill. Optional jobDescription for dynamic ATS scoring. */
export async function extractResumeFromFile(token, file, jobDescription = '') {
  if (!token) {
    throw new Error('Not logged in. Please sign in again.')
  }
  const form = new FormData()
  form.append('file', file)
  if (jobDescription) form.append('job_description', jobDescription)
  const res = await fetch(`${BASE}/api/v1/admin/resumes/extract-file`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
    body: form,
  })
  if (!res.ok) {
    if (res.status === 401) {
      throw new Error('Session expired or invalid. Please sign in again.')
    }
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
