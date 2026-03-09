import React, { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import api from '../services/api'
import './UserDetail.css'

const UserDetail = () => {
  const { id } = useParams()
  const navigate = useNavigate()
  const [user, setUser] = useState(null)
  const [profile, setProfile] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchUserData()
  }, [id])

  const fetchUserData = async () => {
    try {
      const [userRes, profileRes] = await Promise.all([
        api.get(`/api/users/${id}`),
        api.get(`/api/users/${id}/profile`).catch(() => null),
      ])

      setUser(userRes.data)
      setProfile(profileRes?.data || null)
    } catch (error) {
      console.error('Error fetching user data:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleBan = async () => {
    if (!confirm('Забанить этого пользователя?')) return

    try {
      await api.post(`/api/users/${id}/ban`)
      fetchUserData()
    } catch (error) {
      console.error('Error banning user:', error)
      alert('Ошибка при бане пользователя')
    }
  }

  const handleUnban = async () => {
    if (!confirm('Разбанить этого пользователя?')) return

    try {
      await api.post(`/api/users/${id}/unban`)
      fetchUserData()
    } catch (error) {
      console.error('Error unbanning user:', error)
      alert('Ошибка при разбане пользователя')
    }
  }

  if (loading) {
    return <div className="loading">Загрузка...</div>
  }

  if (!user) {
    return <div>Пользователь не найден</div>
  }

  return (
    <div className="user-detail">
      <button onClick={() => navigate('/users')} className="back-btn">
        ← Назад к списку
      </button>

      <h1>Пользователь #{user.id}</h1>

      <div className="user-info">
        <div className="info-section">
          <h2>Основная информация</h2>
          <p><strong>Telegram ID:</strong> {user.telegram_id}</p>
          <p><strong>Username:</strong> @{user.username || 'N/A'}</p>
          <p><strong>Забанен:</strong> {user.is_banned ? 'Да' : 'Нет'}</p>
          <p><strong>Верифицирован:</strong> {user.is_verified ? 'Да' : 'Нет'}</p>
          <p><strong>Активен:</strong> {user.is_active ? 'Да' : 'Нет'}</p>
          <p><strong>Создан:</strong> {new Date(user.created_at).toLocaleString('ru-RU')}</p>
        </div>

        {profile && (
          <div className="info-section">
            <h2>Профиль</h2>
            <p><strong>Имя:</strong> {profile.name}</p>
            <p><strong>Возраст:</strong> {profile.age}</p>
            <p><strong>Пол:</strong> {profile.gender}</p>
            <p><strong>Город:</strong> {profile.city || 'N/A'}</p>
            <p><strong>Описание:</strong> {profile.bio || 'N/A'}</p>
          </div>
        )}

        <div className="actions">
          {user.is_banned ? (
            <button onClick={handleUnban} className="btn-unban">
              Разбанить
            </button>
          ) : (
            <button onClick={handleBan} className="btn-ban">
              Забанить
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

export default UserDetail
