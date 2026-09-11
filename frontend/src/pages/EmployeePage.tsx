import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'

import {
  api,
  type EmployeeStats,
  type Issue,
  type Meeting,
  type MeetingBrief,
  type Plan,
  type PlanItem,
  type Skill,
  type User,
} from '../api'
import { useAsync } from '../hooks'
import { Avatar, ErrorBox, Loading, Modal, dateTimeInput, formatDate, formatDateTime } from '../ui'

export default function EmployeePage() {
  const { id } = useParams()
  const userId = Number(id)
  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null)
  const [skillModal, setSkillModal] = useState(false)
  const [meetingModal, setMeetingModal] = useState(false)
  const [issueFor, setIssueFor] = useState<PlanItem | 'user' | null>(null)
  const [passwordModal, setPasswordModal] = useState(false)

  const user = useAsync(() => api.get<User>(`/api/users/${userId}`), [userId])
  const plan = useAsync(() => api.get<Plan | null>(`/api/users/${userId}/plan`), [userId])
  const meetings = useAsync(
    () => api.get<MeetingBrief[]>('/api/meetings', { employee_id: userId }),
    [userId],
  )
  const stats = useAsync(
    () => api.get<EmployeeStats>(`/api/analytics/employees/${userId}`),
    [userId],
  )
  const issues = useAsync(
    () => api.get<Issue[]>('/api/issues', { employee_id: userId }),
    [userId],
  )

  function reload() {
    user.reload()
    plan.reload()
    meetings.reload()
    stats.reload()
    issues.reload()
  }

  async function run(action: () => Promise<unknown>) {
    setError(null)
    try {
      await action()
      reload()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка')
    }
  }

  if (user.loading) return <Loading />
  if (!user.data) return <ErrorBox text={user.error ?? 'Сотрудник не найден'} />

  const employee = user.data
  const canReview = employee.relation === 'manager' || employee.relation === 'admin'

  return (
    <div>
      <div className="head row" style={{ gap: 14, alignItems: 'flex-start' }}>
        <Avatar name={employee.full_name} big />
        <div>
        <h1>{employee.full_name}</h1>
        <p>
          {employee.position || '—'}{' '}
          {employee.direction ? (
            <span className="tag accent">{employee.direction.code}</span>
          ) : null}
          {employee.manager_name ? ` · руководитель: ${employee.manager_name}` : ''}
          <br />
          <span className="small">{employee.department_path.join(' / ') || '—'}</span>
        </p>
        </div>
      </div>

      <ErrorBox text={error} />

      <div className="box accent">
        <div className="stats">
          <div className="main">
            <b>{employee.progress.percent}%</b>
            <span className="small">
              план выполнен ({employee.progress.confirmed} из {employee.progress.total})
            </span>
          </div>
          <div>
            <b>{employee.progress.overdue}</b>
            <span className="small">просрочено</span>
          </div>
          <div>
            <b>{employee.progress.issues}</b>
            <span className="small">открытых проблем</span>
          </div>
          <div>
            <b>{stats.data?.meetings_held ?? 0}</b>
            <span className="small">
              встреч проведено
              {stats.data?.next_meeting_at
                ? `, следующая ${formatDateTime(stats.data.next_meeting_at)}`
                : ''}
            </span>
          </div>
        </div>
        {canReview ? (
          <div className="row">
            <button onClick={() => setMeetingModal(true)}>Назначить встречу</button>
            <button className="grey" onClick={() => setIssueFor('user')}>
              Отметить проблему
            </button>
          </div>
        ) : (
          <div className="row">
            <span className="small">
              {employee.relation === 'self'
                ? 'Это ваш профиль, PR по нему ведёт ваш руководитель.'
                : 'Только просмотр.'}
            </span>
            {employee.relation === 'self' ? (
              <button className="grey" onClick={() => setPasswordModal(true)}>
                Сменить пароль
              </button>
            ) : null}
          </div>
        )}
      </div>

      <div className="box">
        <div className="box-head">
          <h2 className="box-title">План обучения на {plan.data?.year ?? new Date().getFullYear()} год</h2>
          {canReview ? (
            plan.data ? (
              <button className="grey" onClick={() => setSkillModal(true)}>
                Добавить скилл
              </button>
            ) : (
              <button onClick={() => run(() => api.post(`/api/users/${userId}/plan`))}>
                Создать план
              </button>
            )
          ) : null}
        </div>

        {plan.loading ? (
          <Loading />
        ) : !plan.data ? (
          <p className="empty">Плана на этот год нет</p>
        ) : plan.data.items.length === 0 ? (
          <p className="empty">В плане пока нет скиллов</p>
        ) : (
          <ul className="list">
            {plan.data.items.map((item) => (
              <li key={item.id} className="item">
                <span className="grow">
                  {item.skill.name} <span className="small">({item.skill.direction?.code})</span>
                  <div className="small">
                    {item.is_confirmed
                      ? `зачтён ${formatDate(item.confirmed_at)}`
                      : `план до ${formatDate(item.target_date)}`}
                  </div>
                </span>
                {item.is_confirmed ? <span className="tag green">зачтён</span> : null}
                {item.is_overdue ? <span className="tag red">просрочен</span> : null}
                {canReview ? (
                  <>
                    <button className="link" onClick={() => setIssueFor(item)}>
                      проблема
                    </button>
                    <button
                      className="link"
                      onClick={() => run(() => api.del(`/api/users/${userId}/plan/items/${item.id}`))}
                    >
                      удалить
                    </button>
                  </>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="cols">
        <div className="box">
          <h2>PR-встречи</h2>
          {meetings.loading ? (
            <Loading />
          ) : (meetings.data ?? []).length === 0 ? (
            <p className="empty">Встреч не было</p>
          ) : (
            <ul className="list">
              {meetings.data?.map((meeting) => (
                <li key={meeting.id} className="item">
                  <span className="grow">
                    <Link to={`/meetings/${meeting.id}`}>{meeting.title}</Link>
                    <div className="small">
                      {formatDateTime(meeting.held_at ?? meeting.scheduled_at)} · проводит{' '}
                      {meeting.reviewer.full_name}
                    </div>
                  </span>
                  <span className={meeting.held_at ? 'tag green' : 'tag'}>
                    {meeting.held_at ? 'проведена' : 'запланирована'}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="box">
          <h2>Проблемы</h2>
          {issues.loading ? (
            <Loading />
          ) : (issues.data ?? []).length === 0 ? (
            <p className="empty">Проблем нет</p>
          ) : (
            <ul className="list">
              {issues.data?.map((issue) => (
                <li key={issue.id} className="item">
                  <span className="grow">
                    {issue.skill_name ?? 'По сотруднику в целом'}
                    <div className="small">{issue.comment}</div>
                    <div className="small">{formatDate(issue.created_at)}</div>
                  </span>
                  {issue.is_resolved ? (
                    <span className="tag green">закрыта</span>
                  ) : (
                    <>
                      <span className="tag amber">открыта</span>
                      {canReview ? (
                        <button
                          className="link"
                          onClick={() => run(() => api.post(`/api/issues/${issue.id}/resolve`))}
                        >
                          закрыть
                        </button>
                      ) : null}
                    </>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {skillModal && plan.data ? (
        <AddSkill
          userId={userId}
          used={plan.data.items.map((item) => item.skill.id)}
          year={plan.data.year}
          onClose={() => setSkillModal(false)}
          onDone={() => {
            setSkillModal(false)
            reload()
          }}
        />
      ) : null}

      {meetingModal ? (
        <NewMeeting
          userId={userId}
          onClose={() => setMeetingModal(false)}
          onDone={(meeting) => navigate(`/meetings/${meeting.id}`)}
        />
      ) : null}

      {passwordModal ? <ChangePassword onClose={() => setPasswordModal(false)} /> : null}

      {issueFor ? (
        <NewIssue
          userId={userId}
          item={issueFor === 'user' ? null : issueFor}
          onClose={() => setIssueFor(null)}
          onDone={() => {
            setIssueFor(null)
            reload()
          }}
        />
      ) : null}
    </div>
  )
}

function ChangePassword({ onClose }: { onClose: () => void }) {
  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [done, setDone] = useState(false)

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    try {
      await api.post('/api/auth/change-password', {
        current_password: current,
        new_password: next,
      })
      setDone(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка')
    }
  }

  return (
    <Modal title="Смена пароля" onClose={onClose}>
      <ErrorBox text={error} />
      {done ? (
        <>
          <p>Пароль изменён.</p>
          <div className="modal-buttons">
            <button onClick={onClose}>Закрыть</button>
          </div>
        </>
      ) : (
        <form onSubmit={submit}>
          <label>
            <span>Текущий пароль</span>
            <input
              type="password"
              value={current}
              onChange={(e) => setCurrent(e.target.value)}
              required
            />
          </label>
          <label>
            <span>Новый пароль (от 6 символов)</span>
            <input
              type="password"
              value={next}
              onChange={(e) => setNext(e.target.value)}
              minLength={6}
              required
            />
          </label>
          <div className="modal-buttons">
            <button type="button" className="grey" onClick={onClose}>
              Отмена
            </button>
            <button type="submit">Сохранить</button>
          </div>
        </form>
      )}
    </Modal>
  )
}

function AddSkill({
  userId,
  used,
  year,
  onClose,
  onDone,
}: {
  userId: number
  used: number[]
  year: number
  onClose: () => void
  onDone: () => void
}) {
  const skills = useAsync(() => api.get<Skill[]>('/api/skills'), [])
  const [skillId, setSkillId] = useState('')
  const [target, setTarget] = useState(`${year}-12-31`)
  const [error, setError] = useState<string | null>(null)

  const available = (skills.data ?? []).filter((skill) => !used.includes(skill.id))

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    try {
      await api.post(`/api/users/${userId}/plan/items`, {
        skill_id: Number(skillId),
        target_date: target,
      })
      onDone()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка')
    }
  }

  return (
    <Modal title="Добавить скилл в план" onClose={onClose}>
      <ErrorBox text={error} />
      <form onSubmit={submit}>
        <label>
          <span>Скилл</span>
          <select value={skillId} onChange={(e) => setSkillId(e.target.value)} required>
            <option value="">Выберите скилл</option>
            {available.map((skill) => (
              <option key={skill.id} value={skill.id}>
                [{skill.direction?.code}] {skill.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span>Плановая дата подтверждения</span>
          <input type="date" value={target} onChange={(e) => setTarget(e.target.value)} required />
        </label>
        <div className="modal-buttons">
          <button type="button" className="grey" onClick={onClose}>
            Отмена
          </button>
          <button type="submit">Добавить</button>
        </div>
      </form>
    </Modal>
  )
}

function NewMeeting({
  userId,
  onClose,
  onDone,
}: {
  userId: number
  onClose: () => void
  onDone: (meeting: Meeting) => void
}) {
  const [when, setWhen] = useState(() => {
    const date = new Date()
    date.setDate(date.getDate() + 1)
    date.setHours(12, 0, 0, 0)
    return dateTimeInput(date)
  })
  const [title, setTitle] = useState('PR-встреча')
  const [error, setError] = useState<string | null>(null)

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    try {
      const meeting = await api.post<Meeting>('/api/meetings', {
        employee_id: userId,
        scheduled_at: new Date(when).toISOString(),
        title,
      })
      onDone(meeting)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка')
    }
  }

  return (
    <Modal title="Новая встреча" onClose={onClose}>
      <ErrorBox text={error} />
      <form onSubmit={submit}>
        <label>
          <span>Дата и время</span>
          <input
            type="datetime-local"
            value={when}
            onChange={(e) => setWhen(e.target.value)}
            required
          />
        </label>
        <label>
          <span>Тема</span>
          <input value={title} onChange={(e) => setTitle(e.target.value)} />
        </label>
        <div className="modal-buttons">
          <button type="button" className="grey" onClick={onClose}>
            Отмена
          </button>
          <button type="submit">Создать</button>
        </div>
      </form>
    </Modal>
  )
}

function NewIssue({
  userId,
  item,
  onClose,
  onDone,
}: {
  userId: number
  item: PlanItem | null
  onClose: () => void
  onDone: () => void
}) {
  const [comment, setComment] = useState('')
  const [error, setError] = useState<string | null>(null)

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    try {
      await api.post(`/api/issues/${userId}`, { comment, plan_item_id: item?.id ?? null })
      onDone()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка')
    }
  }

  return (
    <Modal title={item ? `Проблема: ${item.skill.name}` : 'Проблема по сотруднику'} onClose={onClose}>
      <ErrorBox text={error} />
      <form onSubmit={submit}>
        <label>
          <span>Комментарий</span>
          <textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            required
            style={{ minHeight: 90 }}
          />
        </label>
        <div className="modal-buttons">
          <button type="button" className="grey" onClick={onClose}>
            Отмена
          </button>
          <button type="submit">Сохранить</button>
        </div>
      </form>
    </Modal>
  )
}
