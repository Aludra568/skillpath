import { useState } from 'react'

import { api, type Department, type Direction, type Skill, type User } from '../api'
import { useAsync } from '../hooks'
import { ErrorBox, Loading, Modal } from '../ui'

/** Одна страница администратора: направления, скиллы и пользователи. */
export default function AdminPage() {
  const [tab, setTab] = useState<'skills' | 'users'>('skills')
  const [error, setError] = useState<string | null>(null)

  const directions = useAsync(() => api.get<Direction[]>('/api/directions'), [])
  const skills = useAsync(() => api.get<Skill[]>('/api/skills'), [])
  const users = useAsync(() => api.get<User[]>('/api/users'), [])
  const departments = useAsync(() => api.get<Department[]>('/api/departments'), [])

  const [directionForm, setDirectionForm] = useState<Direction | 'new' | null>(null)
  const [skillForm, setSkillForm] = useState<Skill | 'new' | null>(null)
  const [userForm, setUserForm] = useState<User | 'new' | null>(null)

  const unassigned = (users.data ?? []).filter((user) => user.department === null)

  async function run(action: () => Promise<unknown>, reload: () => void) {
    setError(null)
    try {
      await action()
      reload()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка')
    }
  }

  return (
    <div>
      <div className="head">
        <h1>Администрирование</h1>
        <p>Справочник скиллов и учётные записи сотрудников.</p>
      </div>

      <div className="row" style={{ marginBottom: 12 }}>
        <button className={tab === 'skills' ? '' : 'grey'} onClick={() => setTab('skills')}>
          Справочник
        </button>
        <button className={tab === 'users' ? '' : 'grey'} onClick={() => setTab('users')}>
          Пользователи
        </button>
      </div>

      <ErrorBox text={error} />

      {tab === 'skills' ? (
        <>
          <div className="box">
            <div className="box-head">
              <h2>Направления</h2>
              <button className="grey" onClick={() => setDirectionForm('new')}>
                Добавить
              </button>
            </div>
            {directions.loading ? (
              <Loading />
            ) : (
              <ul className="list">
                {directions.data?.map((direction) => (
                  <li key={direction.id} className="item">
                    <span className="grow">
                      <b>{direction.code}</b> — {direction.name}
                    </span>
                    <button className="link" onClick={() => setDirectionForm(direction)}>
                      изменить
                    </button>
                    <button
                      className="link"
                      onClick={() =>
                        run(() => api.del(`/api/directions/${direction.id}`), directions.reload)
                      }
                    >
                      удалить
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="box">
            <div className="box-head">
              <h2>Скиллы ({skills.data?.length ?? 0})</h2>
              <button className="grey" onClick={() => setSkillForm('new')}>
                Добавить
              </button>
            </div>
            {skills.loading ? (
              <Loading />
            ) : (
              <table>
                <thead>
                  <tr>
                    <th>Название</th>
                    <th>Направление</th>
                    <th>Описание</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {skills.data?.map((skill) => (
                    <tr key={skill.id}>
                      <td>{skill.name}</td>
                      <td>{skill.direction?.code}</td>
                      <td className="small">{skill.description || '—'}</td>
                      <td>
                        <button className="link" onClick={() => setSkillForm(skill)}>
                          изменить
                        </button>
                        <button
                          className="link"
                          onClick={() => run(() => api.del(`/api/skills/${skill.id}`), skills.reload)}
                        >
                          удалить
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </>
      ) : (
        <>
          {unassigned.length > 0 ? (
            <div className="box accent">
              <h2 className="box-title">Новые сотрудники ({unassigned.length})</h2>
              <p className="small">
                Зарегистрировались сами, но ещё не добавлены в структуру. Пока они видят только
                себя.
              </p>
              <ul className="list">
                {unassigned.map((user) => (
                  <li key={user.id} className="item">
                    <span className="grow">
                      <b>{user.full_name}</b>
                      <div className="small">
                        {user.position || 'должность не указана'} · {user.email}
                      </div>
                    </span>
                    <button onClick={() => setUserForm(user)}>Добавить в подразделение</button>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          <div className="box">
          <div className="box-head">
            <h2 className="box-title">Пользователи ({users.data?.length ?? 0})</h2>
            <button className="grey" onClick={() => setUserForm('new')}>
              Добавить
            </button>
          </div>
          {users.loading ? (
            <Loading />
          ) : (
            <table>
              <thead>
                <tr>
                  <th>ФИО</th>
                  <th>Почта</th>
                  <th>Направление</th>
                  <th>Подразделение</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {users.data?.map((user) => (
                  <tr key={user.id}>
                    <td>
                      {user.full_name}
                      {user.is_admin ? <span className="tag"> админ</span> : null}
                      <div className="small">{user.position}</div>
                    </td>
                    <td className="small">{user.email}</td>
                    <td>{user.direction?.code ?? '—'}</td>
                    <td className="small">{user.department_path.join(' / ') || '—'}</td>
                    <td>
                      <button className="link" onClick={() => setUserForm(user)}>
                        изменить
                      </button>
                      <button
                        className="link"
                        onClick={() => run(() => api.del(`/api/users/${user.id}`), users.reload)}
                      >
                        удалить
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          </div>
        </>
      )}

      {directionForm ? (
        <DirectionForm
          direction={directionForm === 'new' ? null : directionForm}
          onClose={() => setDirectionForm(null)}
          onDone={() => {
            setDirectionForm(null)
            directions.reload()
          }}
        />
      ) : null}

      {skillForm ? (
        <SkillForm
          skill={skillForm === 'new' ? null : skillForm}
          directions={directions.data ?? []}
          onClose={() => setSkillForm(null)}
          onDone={() => {
            setSkillForm(null)
            skills.reload()
          }}
        />
      ) : null}

      {userForm ? (
        <UserForm
          user={userForm === 'new' ? null : userForm}
          directions={directions.data ?? []}
          departments={departments.data ?? []}
          onClose={() => setUserForm(null)}
          onDone={() => {
            setUserForm(null)
            users.reload()
          }}
        />
      ) : null}
    </div>
  )
}

function DirectionForm({
  direction,
  onClose,
  onDone,
}: {
  direction: Direction | null
  onClose: () => void
  onDone: () => void
}) {
  const [code, setCode] = useState(direction?.code ?? '')
  const [name, setName] = useState(direction?.name ?? '')
  const [error, setError] = useState<string | null>(null)

  return (
    <Modal title={direction ? 'Изменить направление' : 'Новое направление'} onClose={onClose}>
      <ErrorBox text={error} />
      <form
        onSubmit={async (event) => {
          event.preventDefault()
          try {
            const body = { code, name }
            if (direction) await api.patch(`/api/directions/${direction.id}`, body)
            else await api.post('/api/directions', body)
            onDone()
          } catch (err) {
            setError(err instanceof Error ? err.message : 'Ошибка')
          }
        }}
      >
        <label>
          <span>Код</span>
          <input value={code} onChange={(e) => setCode(e.target.value.toUpperCase())} required />
        </label>
        <label>
          <span>Название</span>
          <input value={name} onChange={(e) => setName(e.target.value)} required />
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

function SkillForm({
  skill,
  directions,
  onClose,
  onDone,
}: {
  skill: Skill | null
  directions: Direction[]
  onClose: () => void
  onDone: () => void
}) {
  const [name, setName] = useState(skill?.name ?? '')
  const [description, setDescription] = useState(skill?.description ?? '')
  const [directionId, setDirectionId] = useState(
    String(skill?.direction_id ?? directions[0]?.id ?? ''),
  )
  const [error, setError] = useState<string | null>(null)

  return (
    <Modal title={skill ? 'Изменить скилл' : 'Новый скилл'} onClose={onClose}>
      <ErrorBox text={error} />
      <form
        onSubmit={async (event) => {
          event.preventDefault()
          try {
            const body = { name, description, direction_id: Number(directionId) }
            if (skill) await api.patch(`/api/skills/${skill.id}`, body)
            else await api.post('/api/skills', body)
            onDone()
          } catch (err) {
            setError(err instanceof Error ? err.message : 'Ошибка')
          }
        }}
      >
        <label>
          <span>Название</span>
          <input value={name} onChange={(e) => setName(e.target.value)} required />
        </label>
        <label>
          <span>Направление</span>
          <select value={directionId} onChange={(e) => setDirectionId(e.target.value)}>
            {directions.map((direction) => (
              <option key={direction.id} value={direction.id}>
                {direction.code} — {direction.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span>Описание</span>
          <input value={description} onChange={(e) => setDescription(e.target.value)} />
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

function UserForm({
  user,
  directions,
  departments,
  onClose,
  onDone,
}: {
  user: User | null
  directions: Direction[]
  departments: Department[]
  onClose: () => void
  onDone: () => void
}) {
  const [fullName, setFullName] = useState(user?.full_name ?? '')
  const [email, setEmail] = useState(user?.email ?? '')
  const [position, setPosition] = useState(user?.position ?? '')
  const [password, setPassword] = useState('')
  const [isAdmin, setIsAdmin] = useState(user?.is_admin ?? false)
  const [directionId, setDirectionId] = useState(String(user?.direction?.id ?? ''))
  const [departmentId, setDepartmentId] = useState(String(user?.department?.id ?? ''))
  const [error, setError] = useState<string | null>(null)

  return (
    <Modal title={user ? user.full_name : 'Новый пользователь'} onClose={onClose}>
      <ErrorBox text={error} />
      <form
        onSubmit={async (event) => {
          event.preventDefault()
          const body = {
            full_name: fullName,
            email,
            position,
            is_admin: isAdmin,
            password: password || null,
            direction_id: directionId ? Number(directionId) : null,
            department_id: departmentId ? Number(departmentId) : null,
          }
          try {
            if (user) await api.patch(`/api/users/${user.id}`, body)
            else await api.post('/api/users', body)
            onDone()
          } catch (err) {
            setError(err instanceof Error ? err.message : 'Ошибка')
          }
        }}
      >
        <label>
          <span>ФИО</span>
          <input value={fullName} onChange={(e) => setFullName(e.target.value)} required />
        </label>
        <label>
          <span>Почта</span>
          <input value={email} onChange={(e) => setEmail(e.target.value)} required />
        </label>
        <label>
          <span>Должность</span>
          <input value={position} onChange={(e) => setPosition(e.target.value)} />
        </label>
        <label>
          <span>{user ? 'Новый пароль (если нужно сменить)' : 'Пароль'}</span>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required={!user}
          />
        </label>
        <label>
          <span>Направление</span>
          <select value={directionId} onChange={(e) => setDirectionId(e.target.value)}>
            <option value="">— не задано —</option>
            {directions.map((direction) => (
              <option key={direction.id} value={direction.id}>
                {direction.code}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span>Подразделение</span>
          <select value={departmentId} onChange={(e) => setDepartmentId(e.target.value)}>
            <option value="">— не задано —</option>
            {departments.map((department) => (
              <option key={department.id} value={department.id}>
                {department.name}
              </option>
            ))}
          </select>
        </label>
        <label className="row">
          <input
            type="checkbox"
            checked={isAdmin}
            onChange={(e) => setIsAdmin(e.target.checked)}
            style={{ width: 16 }}
          />
          <span style={{ margin: 0 }}>Администратор</span>
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
