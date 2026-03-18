import { useState, useEffect, useCallback } from 'react'

const MAX_ESCAPE_ATTEMPTS = 3

/**
 * Detects when the user exits fullscreen (e.g. presses ESC). Re-requests fullscreen
 * and shows warning. After MAX_ESCAPE_ATTEMPTS, calls onTerminated.
 */
export function useFullscreenExitMonitor({ onTerminated, enabled }) {
  const [escapeAttempts, setEscapeAttempts] = useState(0)
  const [showWarning, setShowWarning] = useState(false)
  const [terminated, setTerminated] = useState(false)

  const requestFullscreen = useCallback(() => {
    const elem = document.documentElement
    if (elem.requestFullscreen) return elem.requestFullscreen()
    if (elem.webkitRequestFullscreen) return elem.webkitRequestFullscreen()
    if (elem.msRequestFullscreen) return elem.msRequestFullscreen()
    return Promise.resolve()
  }, [])

  useEffect(() => {
    if (!enabled) return

    const handleFullscreenChange = () => {
      if (document.fullscreenElement || document.webkitFullscreenElement || document.msFullscreenElement) return
      setEscapeAttempts((prev) => {
        const next = prev + 1
        if (next <= MAX_ESCAPE_ATTEMPTS) setShowWarning(true)
        if (next > MAX_ESCAPE_ATTEMPTS) {
          setTerminated(true)
          onTerminated && onTerminated()
        } else {
          requestFullscreen().catch(() => {})
        }
        return next
      })
    }

    document.addEventListener('fullscreenchange', handleFullscreenChange)
    document.addEventListener('webkitfullscreenchange', handleFullscreenChange)
    document.addEventListener('MSFullscreenChange', handleFullscreenChange)

    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange)
      document.removeEventListener('webkitfullscreenchange', handleFullscreenChange)
      document.removeEventListener('MSFullscreenChange', handleFullscreenChange)
    }
  }, [enabled, onTerminated, requestFullscreen])

  const dismissWarning = useCallback(() => setShowWarning(false), [])

  return { escapeAttempts, showWarning, dismissWarning, terminated }
}

export { MAX_ESCAPE_ATTEMPTS }
