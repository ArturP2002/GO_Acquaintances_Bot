import React, { useState, useEffect } from 'react'
import api from '../services/api'
import './Settings.css'

// Маппинг настроек с описаниями и иконками
const SETTING_DESCRIPTIONS = {
  max_likes_per_day: {
    name: 'Лимит лайков в день',
    icon: '❤️',
    description: 'Максимальное количество лайков, которое пользователь может поставить за день',
    min: 1,
    max: 1000,
    unit: 'лайков'
  },
  boost_frequency: {
    name: 'Частота показа буста',
    icon: '🚀',
    description: 'Буст-анкеты показываются каждые N обычных анкет',
    min: 1,
    max: 100,
    unit: 'анкет'
  },
  min_age: {
    name: 'Минимальный возраст',
    icon: '🔞',
    description: 'Минимальный возраст для регистрации в боте',
    min: 16,
    max: 100,
    unit: 'лет'
  },
  referral_bonus: {
    name: 'Бонус за реферала',
    icon: '🎁',
    description: 'Значение boost_value, которое получает пользователь за приглашенного друга',
    min: 1,
    max: 100,
    unit: 'баллов'
  }
}

const Settings = () => {
  const [settings, setSettings] = useState([])
  const [loading, setLoading] = useState(true)
  const [editingKey, setEditingKey] = useState(null)
  const [editValue, setEditValue] = useState('')
  const [error, setError] = useState(null)
  const [fetchError, setFetchError] = useState(null)
  const [testProfilesCount, setTestProfilesCount] = useState(null)
  const [testProfilesLoading, setTestProfilesLoading] = useState(false)
  const [testProfilesError, setTestProfilesError] = useState(null)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [deleting, setDeleting] = useState(false)

  useEffect(() => {
    fetchSettings()
    fetchTestProfilesCount()
  }, [])

  const fetchSettings = async () => {
    try {
      setFetchError(null)
      const response = await api.get('/api/settings/')
      setSettings(response.data)
    } catch (error) {
      console.error('Error fetching settings:', error)
      let errorMessage = 'Ошибка при загрузке настроек'
      
      if (error.code === 'ERR_NETWORK' || error.message === 'Network Error') {
        errorMessage = 'Ошибка сети: не удалось подключиться к серверу. Проверьте, что бэкенд запущен на порту 8000.'
      } else if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail
      } else if (error.message) {
        errorMessage = error.message
      }
      
      setFetchError(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  const handleEdit = (setting) => {
    setEditingKey(setting.key)
    setEditValue(setting.value)
    setError(null)
  }

  const handleSave = async (key) => {
    try {
      const settingInfo = SETTING_DESCRIPTIONS[key]
      const value = parseInt(editValue)
      
      // Валидация
      if (isNaN(value)) {
        setError('Введите корректное число')
        return
      }
      
      if (settingInfo) {
        if (value < settingInfo.min || value > settingInfo.max) {
          setError(`Значение должно быть от ${settingInfo.min} до ${settingInfo.max}`)
          return
        }
      }
      
      await api.put(`/api/settings/${key}`, { value: editValue })
      setEditingKey(null)
      setEditValue('')
      setError(null)
      fetchSettings()
    } catch (error) {
      console.error('Error updating setting:', error)
      setError('Ошибка при обновлении настройки')
    }
  }

  const handleCancel = () => {
    setEditingKey(null)
    setEditValue('')
    setError(null)
  }

  const getSettingInfo = (key) => {
    return SETTING_DESCRIPTIONS[key] || {
      name: key,
      icon: '⚙️',
      description: '',
      unit: ''
    }
  }

  const fetchTestProfilesCount = async () => {
    try {
      setTestProfilesLoading(true)
      setTestProfilesError(null)
      const response = await api.get('/api/test-profiles/count')
      setTestProfilesCount(response.data.count)
    } catch (error) {
      console.error('Error fetching test profiles count:', error)
      let errorMessage = 'Ошибка при загрузке количества тестовых анкет'
      
      if (error.code === 'ERR_NETWORK' || error.message === 'Network Error') {
        errorMessage = 'Ошибка сети: не удалось подключиться к серверу'
      } else if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail
      } else if (error.message) {
        errorMessage = error.message
      }
      
      setTestProfilesError(errorMessage)
    } finally {
      setTestProfilesLoading(false)
    }
  }

  const handleDeleteTestProfiles = async () => {
    try {
      setDeleting(true)
      setTestProfilesError(null)
      const response = await api.delete('/api/test-profiles/')
      
      // Обновляем количество после удаления
      await fetchTestProfilesCount()
      
      // Закрываем диалог подтверждения
      setShowDeleteConfirm(false)
      
      // Показываем сообщение об успехе (можно добавить toast notification)
      alert(response.data.message || 'Тестовые анкеты успешно удалены')
    } catch (error) {
      console.error('Error deleting test profiles:', error)
      let errorMessage = 'Ошибка при удалении тестовых анкет'
      
      if (error.code === 'ERR_NETWORK' || error.message === 'Network Error') {
        errorMessage = 'Ошибка сети: не удалось подключиться к серверу'
      } else if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail
      } else if (error.message) {
        errorMessage = error.message
      }
      
      setTestProfilesError(errorMessage)
    } finally {
      setDeleting(false)
    }
  }

  if (loading) {
    return <div className="loading">Загрузка...</div>
  }

  if (fetchError) {
    return (
      <div className="settings-page">
        <h1>Настройки бота</h1>
        <div className="error-container">
          <div className="error-message">
            <strong>Ошибка:</strong> {fetchError}
          </div>
          <button onClick={fetchSettings} className="btn-retry">
            Повторить попытку
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="settings-page">
      <h1>Настройки бота</h1>

      {/* Секция управления тестовыми анкетами */}
      <div className="test-profiles-section">
        <div className="test-profiles-header">
          <div className="test-profiles-icon">🧪</div>
          <div className="test-profiles-title-section">
            <h2>Управление тестовыми анкетами</h2>
            <p className="test-profiles-description">
              Управление автоматически сгенерированными тестовыми анкетами для тестирования функционала бота
            </p>
          </div>
        </div>

        <div className="test-profiles-content">
          {testProfilesLoading ? (
            <div className="test-profiles-loading">Загрузка...</div>
          ) : testProfilesError ? (
            <div className="test-profiles-error">
              <div className="error-message">{testProfilesError}</div>
              <button onClick={fetchTestProfilesCount} className="btn-retry">
                Повторить попытку
              </button>
            </div>
          ) : (
            <>
              <div className="test-profiles-count">
                <span className="test-profiles-count-label">Количество тестовых анкет:</span>
                <span className="test-profiles-count-value">{testProfilesCount ?? 0}</span>
              </div>
              
              {testProfilesCount > 0 && (
                <div className="test-profiles-actions">
                  {!showDeleteConfirm ? (
                    <button
                      onClick={() => setShowDeleteConfirm(true)}
                      className="btn-delete-test-profiles"
                    >
                      Удалить все тестовые анкеты
                    </button>
                  ) : (
                    <div className="delete-confirm-dialog">
                      <p className="delete-confirm-message">
                        Вы уверены, что хотите удалить все {testProfilesCount} тестовых анкет?
                        Это действие нельзя отменить.
                      </p>
                      <div className="delete-confirm-buttons">
                        <button
                          onClick={handleDeleteTestProfiles}
                          className="btn-confirm-delete"
                          disabled={deleting}
                        >
                          {deleting ? 'Удаление...' : 'Да, удалить'}
                        </button>
                        <button
                          onClick={() => {
                            setShowDeleteConfirm(false)
                            setTestProfilesError(null)
                          }}
                          className="btn-cancel-delete"
                          disabled={deleting}
                        >
                          Отмена
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}
              
              {testProfilesCount === 0 && (
                <div className="test-profiles-empty">
                  <p>Тестовые анкеты отсутствуют</p>
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {settings.length === 0 ? (
        <div className="empty-state">
          <p>Настройки отсутствуют</p>
          <p className="empty-state-hint">Настройки будут отображаться здесь после их создания</p>
        </div>
      ) : (
        <div className="settings-list">
          {settings.map((setting) => {
            const settingInfo = getSettingInfo(setting.key)
            const isEditing = editingKey === setting.key
            
            return (
              <div key={setting.id} className="setting-item">
                <div className="setting-header">
                  <div className="setting-icon">{settingInfo.icon}</div>
                  <div className="setting-title-section">
                    <h3>{settingInfo.name}</h3>
                    {settingInfo.description && (
                      <p className="setting-description">{settingInfo.description}</p>
                    )}
                  </div>
                </div>
                
                {isEditing ? (
                  <div className="edit-form">
                    <div className="edit-input-wrapper">
                      <input
                        type="number"
                        value={editValue}
                        onChange={(e) => setEditValue(e.target.value)}
                        className="edit-input"
                        min={settingInfo.min}
                        max={settingInfo.max}
                        placeholder={`От ${settingInfo.min} до ${settingInfo.max}`}
                      />
                      {settingInfo.unit && (
                        <span className="input-unit">{settingInfo.unit}</span>
                      )}
                    </div>
                    {error && editingKey === setting.key && (
                      <div className="error-message">{error}</div>
                    )}
                    <div className="edit-buttons">
                      <button
                        onClick={() => handleSave(setting.key)}
                        className="btn-save"
                      >
                        Сохранить
                      </button>
                      <button onClick={handleCancel} className="btn-cancel">
                        Отмена
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="setting-display">
                    <div className="setting-value-wrapper">
                      <span className="setting-value">{setting.value}</span>
                      {settingInfo.unit && (
                        <span className="setting-unit">{settingInfo.unit}</span>
                      )}
                    </div>
                    <button
                      onClick={() => handleEdit(setting)}
                      className="btn-edit"
                    >
                      Редактировать
                    </button>
                  </div>
                )}
                
                <p className="setting-updated">
                  Обновлено: {new Date(setting.updated_at).toLocaleString('ru-RU')}
                </p>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

export default Settings
