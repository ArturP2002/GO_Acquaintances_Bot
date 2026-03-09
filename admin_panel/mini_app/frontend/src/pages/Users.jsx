import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import api from '../services/api'
import './Users.css'

const Users = () => {
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [filters, setFilters] = useState({
    telegram_id: '',
    username: '',
    is_banned: '',
    is_verified: '',
  })

  useEffect(() => {
    fetchUsers()
  }, [page, filters])

  const fetchUsers = async () => {
    setLoading(true)
    try {
      const params = {
        page,
        page_size: 20,
        ...Object.fromEntries(
          Object.entries(filters).filter(([_, v]) => v !== '')
        ),
      }

      const response = await api.get('/api/users/', { params })
      setUsers(response.data.users)
      setTotal(response.data.total)
    } catch (error) {
      console.error('Error fetching users:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleFilterChange = (field, value) => {
    setFilters((prev) => ({ ...prev, [field]: value }))
    setPage(1)
  }

  return (
    <div className="users-page">
      <h1>Пользователи</h1>

      <div className="filters">
        <input
          type="text"
          placeholder="Telegram ID"
          value={filters.telegram_id}
          onChange={(e) => handleFilterChange('telegram_id', e.target.value)}
        />
        <input
          type="text"
          placeholder="Username"
          value={filters.username}
          onChange={(e) => handleFilterChange('username', e.target.value)}
        />
        <select
          value={filters.is_banned}
          onChange={(e) => handleFilterChange('is_banned', e.target.value)}
        >
          <option value="">Все</option>
          <option value="true">Забанены</option>
          <option value="false">Не забанены</option>
        </select>
        <select
          value={filters.is_verified}
          onChange={(e) => handleFilterChange('is_verified', e.target.value)}
        >
          <option value="">Все</option>
          <option value="true">Верифицированы</option>
          <option value="false">Не верифицированы</option>
        </select>
      </div>

      {loading ? (
        <div className="loading">Загрузка...</div>
      ) : (
        <>
          <div className="users-table">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Telegram ID</th>
                  <th>Username</th>
                  <th>Статус</th>
                  <th>Действия</th>
                </tr>
              </thead>
              <tbody>
                {users.map((user) => (
                  <tr key={user.id}>
                    <td>{user.id}</td>
                    <td>{user.telegram_id}</td>
                    <td>@{user.username || 'N/A'}</td>
                    <td>
                      {user.is_banned && <span className="badge banned">Забанен</span>}
                      {user.is_verified && <span className="badge verified">Верифицирован</span>}
                    </td>
                    <td>
                      <Link to={`/users/${user.id}`} className="btn-view">
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

export default Users
