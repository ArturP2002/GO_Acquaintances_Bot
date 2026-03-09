import React, { useState, useEffect } from 'react'
import api from '../services/api'
import './Dashboard.css'

const Dashboard = () => {
  const [stats, setStats] = useState({
    totalUsers: 0,
    totalProfiles: 0,
    totalLikes: 0,
    totalMatches: 0,
    bannedUsers: 0,
    verifiedUsers: 0,
    pendingComplaints: 0,
  })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchStats()
  }, [])

  const fetchStats = async () => {
    try {
      setError(null)
      const response = await api.get('/api/stats/')
      setStats({
        totalUsers: response.data.totalUsers || 0,
        totalProfiles: response.data.totalProfiles || 0,
        totalLikes: response.data.totalLikes || 0,
        totalMatches: response.data.totalMatches || 0,
        bannedUsers: response.data.bannedUsers || 0,
        verifiedUsers: response.data.verifiedUsers || 0,
        pendingComplaints: response.data.pendingComplaints || 0,
      })
    } catch (error) {
      console.error('Error fetching stats:', error)
      let errorMessage = 'Ошибка при загрузке статистики'
      
      if (error.code === 'ERR_NETWORK' || error.message === 'Network Error') {
        errorMessage = 'Ошибка сети: не удалось подключиться к серверу. Проверьте, что бэкенд запущен на порту 8000.'
      } else if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail
      } else if (error.message) {
        errorMessage = error.message
      }
      
      setError(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return <div className="loading">Загрузка...</div>
  }

  if (error) {
    const isAuthError = error.includes('401') || error.includes('авторизации') || error.includes('Unauthorized')
    
    return (
      <div className="dashboard">
        <h1>Дашборд</h1>
        <div className="error-container">
          <div className="error-message">
            <strong>Ошибка:</strong> {error}
          </div>
          {isAuthError && (
            <div className="auth-help" style={{ marginTop: '20px', padding: '15px', backgroundColor: '#f0f0f0', borderRadius: '5px' }}>
              <strong>Для тестирования в браузере:</strong>
              <ol style={{ marginTop: '10px', paddingLeft: '20px' }}>
                <li>Откройте консоль браузера (F12)</li>
                <li>Выполните: <code>localStorage.setItem('auth_token', 'ВАШ_TELEGRAM_ID')</code></li>
                <li>Или добавьте в URL: <code>?test_user_id=ВАШ_TELEGRAM_ID</code></li>
                <li>Обновите страницу</li>
              </ol>
            </div>
          )}
          <button onClick={fetchStats} className="btn-retry" style={{ marginTop: '15px' }}>
            Повторить попытку
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="dashboard">
      <h1>Дашборд</h1>
      
      <div className="stats-section">
        <h2 className="section-title">Пользователи</h2>
        <div className="stats-grid">
          <div className="stat-card stat-card-primary">
            <div className="stat-icon">👥</div>
            <h3>Всего пользователей</h3>
            <p className="stat-value">{stats.totalUsers}</p>
          </div>
          
          <div className="stat-card stat-card-success">
            <div className="stat-icon">✅</div>
            <h3>Верифицировано</h3>
            <p className="stat-value">{stats.verifiedUsers}</p>
          </div>
          
          <div className="stat-card stat-card-danger">
            <div className="stat-icon">🚫</div>
            <h3>Забанено</h3>
            <p className="stat-value">{stats.bannedUsers}</p>
          </div>
        </div>
      </div>

      <div className="stats-section">
        <h2 className="section-title">Активность</h2>
        <div className="stats-grid">
          <div className="stat-card stat-card-info">
            <div className="stat-icon">📋</div>
            <h3>Всего профилей</h3>
            <p className="stat-value">{stats.totalProfiles}</p>
          </div>
          
          <div className="stat-card stat-card-love">
            <div className="stat-icon">❤️</div>
            <h3>Всего лайков</h3>
            <p className="stat-value">{stats.totalLikes}</p>
          </div>
          
          <div className="stat-card stat-card-match">
            <div className="stat-icon">💕</div>
            <h3>Всего мэтчей</h3>
            <p className="stat-value">{stats.totalMatches}</p>
          </div>
        </div>
      </div>

      <div className="stats-section">
        <h2 className="section-title">Модерация</h2>
        <div className="stats-grid">
          <div className="stat-card stat-card-warning">
            <div className="stat-icon">⚠️</div>
            <h3>Ожидающих жалоб</h3>
            <p className="stat-value">{stats.pendingComplaints}</p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Dashboard
