import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'

import { api, type Department, type Direction, type User } from '../api'
import { useAsync } from '../hooks'
import { ErrorBox, Loading, Person } from '../ui'

export default function EmployeesPage() {
  const [params, setParams] = useSearchParams()
  const [search, setSearch] = useState(params.get('q') ?? '')

  const direction = params.get('direction') ?? ''
  const department = params.get('department') ?? ''
  const query = params.get('q') ?? ''

  const directions = useAsync(() => api.get<Direction[]>('/api/directions'), [])
  const departments = useAsync(() => api.get<Department[]>('/api/departments'), [])
  const users = useAsync(
    () =>
      api.get<User[]>('/api/users', {
        direction_id: direction || undefined,
        department_id: department || undefined,
        q: query || undefined,
      }),
    [direction, department, query],
  )

  function setParam(key: string, value: string) {
    const next = new URLSearchParams(params)
    if (value) next.set(key, value)
    else next.delete(key)
    setParams(next, { replace: true })
  }

  return (
    <div>
      <div className="head">
        <h1>Сотрудники</h1>
        <p>Видно вас и ваших подчинённых, включая вложенные подразделения.</p>
      </div>

      <div className="box">
        <div className="filters">
          <label>
            <span>Направление</span>
            <select value={direction} onChange={(e) => setParam('direction', e.target.value)}>
              <option value="">Все</option>
              {directions.data?.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.code} — {item.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Подразделение</span>
            <select value={department} onChange={(e) => setParam('department', e.target.value)}>
              <option value="">Все</option>
              {departments.data?.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Поиск</span>
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') setParam('q', search)
              }}
              placeholder="Фамилия или почта"
            />
          </label>
          <button className="grey" onClick={() => setParam('q', search)}>
            Найти
          </button>
        </div>
      </div>

      <div className="box">
        <ErrorBox text={users.error} />
        {users.loading ? (
          <Loading />
        ) : (users.data ?? []).length === 0 ? (
          <p className="empty">Никого не нашли</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Сотрудник</th>
                <th>Направление</th>
                <th>Подразделение</th>
                <th>План</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {users.data?.map((user) => (
                <tr key={user.id}>
                  <td>
                    <Person id={user.id} name={user.full_name} />
                    <div className="small" style={{ paddingLeft: 38 }}>
                      {user.position}
                    </div>
                  </td>
                  <td>
                    {user.direction ? (
                      <span className="tag accent">{user.direction.code}</span>
                    ) : (
                      '—'
                    )}
                  </td>
                  <td className="small">{user.department_path.join(' / ') || '—'}</td>
                  <td>
                    {user.progress.total > 0 ? (
                      <>
                        <div className={`bar${user.progress.percent === 100 ? ' done' : ''}`}>
                          <div style={{ width: `${user.progress.percent}%` }} />
                        </div>
                        <div className="small">
                          {user.progress.confirmed} из {user.progress.total} · {user.progress.percent}%
                        </div>
                      </>
                    ) : (
                      <span className="small">плана нет</span>
                    )}
                  </td>
                  <td>
                    {user.progress.overdue > 0 ? (
                      <span className="tag red">просрочено: {user.progress.overdue}</span>
                    ) : null}{' '}
                    {user.progress.issues > 0 ? (
                      <span className="tag amber">проблем: {user.progress.issues}</span>
                    ) : null}
                    {user.relation === 'self' ? <span className="tag">это вы</span> : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
