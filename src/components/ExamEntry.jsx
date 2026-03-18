import { useState, useEffect } from 'react'
import { validateExamToken, getCandidateMe } from '../api/client'
import { useInterviewConfig } from '../context/InterviewConfig'
import './ExamEntry.css'

const defaultApiBase = (import.meta.env && import.meta.env.VITE_API_URL) || (typeof window !== 'undefined' ? window.location.origin : 'http://localhost:8000')

export function ExamEntry({ token, onExamStarted, onInvalidLink }) {
  const { setConfig } = useInterviewConfig()
  const [status, setStatus] = useState('validating') // validating | ready | error
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    async function run() {
      const apiBase = defaultApiBase.replace(/\/$/, '')
      try {
        const data = await validateExamToken(apiBase, token)
        if (cancelled) return
        const baseUrl = (data.api_base_url && data.api_base_url.trim()) || apiBase
        setConfig({
          apiBaseUrl: baseUrl,
          sessionId: data.session_id,
          authToken: data.access_token,
          jobRole: '',
          techStack: [],
        })
        const profile = await getCandidateMe(baseUrl, data.access_token)
        if (cancelled) return
        const jobRole = (profile && profile.job_role) || 'Candidate'
        const techStack = Array.isArray(profile && profile.tech_stack) ? profile.tech_stack : []
        setConfig((prev) => ({ ...prev, jobRole, techStack }))
        setStatus('ready')
      } catch (e) {
        if (!cancelled) {
          setError(e.message || 'Invalid or expired link')
          setStatus('error')
        }
      }
    }
    run()
    return () => { cancelled = true }
  }, [token, setConfig])

  const handleStartExam = async () => {
    const elem = document.documentElement
    try {
      if (elem.requestFullscreen) await elem.requestFullscreen()
      else if (elem.webkitRequestFullscreen) await elem.webkitRequestFullscreen()
      else if (elem.msRequestFullscreen) await elem.msRequestFullscreen()
    } catch (_) {}
    onExamStarted()
  }

  if (status === 'validating') {
    return (
      <div className="exam-entry">
        <div className="exam-entry-card">
          <h1>Interview</h1>
          <p className="exam-entry-loading">Checking your link…</p>
        </div>
      </div>
    )
  }

  if (status === 'error') {
    return (
      <div className="exam-entry">
        <div className="exam-entry-card exam-entry-card-error">
          <h1>Invalid link</h1>
          <p className="exam-entry-error">{error}</p>
          <button type="button" className="btn btn-primary" onClick={onInvalidLink}>
            Go to login
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="exam-entry">
      <div className="exam-entry-card">
        <h1>Interview</h1>
        <p className="exam-entry-desc">When you start, your browser will go full screen. Do not switch tabs or exit full screen more than allowed, or the exam may be terminated.</p>
        <button type="button" className="btn btn-primary exam-entry-start" onClick={handleStartExam}>
          Start exam
        </button>
      </div>
    </div>
  )
}
