import { useState, useEffect, useCallback } from 'react'

function useLeaveDetection() {
  const [tabSwitchCount, setTabSwitchCount] = useState(0)
  const [showWarning, setShowWarning] = useState(false)
  const [isDisqualified, setIsDisqualified] = useState(false)

  const dismissWarning = useCallback(() => setShowWarning(false), [])

  const handleLeftApp = useCallback(() => {
    setTabSwitchCount((prev) => {
      const next = prev + 1
      if (next === 1) setShowWarning(true)
      if (next >= 2) setIsDisqualified(true)
      return next
    })
  }, [])

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
 * First time = warning, second time = disqualify.
 */
export function useTabSwitchMonitor() {
  return useLeaveDetection()
}
