import { useState, useRef, useEffect } from 'react'
import { uploadPhoto } from '../api/client'
import { useInterviewConfig } from '../context/InterviewConfig'
import './PhotoCapture.css'

export function PhotoCapture({ onDone }) {
  const { config } = useInterviewConfig()
  const videoRef = useRef(null)
  const streamRef = useRef(null)
  const [status, setStatus] = useState('loading') // loading | ready | capturing | uploading | done
  const [error, setError] = useState('')

  useEffect(() => {
    let stream = null
    const start = async () => {
      try {
        const s = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' } })
        streamRef.current = s
        if (videoRef.current) videoRef.current.srcObject = s
        setStatus('ready')
      } catch (e) {
        setError('Camera access denied or not available.')
        setStatus('ready')
      }
    }
    start()
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop())
      }
    }
  }, [])

  const capture = async () => {
    if (!videoRef.current || !streamRef.current || status !== 'ready') return
    setStatus('capturing')
    try {
      const canvas = document.createElement('canvas')
      canvas.width = videoRef.current.videoWidth
      canvas.height = videoRef.current.videoHeight
      canvas.getContext('2d').drawImage(videoRef.current, 0, 0)
      const blob = await new Promise((res) => canvas.toBlob(res, 'image/jpeg', 0.9))
      if (config.apiBaseUrl && config.authToken && blob) {
        setStatus('uploading')
        await uploadPhoto(config.apiBaseUrl, config.authToken, blob)
      }
      if (streamRef.current) streamRef.current.getTracks().forEach((t) => t.stop())
      setStatus('done')
      onDone()
    } catch (e) {
      setError(e.message || 'Capture failed')
      setStatus('ready')
    }
  }

  const skip = () => {
    if (streamRef.current) streamRef.current.getTracks().forEach((t) => t.stop())
    onDone()
  }

  return (
    <div className="photo-capture-screen">
      <div className="photo-capture-card">
        <h2>Verify your identity</h2>
        <p className="photo-capture-desc">Your photo will be recorded for this interview session.</p>
        {error && <p className="photo-capture-error">{error}</p>}
        {status === 'loading' && <p>Starting camera…</p>}
        {status !== 'loading' && (
          <>
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              className="photo-capture-video"
            />
            <div className="photo-capture-actions">
              {status === 'ready' && (
                <>
                  <button type="button" className="btn btn-primary" onClick={capture}>
                    Capture photo
                  </button>
                  <button type="button" className="btn btn-secondary" onClick={skip}>
                    Skip
                  </button>
                </>
              )}
              {(status === 'capturing' || status === 'uploading') && (
                <p>Please wait…</p>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
