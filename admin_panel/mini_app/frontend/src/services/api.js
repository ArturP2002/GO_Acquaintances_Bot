import axios from 'axios'

// Определение API URL
// Используем относительный путь для проксирования через Vite
// Или абсолютный URL из переменной окружения
function getApiBaseUrl() {
  // Если указана переменная окружения, используем её
  if (import.meta.env.VITE_API_BASE_URL) {
    return import.meta.env.VITE_API_BASE_URL
  }
  
  // В режиме разработки используем относительный путь
  // Vite proxy будет проксировать запросы к бэкенду
  if (import.meta.env.DEV) {
    return '' // Относительный путь - будет использован текущий домен
  }
  
  // В продакшене используем тот же домен
  return ''
}

const API_BASE_URL = getApiBaseUrl()

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Добавление токена авторизации к каждому запросу
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Обработка ошибок
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Логирование ошибок для отладки
    if (error.code === 'ERR_NETWORK' || error.message === 'Network Error') {
      console.error('Network Error:', {
        message: error.message,
        code: error.code,
        baseURL: API_BASE_URL,
        url: error.config?.url,
        fullUrl: error.config?.baseURL + error.config?.url
      })
    }
    
    if (error.response?.status === 401) {
      // Неавторизован - удаляем токен, но не редиректим
      // Пользователь увидит сообщение об авторизации в Layout
      const currentToken = localStorage.getItem('auth_token')
      if (currentToken) {
        localStorage.removeItem('auth_token')
        console.warn('Токен авторизации удален из-за ошибки 401')
      }
    }
    return Promise.reject(error)
  }
)

// Логирование базового URL при инициализации
console.log('API Base URL:', API_BASE_URL || window.location.origin)

export default api
