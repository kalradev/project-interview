import { Routes, Route, Navigate } from 'react-router-dom'
import Login from './pages/Login'
import Signup from './pages/Signup'
import Dashboard from './pages/Dashboard'
import CandidateProfile from './pages/CandidateProfile'

const tokenKey = 'interview_admin_token'

export function getToken() {
  return localStorage.getItem(tokenKey)
}

export function setToken(token) {
  if (token) localStorage.setItem(tokenKey, token)
  else localStorage.removeItem(tokenKey)
}

export function logout() {
  setToken(null)
  window.location.href = '/'
}

function Protected({ children }) {
  if (!getToken()) return <Navigate to="/" replace />
  return children
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Login />} />
      <Route path="/signup" element={<Signup />} />
      <Route
        path="/dashboard"
        element={
          <Protected>
            <Dashboard />
          </Protected>
        }
      />
      <Route
        path="/dashboard/candidates/:id"
        element={
          <Protected>
            <CandidateProfile />
          </Protected>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
