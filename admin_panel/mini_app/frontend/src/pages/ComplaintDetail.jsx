import React, { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import api from '../services/api'
import './ComplaintDetail.css'

const ComplaintDetail = () => {
  const { id } = useParams()
  const navigate = useNavigate()
  const [complaint, setComplaint] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchComplaint()
  }, [id])

  const fetchComplaint = async () => {
    try {
      const response = await api.get(`/api/complaints/${id}`)
      setComplaint(response.data)
    } catch (error) {
      console.error('Error fetching complaint:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleStatusUpdate = async (status) => {
    try {
      await api.patch(`/api/complaints/${id}`, {
        status,
        comment: '',
      })
      fetchComplaint()
    } catch (error) {
      console.error('Error updating complaint:', error)
      alert('Ошибка при обновлении жалобы')
    }
  }

  const handleBanReported = async () => {
    if (!confirm('Забанить пользователя, на которого пожаловались?')) return

    try {
      await api.post(`/api/complaints/${id}/ban-reported`)
      fetchComplaint()
      alert('Пользователь забанен')
    } catch (error) {
      console.error('Error banning user:', error)
      alert('Ошибка при бане пользователя')
    }
  }

  if (loading) {
    return <div className="loading">Загрузка...</div>
  }

  if (!complaint) {
    return <div>Жалоба не найдена</div>
  }

  return (
    <div className="complaint-detail">
      <button onClick={() => navigate('/complaints')} className="back-btn">
        ← Назад к списку
      </button>

      <h1>Жалоба #{complaint.id}</h1>

      <div className="complaint-info">
        <div className="info-section">
          <h2>Информация о жалобе</h2>
          <p><strong>От пользователя:</strong> {complaint.reporter_id}</p>
          <p><strong>На пользователя:</strong> {complaint.reported_id}</p>
          <p><strong>Причина:</strong> {complaint.reason}</p>
          <p><strong>Описание:</strong> {complaint.description || 'N/A'}</p>
          <p><strong>Статус:</strong> {complaint.status}</p>
          <p><strong>Создана:</strong> {new Date(complaint.created_at).toLocaleString('ru-RU')}</p>
        </div>

        <div className="actions">
          <button
            onClick={() => handleStatusUpdate('resolved')}
            className="btn-resolve"
          >
            Решено
          </button>
          <button
            onClick={() => handleStatusUpdate('dismissed')}
            className="btn-dismiss"
          >
            Отклонить
          </button>
          <button
            onClick={handleBanReported}
            className="btn-ban"
          >
            Забанить пользователя
          </button>
        </div>
      </div>
    </div>
  )
}

export default ComplaintDetail
