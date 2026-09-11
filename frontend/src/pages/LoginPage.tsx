import { useState } from 'react'

import { api } from '../api'
import { useAuth } from '../auth'
import { useAsync } from '../hooks'
import { ErrorBox } from '../ui'

export default function LoginPage() {
  const { login, register } = useAuth()
  const [tab, setTab] = useState<'login' | 'register'>('login')

  const setup = useAsync(() => api.get<{ empty: boolean }>('/api/auth/needs-setup'), [])
  const isEmpty = setup.data?.empty === true

  return (
    <div className="login">
      <div className="row" style={{ gap: 10, marginBottom: 4 }}>
        <span className="mark">S</span>
        <h1>SkillPath</h1>
      </div>
      <p className="small">Система мониторинга развития технических навыков</p>

      {isEmpty ? (
        <div className="box accent" style={{ marginTop: 16 }}>
          <b>Система пустая</b>
          <p className="small" style={{ margin: '4px 0 0' }}>
            Первый зарегистрировавшийся становится администратором: заводит подразделения,
            справочник скиллов и распределяет сотрудников.
          </p>
        </div>
      ) : null}

      <div className="box">
        <div className="row" style={{ marginBottom: 14 }}>
          <button
            className={tab === 'login' ? '' : 'grey'}
            onClick={() => setTab('login')}
            type="button"
          >
            Вход
          </button>
          <button
            className={tab === 'register' ? '' : 'grey'}
            onClick={() => setTab('register')}
            type="button"
          >
            Регистрация
          </button>
        </div>

        {tab === 'login' ? (
          <LoginForm onSubmit={login} />
        ) : (
          <RegisterForm onSubmit={register} isFirst={isEmpty} />
        )}
      </div>
    </div>
  )
}

function LoginForm({
  onSubmit,
}: {
  onSubmit: (email: string, password: string) => Promise<void>
}) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await onSubmit(email, password)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось войти')
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={submit}>
      <ErrorBox text={error} />
      <label>
        <span>Рабочая почта</span>
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          autoComplete="username"
          required
        />
      </label>
      <label>
        <span>Пароль</span>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete="current-password"
          required
        />
      </label>
      <button type="submit" disabled={busy}>
        {busy ? 'Входим…' : 'Войти'}
      </button>
    </form>
  )
}

function RegisterForm({
  onSubmit,
  isFirst,
}: {
  onSubmit: (data: {
    email: string
    full_name: string
    password: string
    position: string
  }) => Promise<void>
  isFirst: boolean
}) {
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [position, setPosition] = useState('')
  const [password, setPassword] = useState('')
  const [repeat, setRepeat] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    if (password !== repeat) {
      setError('Пароли не совпадают')
      return
    }
    setBusy(true)
    setError(null)
    try {
      await onSubmit({ email, full_name: fullName, password, position })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось зарегистрироваться')
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={submit}>
      <ErrorBox text={error} />
      <label>
        <span>ФИО</span>
        <input
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
          placeholder="Иванов Иван"
          required
        />
      </label>
      <label>
        <span>Рабочая почта</span>
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          autoComplete="username"
          required
        />
      </label>
      <label>
        <span>Должность</span>
        <input
          value={position}
          onChange={(e) => setPosition(e.target.value)}
          placeholder="Backend-разработчик"
        />
      </label>
      <label>
        <span>Пароль (от 6 символов)</span>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete="new-password"
          minLength={6}
          required
        />
      </label>
      <label>
        <span>Пароль ещё раз</span>
        <input
          type="password"
          value={repeat}
          onChange={(e) => setRepeat(e.target.value)}
          autoComplete="new-password"
          required
        />
      </label>
      <button type="submit" disabled={busy}>
        {busy ? 'Регистрируем…' : isFirst ? 'Зарегистрироваться как владелец' : 'Зарегистрироваться'}
      </button>
      {!isFirst ? (
        <p className="small" style={{ marginBottom: 0 }}>
          После регистрации администратор добавит вас в подразделение и назначит направление.
        </p>
      ) : null}
    </form>
  )
}
