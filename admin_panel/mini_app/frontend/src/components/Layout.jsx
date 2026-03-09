import React from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import './Layout.css'

const Layout = ({ children }) => {
  const location = useLocation()
  const { user, logout, loading, isAuthenticated } = useAuth()

  const navItems = [
    { path: '/dashboard', label: 'Дашборд', icon: '📊' },
    { path: '/users', label: 'Пользователи', icon: '👥' },
    { path: '/complaints', label: 'Жалобы', icon: '🚨' },
    { path: '/settings', label: 'Настройки', icon: '⚙️' },
  ]

  return (
    <div className="layout">
      <header className="header">
        <h1>Admin Panel</h1>
        {user && (
          <div className="user-info">
            <span>{user.username || `ID: ${user.telegram_id}`}</span>
            <button onClick={logout} className="logout-btn">Выйти</button>
          </div>
        )}
      </header>
      
      <div className="container">
        <nav className="sidebar">
          <ul className="nav-list">
            {navItems.map((item) => (
              <li key={item.path}>
                <Link
                  to={item.path}
                  className={location.pathname === item.path ? 'active' : ''}
                >
                  <span className="icon">{item.icon}</span>
                  <span>{item.label}</span>
                </Link>
              </li>
            ))}
          </ul>
        </nav>
        
        <main className="main-content">
          {loading ? (
            <div style={{ padding: '20px', textAlign: 'center' }}>Загрузка...</div>
          ) : !isAuthenticated ? (
            <div style={{ padding: '40px', maxWidth: '600px', margin: '0 auto' }}>
              <h2>Требуется авторизация</h2>
              <div style={{ marginTop: '20px', padding: '20px', backgroundColor: '#f0f0f0', borderRadius: '5px' }}>
                <p><strong>Для тестирования в браузере:</strong></p>
                <ol style={{ marginTop: '10px', paddingLeft: '20px' }}>
                  <li style={{ marginBottom: '10px' }}>
                    Откройте консоль браузера (F12 → Console)
                  </li>
                  <li style={{ marginBottom: '10px' }}>
                    Выполните команду:
                    <br />
                    <code style={{ 
                      display: 'block', 
                      marginTop: '5px', 
                      padding: '10px', 
                      backgroundColor: '#fff', 
                      borderRadius: '3px',
                      fontFamily: 'monospace'
                    }}>
                      localStorage.setItem('auth_token', 'ВАШ_TELEGRAM_ID')
                    </code>
                    <small style={{ display: 'block', marginTop: '5px', color: '#666' }}>
                      Замените ВАШ_TELEGRAM_ID на ваш реальный Telegram ID администратора
                    </small>
                  </li>
                  <li style={{ marginBottom: '10px' }}>
                    Или добавьте в URL параметр:
                    <br />
                    <code style={{ 
                      display: 'block', 
                      marginTop: '5px', 
                      padding: '10px', 
                      backgroundColor: '#fff', 
                      borderRadius: '3px',
                      fontFamily: 'monospace'
                    }}>
                      ?test_user_id=ВАШ_TELEGRAM_ID
                    </code>
                  </li>
                  <li>
                    Обновите страницу (F5)
                  </li>
                </ol>
              </div>
            </div>
          ) : (
            children
          )}
        </main>
      </div>
    </div>
  )
}

export default Layout
