import { useState, useEffect } from 'react'
import './WaitForInterview.css'

function formatScheduledAt(iso) {
  if (!iso) return null
  try {
    const d = new Date(iso)
    return d.toLocaleString(undefined, {
      dateStyle: 'long',
      timeStyle: 'short',
    })
  } catch {
    return iso
  }
}

function useTimeLeft(scheduledAt) {
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    if (!scheduledAt) return
    const t = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(t)
  }, [scheduledAt])
  if (!scheduledAt) return null
  const scheduled = new Date(scheduledAt).getTime()
  const diff = scheduled - now
  if (diff <= 0) return null
  const hours = Math.floor(diff / (1000 * 60 * 60))
  const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60))
  const seconds = Math.floor((diff % (1000 * 60)) / 1000)
  return { hours, minutes, seconds }
}

export function WaitForInterview({ candidateInfo, onJoin }) {
  const scheduledAt = candidateInfo?.interviewScheduledAt || null
  const timeLeft = useTimeLeft(scheduledAt)
  const scheduledTimeFormatted = formatScheduledAt(scheduledAt)

  // If no scheduled time, allow join immediately (e.g. manual session / legacy).
  const canJoin = !scheduledAt || Date.now() >= new Date(scheduledAt).getTime()

  return (
    <div className="wait-for-interview-screen">
      <div className="wait-for-interview-card">
        <h2>Your interview</h2>
        {scheduledTimeFormatted && (
          <p className="wait-scheduled-time">
            Scheduled for <strong>{scheduledTimeFormatted}</strong>
          </p>
        )}
        {canJoin ? (
          <>
            <p className="wait-message wait-message-ok">
              {scheduledAt ? "It's time. Click below to join your interview." : 'You can join the interview when ready.'}
            </p>
            <button type="button" className="btn btn-primary wait-join-btn" onClick={onJoin}>
              Join interview
            </button>
          </>
        ) : (
          <>
            <p className="wait-message wait-message-wait">
              Please wait until your scheduled time. You may leave and return when it&apos;s time—just log in again and you&apos;ll see the option to join.
            </p>
            {timeLeft && (
              <div className="wait-countdown" aria-live="polite">
                <span className="wait-countdown-label">Time until interview:</span>
                <span className="wait-countdown-value">
                  {String(timeLeft.hours).padStart(2, '0')}:{String(timeLeft.minutes).padStart(2, '0')}:
                  {String(timeLeft.seconds).padStart(2, '0')}
                </span>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
