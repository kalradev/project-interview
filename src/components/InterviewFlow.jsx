import { useState, useEffect, useCallback, useRef } from 'react'
import { useInterviewConfig } from '../context/InterviewConfig'
import {
  getNextQuestion,
  recordExchange,
  endMySession,
  uploadSessionPhoto,
  uploadSessionVideo,
} from '../api/client'
import './InterviewFlow.css'

const SESSION_PHOTO_INTERVAL_MS = 2 * 60 * 1000 // Every 2 minutes during interview

export function InterviewFlow({ onEnd }) {
  const { config } = useInterviewConfig()
  const [exchanges, setExchanges] = useState([])
  const [currentQuestion, setCurrentQuestion] = useState('')
  const [answer, setAnswer] = useState('')
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [ended, setEnded] = useState(false)
  const [error, setError] = useState('')
  const [videoError, setVideoError] = useState('')
  const videoRef = useRef(null)
  const streamRef = useRef(null)
  const mediaRecorderRef = useRef(null)
  const chunksRef = useRef([])
  const questionShownAtRef = useRef(0)

  const jobRole = config.jobRole || 'Candidate'
  const techStack = config.techStack || []
  const baseUrl = config.apiBaseUrl
  const token = config.authToken
  const sessionId = config.sessionId

  const MIN_READ_TIME_MS = 15000 // Under 15s = "cut agent" (interrupt)

  // Video mode: start webcam and periodic session photo upload (agent gets photos during interview)
  useEffect(() => {
    if (!baseUrl || !token) return
    let intervalId
    let firstCaptureTimer
    const startVideo = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true })
        streamRef.current = stream
        if (videoRef.current) videoRef.current.srcObject = stream

        // Agent captures photos of user during interview; stored for admin dashboard
        const captureAndUpload = () => {
          if (!videoRef.current || !streamRef.current || !baseUrl || !token) return
          const video = videoRef.current
          if (video.readyState < 2 || !video.videoWidth || !video.videoHeight) return
          const canvas = document.createElement('canvas')
          canvas.width = video.videoWidth
          canvas.height = video.videoHeight
          const ctx = canvas.getContext('2d')
          ctx.drawImage(video, 0, 0)
          canvas.toBlob(
            (blob) => {
              if (blob) uploadSessionPhoto(baseUrl, token, blob).catch(() => {})
            },
            'image/jpeg',
            0.85
          )
        }
        intervalId = setInterval(captureAndUpload, SESSION_PHOTO_INTERVAL_MS)
        // First capture after video is ready (delay so we have frames)
        firstCaptureTimer = setTimeout(captureAndUpload, 3000)

        // Start video recording for admin (video mode)
        try {
          const recorder = new MediaRecorder(stream, { mimeType: 'video/webm;codecs=vp9' })
          chunksRef.current = []
          recorder.ondataavailable = (e) => {
            if (e.data.size > 0) chunksRef.current.push(e.data)
          }
          recorder.start(10000) // 10s chunks
          mediaRecorderRef.current = recorder
        } catch (_) {
          try {
            const recorder = new MediaRecorder(stream)
            chunksRef.current = []
            recorder.ondataavailable = (e) => {
              if (e.data.size > 0) chunksRef.current.push(e.data)
            }
            recorder.start(10000)
            mediaRecorderRef.current = recorder
          } catch (__) {}
        }
      } catch (e) {
        setVideoError('Camera/mic access needed for video mode.')
      }
    }
    startVideo()
    return () => {
      if (intervalId) clearInterval(intervalId)
      clearTimeout(firstCaptureTimer)
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop())
        streamRef.current = null
      }
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        mediaRecorderRef.current.stop()
      }
    }
  }, [baseUrl, token])

  const fetchNext = useCallback(
    async (previous = []) => {
      if (!baseUrl || !token) return
      setLoading(true)
      setError('')
      try {
        const res = await getNextQuestion(baseUrl, token, jobRole, previous, techStack)
        setCurrentQuestion(res.question || 'No more questions.')
        questionShownAtRef.current = Date.now()
        setLoading(false)
      } catch (e) {
        setError(e.message || 'Failed to load question')
        setLoading(false)
      }
    },
    [baseUrl, token, jobRole, techStack]
  )

  useEffect(() => {
    fetchNext(exchanges)
  }, [])

  const handleSubmit = async (e) => {
    e.preventDefault()
    const text = answer.trim()
    if (!text || !currentQuestion || submitting || !baseUrl || !token || !sessionId) return
    const answeredQuickly = Date.now() - questionShownAtRef.current < MIN_READ_TIME_MS
    setSubmitting(true)
    setError('')
    try {
      await recordExchange(
        baseUrl,
        token,
        sessionId,
        exchanges.length,
        currentQuestion,
        text,
        answeredQuickly
      )
      const nextExchanges = [...exchanges, { question: currentQuestion, answer: text }]
      setExchanges(nextExchanges)
      setAnswer('')
      await fetchNext(nextExchanges)
    } catch (e) {
      setError(e.message || 'Failed to submit')
    } finally {
      setSubmitting(false)
    }
  }

  const handleEndInterview = async () => {
    setSubmitting(true)
    try {
      // Stop recording and upload video if we have one
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        const recorder = mediaRecorderRef.current
        await new Promise((resolve) => {
          recorder.onstop = resolve
          recorder.stop()
        })
        const blob = new Blob(chunksRef.current, { type: 'video/webm' })
        if (blob.size > 0 && baseUrl && token) {
          try {
            await uploadSessionVideo(baseUrl, token, blob)
          } catch (_) {}
        }
        mediaRecorderRef.current = null
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop())
        streamRef.current = null
      }
      if (baseUrl && token && sessionId) {
        await endMySession(baseUrl, token, sessionId)
      }
      setEnded(true)
      onEnd?.()
    } catch (_) {
      setEnded(true)
      onEnd?.()
    } finally {
      setSubmitting(false)
    }
  }

  if (ended) {
    return (
      <div className="interview-flow-ended">
        <h2>Interview ended</h2>
        <p>Thank you. Your responses have been submitted.</p>
      </div>
    )
  }

  return (
    <div className="interview-flow">
      <header className="interview-flow-header">
        <h1>Interview – {jobRole}</h1>
        <p className="subtitle">Video mode: you are being recorded. Do not leave this window.</p>
      </header>
      <div className="interview-flow-video-row">
        <main className="interview-flow-main">
          <div className="question-block">
          <h3>Question {exchanges.length + 1}</h3>
          {loading ? (
            <p>Loading question…</p>
          ) : (
            <p className="question-text">{currentQuestion}</p>
          )}
        </div>
        <form onSubmit={handleSubmit}>
          <label className="answer-label">
            Your answer
            <textarea
              className="answer-input"
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              placeholder="Type your answer here..."
              rows={5}
              disabled={loading || submitting}
            />
          </label>
          {error && <p className="interview-flow-error">{error}</p>}
          <div className="interview-flow-actions">
            <button
              type="submit"
              className="btn btn-primary"
              disabled={loading || submitting || !answer.trim()}
            >
              {submitting ? 'Submitting…' : 'Submit & next question'}
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={handleEndInterview}
              disabled={submitting}
            >
              End interview
            </button>
          </div>
        </form>
      </main>
      <aside className="interview-flow-video-aside">
        <div className="video-label">Your video (recorded for verification)</div>
        {videoError ? (
          <p className="video-error">{videoError}</p>
        ) : (
          <video ref={videoRef} autoPlay playsInline muted className="interview-video" />
        )}
      </aside>
      </div>
    </div>
  )
}
