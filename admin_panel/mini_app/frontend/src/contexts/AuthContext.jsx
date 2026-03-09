import React, { createContext, useContext, useState, useEffect } from 'react'
import api from '../services/api'

const AuthContext = createContext(null)

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}

// Функция для получения Telegram WebApp объекта
const getTelegramWebApp = () => {
  if (typeof window !== 'undefined' && window.Telegram && window.Telegram.WebApp) {
    return window.Telegram.WebApp
  }
  return null
}

// Функция для получения initData от Telegram
const getTelegramInitData = () => {
  const webApp = getTelegramWebApp()
  if (webApp && webApp.initData) {
    return webApp.initData
  }
  return null
}

// Функция для получения user_id из initData
const getUserIdFromInitData = (initData) => {
  if (!initData) return null
  
  try {
    // Парсим initData (формат: key1=value1&key2=value2&user=%7B...%7D)
    const params = new URLSearchParams(initData)
    const userParam = params.get('user')
    
    if (userParam) {
      const user = JSON.parse(decodeURIComponent(userParam))
      return user.id || null
    }
  } catch (error) {
    console.error('Error parsing initData:', error)
  }
  
  return null
}

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [isAuthenticated, setIsAuthenticated] = useState(false)

  useEffect(() => {
    // Инициализация Telegram Mini App
    // В продакшене нужно проверить подпись initData
    const initAuth = async () => {
      try {
        // Инициализируем Telegram WebApp
        const webApp = getTelegramWebApp()
        if (webApp) {
          webApp.ready()
          webApp.expand()
        }
        
        // Получаем initData от Telegram
        const telegramInitData = getTelegramInitData()
        
        if (telegramInitData) {
          // TODO: Проверить подпись initData на бэкенде
          // Извлекаем user_id из initData
          const userId = getUserIdFromInitData(telegramInitData)
          
          // Временная заглушка для разработки
          // В продакшене нужно использовать реальный initData и проверять подпись
          const token = localStorage.getItem('auth_token')
          
          if (token) {
            // Проверка токена через API
            try {
              const response = await api.get('/api/users/me')
              setUser(response.data)
              setIsAuthenticated(true)
            } catch (error) {
              console.error('Auth error:', error)
              localStorage.removeItem('auth_token')
            }
          } else if (userId) {
            // Если есть userId из initData, можно использовать его как токен для разработки
            // В продакшене это должно быть заменено на проверку подписи и получение токена с бэкенда
            localStorage.setItem('auth_token', userId.toString())
            try {
              const response = await api.get('/api/users/me')
              setUser(response.data)
              setIsAuthenticated(true)
            } catch (error) {
              console.error('Auth error:', error)
              localStorage.removeItem('auth_token')
            }
          }
        } else {
          // Если не в Telegram WebApp, проверяем токен из localStorage
          let token = localStorage.getItem('auth_token')
          
          // Для разработки: проверяем URL параметры для тестового токена
          const urlParams = new URLSearchParams(window.location.search)
          const testUserId = urlParams.get('test_user_id')
          
          if (testUserId) {
            token = testUserId
            localStorage.setItem('auth_token', testUserId)
            console.log('🔧 Режим разработки: используем test_user_id из URL:', testUserId)
          }
          
          // Если токена нет, пытаемся использовать тестовый токен для разработки
          if (!token) {
            // Можно указать тестовый telegram_id администратора здесь
            // Или использовать из URL параметров
            const defaultTestId = urlParams.get('admin_id') || null
            if (defaultTestId) {
              token = defaultTestId
              localStorage.setItem('auth_token', defaultTestId)
              console.log('🔧 Режим разработки: используем admin_id из URL:', defaultTestId)
            }
          }
          
          if (token) {
            try {
              const response = await api.get('/api/users/me')
              setUser(response.data)
              setIsAuthenticated(true)
            } catch (error) {
              console.error('Auth error:', error)
              // Не удаляем токен сразу, может быть проблема с сетью
              if (error.response?.status === 401) {
                localStorage.removeItem('auth_token')
                console.warn('⚠️ Токен недействителен. Используйте ?test_user_id=YOUR_TELEGRAM_ID в URL для тестирования')
              }
            }
          } else {
            console.warn('⚠️ Токен авторизации не найден. Для тестирования добавьте ?test_user_id=YOUR_TELEGRAM_ID в URL')
          }
        }
      } catch (error) {
        console.error('Initialization error:', error)
      } finally {
        setLoading(false)
      }
    }

    initAuth()
  }, [])

  const login = async (token) => {
    localStorage.setItem('auth_token', token)
    try {
      const response = await api.get('/api/users/me')
      setUser(response.data)
      setIsAuthenticated(true)
    } catch (error) {
      console.error('Login error:', error)
      throw error
    }
  }

  const logout = () => {
    localStorage.removeItem('auth_token')
    setUser(null)
    setIsAuthenticated(false)
  }

  return (
    <AuthContext.Provider value={{ user, loading, isAuthenticated, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}
