import React from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Users from './pages/Users'
import UserDetail from './pages/UserDetail'
import Complaints from './pages/Complaints'
import ComplaintDetail from './pages/ComplaintDetail'
import Settings from './pages/Settings'
import { AuthProvider } from './contexts/AuthContext'

function App() {
  return (
    <AuthProvider>
      <Router>
        <Layout>
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/users" element={<Users />} />
            <Route path="/users/:id" element={<UserDetail />} />
            <Route path="/complaints" element={<Complaints />} />
            <Route path="/complaints/:id" element={<ComplaintDetail />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </Layout>
      </Router>
    </AuthProvider>
  )
}

export default App
