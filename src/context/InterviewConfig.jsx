import { createContext, useContext, useState, useCallback } from 'react'

const STORAGE_KEY = 'interview-agent-config'

const defaultApiBaseUrl = (import.meta.env && import.meta.env.VITE_API_URL) || 'http://localhost:8000'

const defaultConfig = {
  apiBaseUrl: defaultApiBaseUrl,
  sessionId: '',
  authToken: '',
  jobRole: '',
  techStack: [],
}

function loadConfig() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return { ...defaultConfig }
    const parsed = JSON.parse(raw)
    return {
      apiBaseUrl: parsed.apiBaseUrl ?? defaultConfig.apiBaseUrl,
      sessionId: parsed.sessionId ?? '',
      authToken: parsed.authToken ?? '',
      jobRole: parsed.jobRole ?? '',
      techStack: Array.isArray(parsed.techStack) ? parsed.techStack : [],
    }
  } catch {
    return { ...defaultConfig }
  }
}

function saveConfig(config) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(config))
  } catch (_) {}
}

const InterviewConfigContext = createContext(null)

export function InterviewConfigProvider({ children }) {
  const [config, setConfigState] = useState(loadConfig)

  const setConfig = useCallback((next) => {
    setConfigState((prev) => {
      const updated = typeof next === 'function' ? next(prev) : next
      saveConfig(updated)
      return updated
    })
  }, [])

  const isConnected = Boolean(
    config.apiBaseUrl && config.sessionId && config.authToken
  )

  return (
    <InterviewConfigContext.Provider
      value={{ config, setConfig, isConnected }}
    >
      {children}
    </InterviewConfigContext.Provider>
  )
}

export function useInterviewConfig() {
  const ctx = useContext(InterviewConfigContext)
  if (!ctx) throw new Error('useInterviewConfig must be used within InterviewConfigProvider')
  return ctx
}
