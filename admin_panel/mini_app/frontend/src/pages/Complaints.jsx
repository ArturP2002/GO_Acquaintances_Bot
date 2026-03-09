import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import api from '../services/api'
import './Complaints.css'

const Complaints = () => {
  const [complaints, setComplaints] = useState([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [statusFilter, setStatusFilter] = useState('')

  useEffect(() => {
    fetchComplaints()
  }, [page, statusFilter])

  const fetchComplaints = async () => {
    setLoading(true)
    try {
      const params = {
        page,
        page_size: 20,
        ...(statusFilter && { status: statusFilter }),
      }

      const response = await api.get('/api/complaints/', { params })
      setComplaints(response.data.complaints)
      setTotal(response.data.total)
    } catch (error) {
      console.error('Error fetching complaints:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="complaints-page">
      <h1>Жалобы</h1>

      <div className="filters">
        <select
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value)
            setPage(1)
          }}
        >
          <option value="">Все статусы</option>
          <option value="pending">Ожидающие</option>
          <option value="reviewed">Просмотренные</option>
          <option value="resolved">Решенные</option>
          <option value="dismissed">Отклоненные</option>
        </select>
      </div>

      {loading ? (
        <div className="loading">Загрузка...</div>
      ) : (
        <>
          <div className="complaints-table">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>От кого</th>
                  <th>На кого</th>
                  <th>Причина</th>
                  <th>Статус</th>
                  <th>Дата</th>
                  <th>Действия</th>
                </tr>
              </thead>
              <tbody>
                {complaints.map((complaint) => (
                  <tr key={complaint.id}>
                    <td>{complaint.id}</td>
                    <td>{complaint.reporter_id}</td>
                    <td>{complaint.reported_id}</td>
                    <td>{complaint.reason}</td>
                    <td>
                      <span className={`badge status-${complaint.status}`}>
                        {complaint.status}
                      </span>
                    </td>
                    <td>{new Date(complaint.created_at).toLocaleDateString('ru-RU')}</td>
                    <td>
                      <Link to={`/complaints/${complaint.id}`} className="btn-view">
                        Просмотр
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="pagination">
            <button
              disabled={page === 1}
              onClick={() => setPage(page - 1)}
            >
              Назад
            </button>
            <span>
              Страница {page} из {Math.ceil(total / 20)}
            </span>
            <button
              disabled={page >= Math.ceil(total / 20)}
              onClick={() => setPage(page + 1)}
            >
              Вперед
            </button>
          </div>
        </>
      )}
    </div>
  )
}

export default Complaints
