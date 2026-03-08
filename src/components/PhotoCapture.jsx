import { useState, useRef, useEffect } from 'react'
import { uploadPhoto } from '../api/client'
import { useInterviewConfig } from '../context/InterviewConfig'
import './PhotoCapture.css'

export function PhotoCapture({ onDone }) {
  const { config } = useInterviewConfig()
  const videoRef = useRef(null)
  const streamRef = useRef(null)
  const [status, setStatus] = useState('loading') // loading | ready | preview | uploading | done
  const [error, setError] = useState('')
  const [capturedDataUrl, setCapturedDataUrl] = useState(null)
  const [capturedBlob, setCapturedBlob] = useState(null)

  useEffect(() => {
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

  const capture = () => {
    if (!videoRef.current || !streamRef.current || status !== 'ready') return
    try {
      const canvas = document.createElement('canvas')
      canvas.width = videoRef.current.videoWidth
      canvas.height = videoRef.current.videoHeight
      canvas.getContext('2d').drawImage(videoRef.current, 0, 0)
      const dataUrl = canvas.toDataURL('image/jpeg', 0.9)
      setCapturedDataUrl(dataUrl)
      canvas.toBlob((blob) => setCapturedBlob(blob), 'image/jpeg', 0.9)
      if (streamRef.current) streamRef.current.getTracks().forEach((t) => t.stop())
      setStatus('preview')
    } catch (e) {
      setError(e.message || 'Capture failed')
    }
  }

  const confirmPhoto = async () => {
    if (status !== 'preview' || !capturedBlob) return
    setStatus('uploading')
    try {
      if (config.apiBaseUrl && config.authToken) {
        await uploadPhoto(config.apiBaseUrl, config.authToken, capturedBlob)
      }
      setStatus('done')
      onDone()
    } catch (e) {
      setError(e.message || 'Upload failed')
      setStatus('preview')
    }
  }

  const retake = () => {
    setCapturedDataUrl(null)
    setCapturedBlob(null)
    setError('')
    setStatus('ready')
    navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' } }).then((s) => {
      streamRef.current = s
      if (videoRef.current) videoRef.current.srcObject = s
    }).catch(() => setError('Camera could not be restarted.'))
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
        {status === 'ready' && (
          <>
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              className="photo-capture-video"
            />
            <div className="photo-capture-actions">
              <button type="button" className="btn btn-primary" onClick={capture}>
                Capture photo
              </button>
              <button type="button" className="btn btn-secondary" onClick={skip}>
                Skip
              </button>
            </div>
          </>
        )}
        {status === 'preview' && capturedDataUrl && (
          <>
            <p className="photo-capture-preview-label">Your photo</p>
            <img
              src={capturedDataUrl}
              alt="Your captured photo"
              className="photo-capture-preview-img"
            />
            <div className="photo-capture-actions">
              <button type="button" className="btn btn-primary" onClick={confirmPhoto}>
                Use this photo
              </button>
              <button type="button" className="btn btn-secondary" onClick={retake}>
                Retake
              </button>
            </div>
          </>
        )}
        {(status === 'uploading') && (
          <p className="photo-capture-uploading">Uploading…</p>
        )}
      </div>
    </div>
  )
}
