import { useState, useEffect, useCallback } from 'react'

const WARNINGS_BEFORE_DISQUALIFY = 3 // 1st, 2nd, 3rd = warning; 4th = disqualify

/**
 * @param {{ onLeave?: (count: number, isDisqualified: boolean) => void }} [options]
 */
function useLeaveDetection(options) {
  const [tabSwitchCount, setTabSwitchCount] = useState(0)
  const [showWarning, setShowWarning] = useState(false)
  const [isDisqualified, setIsDisqualified] = useState(false)
  const onLeave = options?.onLeave

  const dismissWarning = useCallback(() => setShowWarning(false), [])

  const handleLeftApp = useCallback(() => {
    setTabSwitchCount((prev) => {
      const next = prev + 1
      if (next <= WARNINGS_BEFORE_DISQUALIFY) setShowWarning(true)
      if (next > WARNINGS_BEFORE_DISQUALIFY) setIsDisqualified(true)
      if (onLeave) queueMicrotask(() => onLeave(next, next > WARNINGS_BEFORE_DISQUALIFY))
      return next
    })
  }, [onLeave])

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
 * @param {{ onLeave?: (count: number, isDisqualified: boolean) => void }} [options]
 */
export function useTabSwitchMonitor(options) {
  return useLeaveDetection(options)
}

export { WARNINGS_BEFORE_DISQUALIFY }
