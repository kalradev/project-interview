/**
 * Interview backend API client.
 * Base URL should point to the FastAPI app (e.g. http://localhost:8000).
 */

const API_V1 = '/api/v1'

/**
 * @param {string} baseUrl - e.g. http://localhost:8000
 * @param {string} path - e.g. /api/v1/events/log
 */
function url(baseUrl, path) {
  const base = baseUrl.replace(/\/$/, '')
  const p = path.startsWith('/') ? path : `/${path}`
  return `${base}${p}`
}

/**
 * Log a suspicious event (tab_switch, etc.).
 * @param {string} baseUrl
 * @param {string} sessionId - UUID
 * @param {string} eventType - tab_switch | paste_event | copy_event | devtools_detection | idle_time | burst_typing | instant_large_input | webcam_anomaly
 * @param {string} authToken - Bearer JWT
 * @param {Record<string, unknown>} [payload]
 * @param {string} [severity]
 */
export async function logEvent(baseUrl, sessionId, eventType, authToken, payload = null, severity = 'high') {
  const res = await fetch(url(baseUrl, `${API_V1}/events/log`), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${authToken}`,
    },
    body: JSON.stringify({
      session_id: sessionId,
      event_type: eventType,
      payload: payload ?? undefined,
      severity,
    }),
  })
  if (!res.ok) {
    const err = await res.text()
    throw new Error(`logEvent failed: ${res.status} ${err}`)
  }
  return res.json()
}

/**
 * End an interview session.
 * @param {string} baseUrl
 * @param {string} sessionId - UUID
 * @param {string} authToken - Bearer JWT (Admin or Interviewer)
 */
export async function endSession(baseUrl, sessionId, authToken) {
  const res = await fetch(url(baseUrl, `${API_V1}/sessions/end`), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${authToken}`,
    },
    body: JSON.stringify({ session_id: sessionId }),
  })
  if (!res.ok) {
    const err = await res.text()
    throw new Error(`endSession failed: ${res.status} ${err}`)
  }
  return res.json()
}

/**
 * Compute integrity score for a session (call after disqualify or end).
 */
export async function computeIntegrity(baseUrl, sessionId, authToken, aiProbability = 0) {
  const res = await fetch(
    url(baseUrl, `${API_V1}/integrity/compute/${sessionId}`) + `?ai_probability=${aiProbability}`,
    {
      method: 'POST',
      headers: { Authorization: `Bearer ${authToken}` },
    }
  )
  if (!res.ok) {
    const err = await res.text()
    throw new Error(`computeIntegrity failed: ${res.status} ${err}`)
  }
  return res.json()
}

/** Login; returns { access_token, token_type, expires_in } */
export async function login(baseUrl, email, password) {
  const res = await fetch(url(baseUrl, `${API_V1}/auth/login`), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
  if (!res.ok) {
    const err = await res.text()
    throw new Error(err || 'Login failed')
  }
  return res.json()
}

/** Get candidate profile + session (requires candidate JWT). */
export async function getCandidateMe(baseUrl, authToken) {
  const res = await fetch(url(baseUrl, `${API_V1}/candidate/me`), {
    headers: { Authorization: `Bearer ${authToken}` },
  })
  if (!res.ok) return null
  return res.json()
}

/** Get or create session for candidate (requires candidate JWT). */
export async function getOrCreateSession(baseUrl, authToken) {
  const res = await fetch(url(baseUrl, `${API_V1}/candidate/me/session`), {
    method: 'POST',
    headers: { Authorization: `Bearer ${authToken}` },
  })
  if (!res.ok) {
    const err = await res.text()
    throw new Error(err || 'Session failed')
  }
  return res.json()
}

/** Upload candidate photo (multipart). */
export async function uploadPhoto(baseUrl, authToken, blob) {
  const form = new FormData()
  form.append('file', blob, 'photo.jpg')
  const res = await fetch(url(baseUrl, `${API_V1}/candidate/me/photo`), {
    method: 'POST',
    headers: { Authorization: `Bearer ${authToken}` },
    body: form,
  })
  if (!res.ok) throw new Error('Photo upload failed')
  return res.json()
}

/** Get next AI question (role + tech stack + communication). */
export async function getNextQuestion(baseUrl, authToken, jobRole, previousExchanges, techStack = []) {
  const res = await fetch(url(baseUrl, `${API_V1}/interview/next-question`), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${authToken}`,
    },
    body: JSON.stringify({
      job_role: jobRole,
      tech_stack: Array.isArray(techStack) && techStack.length ? techStack : undefined,
      previous_exchanges: previousExchanges.map((e) => ({ question: e.question, answer: e.answer })),
    }),
  })
  if (!res.ok) throw new Error('Next question failed')
  return res.json()
}

/** Record one Q&A for admin report. answeredQuickly = true if user submitted before reading (cut agent). */
export async function recordExchange(baseUrl, authToken, sessionId, questionIndex, questionText, answerText, answeredQuickly = false) {
  const res = await fetch(url(baseUrl, `${API_V1}/interview/record-exchange`), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${authToken}`,
    },
    body: JSON.stringify({
      session_id: sessionId,
      question_index: questionIndex,
      question_text: questionText,
      answer_text: answerText,
      answered_quickly: answeredQuickly,
    }),
  })
  if (!res.ok) throw new Error('Record exchange failed')
  return res.json()
}

/** Candidate ends their own session. */
export async function endMySession(baseUrl, authToken, sessionId) {
  const res = await fetch(url(baseUrl, `${API_V1}/sessions/end-my`), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${authToken}`,
    },
    body: JSON.stringify({ session_id: sessionId }),
  })
  if (!res.ok) throw new Error('End session failed')
  return res.json()
}

/** Upload a photo captured during the interview (for identity match). */
export async function uploadSessionPhoto(baseUrl, authToken, blob) {
  const form = new FormData()
  form.append('file', blob, 'photo.jpg')
  const res = await fetch(url(baseUrl, `${API_V1}/candidate/me/session/photo`), {
    method: 'POST',
    headers: { Authorization: `Bearer ${authToken}` },
    body: form,
  })
  if (!res.ok) throw new Error('Session photo upload failed')
  return res.json()
}

/** Upload recorded interview video. */
export async function uploadSessionVideo(baseUrl, authToken, blob) {
  const form = new FormData()
  const ext = blob.type === 'video/webm' ? '.webm' : '.mp4'
  form.append('file', blob, `video${ext}`)
  const res = await fetch(url(baseUrl, `${API_V1}/candidate/me/session/video`), {
    method: 'POST',
    headers: { Authorization: `Bearer ${authToken}` },
    body: form,
  })
  if (!res.ok) throw new Error('Session video upload failed')
  return res.json()
}
