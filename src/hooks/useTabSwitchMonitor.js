import { useState, useEffect, useCallback, useRef } from 'react'

const WARNINGS_BEFORE_DISQUALIFY = 3 // 1st, 2nd, 3rd = warning; 4th = disqualify

/**
 * Only count "leave" events when enabled (e.g. during the actual interview).
 * When enabled is false (login/setup/photo), blur and visibility changes are ignored
 * so the candidate cannot be disqualified before logging in.
 *
 * @param {{ onLeave?: (count: number, isDisqualified: boolean) => void; enabled?: boolean }} [options]
 */
function useLeaveDetection(options) {
  const [tabSwitchCount, setTabSwitchCount] = useState(0)
  const [showWarning, setShowWarning] = useState(false)
  const [isDisqualified, setIsDisqualified] = useState(false)
  const onLeave = options?.onLeave
  const enabled = options?.enabled ?? true
  const enabledRef = useRef(enabled)
  enabledRef.current = enabled

  const dismissWarning = useCallback(() => setShowWarning(false), [])

  const handleLeftApp = useCallback(() => {
    if (!enabledRef.current) return // ignore leave events when not in interview
    setTabSwitchCount((prev) => {
      const next = prev + 1
      if (next <= WARNINGS_BEFORE_DISQUALIFY) setShowWarning(true)
      if (next > WARNINGS_BEFORE_DISQUALIFY) setIsDisqualified(true)
      if (onLeave) queueMicrotask(() => onLeave(next, next > WARNINGS_BEFORE_DISQUALIFY))
      return next
    })
  }, [onLeave])

  // When interview starts (enabled becomes true), reset count so we don't carry over any stray events from login/setup
  useEffect(() => {
    if (enabled) {
      setTabSwitchCount(0)
      setShowWarning(false)
    }
  }, [enabled])

  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.visibilityState !== 'hidden') return
      handleLeftApp()
    }

    const handleWindowBlur = () => handleLeftApp()

    document.addEventListener('visibilitychange', handleVisibilityChange)
    window.addEventListener('blur', handleWindowBlur)

    if (window.electronAPI?.onAppBlur) {
      window.electronAPI.onAppBlur(handleLeftApp)
    }

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange)
      window.removeEventListener('blur', handleWindowBlur)
    }
  }, [handleLeftApp])

  return { tabSwitchCount, showWarning, isDisqualified, dismissWarning }
}

/**
 * Monitors leaving the interview (tab switch in browser, or window focus loss in Electron).
 * First 3 times = warning only; 4th time = disqualify.
 * Only active when enabled=true (e.g. during the actual interview); login/setup/photo are ignored.
 *
 * @param {{ onLeave?: (count: number, isDisqualified: boolean) => void; enabled?: boolean }} [options]
 */
export function useTabSwitchMonitor(options) {
  return useLeaveDetection(options)
}

export { WARNINGS_BEFORE_DISQUALIFY }
