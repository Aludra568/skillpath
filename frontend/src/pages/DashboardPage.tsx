import { Link } from 'react-router-dom'

import { api, type DepartmentStats, type Event, type Issue } from '../api'
import { useAuth } from '../auth'
import { useAsync } from '../hooks'
import { ErrorBox, Loading, Person, formatDate, formatDateTime } from '../ui'

/** Что показать, когда подчинённых подразделений ещё нет. */
function StartHere() {
  const { me } = useAuth()

  if (!me) return null

  if (me.is_admin) {
    return (
      <div className="box accent">
        <h2 className="box-title">С чего начать</h2>
        <ol style={{ margin: '10px 0 0', paddingLeft: 20 }}>
          <li>
            <Link to="/admin">Заведите направления и скиллы</Link> — из них собираются планы
            обучения.
          </li>
          <li>
            <Link to="/structure">Создайте подразделения</Link> и назначьте каждому руководителя.
          </li>
          <li>
            Раздайте сотрудникам ссылку на систему: они регистрируются сами, а вы добавляете их в
            подразделение на вкладке <Link to="/admin">Пользователи</Link>.
          </li>
        </ol>
      </div>
    )
  }

  if (!me.user.department) {
    return (
      <div className="box accent">
        <h2 className="box-title">Вы зарегистрированы</h2>
        <p style={{ marginBottom: 0 }}>
          Осталось дождаться, пока администратор добавит вас в подразделение и назначит
          направление. После этого здесь появится ваш план обучения и встречи.
        </p>
      </div>
    )
  }

  return (
    <div className="box">
      <p className="empty" style={{ margin: 0 }}>
        У вас нет подчинённых. <Link to={`/employees/${me.user.id}`}>Открыть своё развитие</Link>
      </p>
    </div>
  )
}

export default function DashboardPage() {
  const stats = useAsync(() => api.get<DepartmentStats[]>('/api/analytics/departments'), [])
  const events = useAsync(() => api.get<Event[]>('/api/events', { days: 30 }), [])
  const issues = useAsync(() => api.get<Issue[]>('/api/issues'), [])

  const openIssues = (issues.data ?? []).filter((issue) => !issue.is_resolved)

  return (
    <div>
      <div className="head">
        <h1>Главная</h1>
        <p>Прогресс обучения по вашим подразделениям и ближайшие события.</p>
      </div>

      <ErrorBox text={stats.error} />

      {stats.loading ? (
        <Loading />
      ) : (stats.data ?? []).length === 0 ? (
        <StartHere />
      ) : (
        stats.data?.map((department) => (
          <div className="box" key={department.id}>
            <div className="box-head">
              <h2 className="box-title">{department.name}</h2>
              <Link to={`/employees?department=${department.id}`}>Сотрудники отдела</Link>
            </div>

            <div className="stats">
              <div className="main">
                <b>{department.progress.percent}%</b>
                <span className="small">
                  выполнение плана ({department.progress.confirmed} из {department.progress.total})
                </span>
                <div className={`bar${department.progress.percent === 100 ? ' done' : ''}`} style={{ marginTop: 6 }}>
                  <div style={{ width: `${department.progress.percent}%` }} />
                </div>
              </div>
              <div>
                <b>{department.employees}</b>
                <span className="small">сотрудников</span>
              </div>
              <div>
                <b>{department.progress.overdue}</b>
                <span className="small">просрочено скиллов</span>
              </div>
              <div>
                <b>{department.progress.issues}</b>
                <span className="small">открытых проблем</span>
              </div>
              <div>
                <b>{department.meetings_held}</b>
                <span className="small">встреч проведено</span>
              </div>
            </div>

            {department.at_risk.length > 0 ? (
              <>
                <h3>Требуют внимания</h3>
                <ul className="list">
                  {department.at_risk.map((user) => (
                    <li key={user.id} className="item">
                      <span className="grow">
                        <Person id={user.id} name={user.full_name} />
                        <span className="small">{user.department_path.join(' / ')}</span>
                      </span>
                      {user.progress.overdue > 0 ? (
                        <span className="tag red">просрочено: {user.progress.overdue}</span>
                      ) : null}
                      {user.progress.issues > 0 ? (
                        <span className="tag amber">проблем: {user.progress.issues}</span>
                      ) : null}
                    </li>
                  ))}
                </ul>
              </>
            ) : null}
          </div>
        ))
      )}

      <div className="cols">
        <div className="box">
          <div className="box-head">
            <h2>Ближайшие события</h2>
            <Link to="/calendar">Календарь</Link>
          </div>
          {events.loading ? (
            <Loading />
          ) : (events.data ?? []).length === 0 ? (
            <p className="empty">Событий нет</p>
          ) : (
            <ul className="list">
              {events.data?.map((event) => (
                <li key={event.kind + event.id} className="item">
                  <span className="grow">
                    {event.kind === 'meeting' ? (
                      <Link to={`/meetings/${event.id}`}>{event.title}</Link>
                    ) : (
                      event.title
                    )}
                    <br />
                    <span className="small">
                      {event.employee_name}
                      {event.kind === 'meeting' ? ' — встреча' : ' — срок подтверждения скилла'}
                    </span>
                  </span>
                  <span className={`tag ${event.kind === 'deadline' ? 'amber' : event.done ? 'green' : 'accent'}`}>
                    {event.kind === 'meeting' ? formatDateTime(event.date) : formatDate(event.date)}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="box">
          <h2>Открытые проблемы ({openIssues.length})</h2>
          {issues.loading ? (
            <Loading />
          ) : openIssues.length === 0 ? (
            <p className="empty">Проблем нет</p>
          ) : (
            <ul className="list">
              {openIssues.map((issue) => (
                <li key={issue.id}>
                  <Person id={issue.employee_id} name={issue.employee_name} />
                  {issue.skill_name ? <span className="small"> — {issue.skill_name}</span> : null}
                  <div className="small">{issue.comment}</div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  )
}
