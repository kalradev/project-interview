import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { getToken, logout } from '../App'
import { getMe, changePassword } from '../api'
import './AdminProfile.css'

export default function AdminProfile() {
  const token = getToken()
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [changing, setChanging] = useState(false)

  useEffect(() => {
    let cancelled = false
    async function load() {
      setError('')
      try {
        const data = await getMe(token)
        if (!cancelled) setUser(data)
      } catch (err) {
        if (!cancelled) setError(err.message || 'Failed to load profile')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [token])

  async function handleChangePassword(e) {
    e.preventDefault()
    setError('')
    setSuccess('')
    if (newPassword !== confirmPassword) {
      setError('New password and confirmation do not match.')
      return
    }
    if (newPassword.length < 6) {
      setError('New password must be at least 6 characters.')
      return
    }
    setChanging(true)
    try {
      await changePassword(token, currentPassword, newPassword)
      setSuccess('Password updated successfully.')
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
    } catch (err) {
      setError(err.message || 'Failed to change password')
    } finally {
      setChanging(false)
    }
  }

  const displayName = user?.full_name?.trim() || user?.email?.split('@')[0] || 'Admin'
  const initial = (displayName[0] || 'A').toUpperCase()

  return (
    <div className="dashboard admin-profile-page">
      {loading && (
        <div className="page-loading-overlay">
          <div className="page-loading-spinner"></div>
        </div>
      )}
      <div className="dashboard-bg-animation" aria-hidden="true">
        <div className="dashboard-bg-blob dashboard-bg-blob-1" />
        <div className="dashboard-bg-blob dashboard-bg-blob-2" />
      </div>
      <div className="dashboard-header-bar">
        <header className="dashboard-header">
          <h1>Account</h1>
          <div className="header-actions">
            <Link to="/dashboard" className="btn btn-outline">Back to dashboard</Link>
            <button type="button" className="btn btn-outline" onClick={logout}>Log out</button>
          </div>
        </header>
      </div>

      <main className="dashboard-main admin-profile-main">
        <div className="admin-profile-hero">
          <div className="admin-profile-avatar" aria-hidden="true">{initial}</div>
          <div className="admin-profile-hero-text">
            {loading ? (
              <div className="admin-profile-skeleton admin-profile-skeleton-hero" aria-hidden="true">
                <div className="admin-profile-skeleton-line" style={{ width: '140px' }} />
                <div className="admin-profile-skeleton-line short" />
              </div>
            ) : error && !user ? (
              <p className="admin-profile-error admin-profile-error-inline">{error}</p>
            ) : (
              <>
                <h2 className="admin-profile-name">{displayName}</h2>
                <p className="admin-profile-email">{user?.email}</p>
                {user?.role && (
                  <span className="admin-profile-badge">{user.role}</span>
                )}
              </>
            )}
          </div>
        </div>

        <div className="admin-profile-grid">
          <section className="admin-profile-card admin-profile-details-card">
            <h3 className="admin-profile-card-title">Account details</h3>
            {loading ? (
              <div className="admin-profile-skeleton" aria-hidden="true">
                <div className="admin-profile-skeleton-line" />
                <div className="admin-profile-skeleton-line short" />
                <div className="admin-profile-skeleton-line short" />
              </div>
            ) : error && !user ? null : (
              <ul className="admin-profile-details-list">
                <li>
                  <span className="admin-profile-detail-label">Email</span>
                  <span className="admin-profile-detail-value">{user?.email ?? '—'}</span>
                </li>
                <li>
                  <span className="admin-profile-detail-label">Full name</span>
                  <span className="admin-profile-detail-value">{user?.full_name || '—'}</span>
                </li>
                <li>
                  <span className="admin-profile-detail-label">Role</span>
                  <span className="admin-profile-detail-value admin-profile-role">{user?.role ?? '—'}</span>
                </li>
              </ul>
            )}
          </section>

          <section className="admin-profile-card admin-profile-password-card">
            <h3 className="admin-profile-card-title">Change password</h3>
            {success && <p className="admin-profile-success">{success}</p>}
            {error && user && <p className="admin-profile-error">{error}</p>}
            <form onSubmit={handleChangePassword} className="admin-profile-form">
              <label className="admin-profile-field">
                <span className="admin-profile-field-label">Current password</span>
                <input
                  type="password"
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  required
                  autoComplete="current-password"
                  placeholder="Enter current password"
                />
              </label>
              <label className="admin-profile-field">
                <span className="admin-profile-field-label">New password</span>
                <input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  required
                  minLength={6}
                  autoComplete="new-password"
                  placeholder="At least 6 characters"
                />
              </label>
              <label className="admin-profile-field">
                <span className="admin-profile-field-label">Confirm new password</span>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                  minLength={6}
                  autoComplete="new-password"
                  placeholder="Repeat new password"
                />
              </label>
              <button type="submit" className="btn btn-primary admin-profile-submit" disabled={changing}>
                {changing ? 'Updating…' : 'Update password'}
              </button>
            </form>
          </section>
        </div>
      </main>
    </div>
  )
}
