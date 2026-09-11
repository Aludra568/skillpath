import { useState } from 'react'

import { api, type CompanyBrief, type RegisterData } from '../api'
import { useAuth } from '../auth'
import { useAsync } from '../hooks'
import { ErrorBox } from '../ui'

export default function LoginPage() {
  const { login, register } = useAuth()
  const [tab, setTab] = useState<'login' | 'register'>('login')

  const companies = useAsync(() => api.get<CompanyBrief[]>('/api/auth/companies'), [])

  return (
    <div className="login">
      <div className="row" style={{ gap: 10, marginBottom: 4 }}>
        <span className="mark">S</span>
        <h1>SkillPath</h1>
      </div>
      <p className="small">Система мониторинга развития технических навыков</p>

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
          <RegisterForm onSubmit={register} companies={companies.data ?? []} />
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
  companies,
}: {
  onSubmit: (data: RegisterData) => Promise<void>
  companies: CompanyBrief[]
}) {
  const [mode, setMode] = useState<'create' | 'join'>('create')
  const [companyName, setCompanyName] = useState('')
  const [companyId, setCompanyId] = useState<number | ''>('')
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
    if (mode === 'join' && companyId === '') {
      setError('Выберите компанию')
      return
    }
    setBusy(true)
    setError(null)
    try {
      await onSubmit({
        email,
        full_name: fullName,
        password,
        position,
        mode,
        company_name: mode === 'create' ? companyName : '',
        company_id: mode === 'join' ? Number(companyId) : null,
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось зарегистрироваться')
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={submit}>
      <ErrorBox text={error} />

      <div className="row" style={{ marginBottom: 12 }}>
        <button
          type="button"
          className={mode === 'create' ? 'small' : 'grey small'}
          onClick={() => setMode('create')}
        >
          Создать компанию
        </button>
        <button
          type="button"
          className={mode === 'join' ? 'small' : 'grey small'}
          onClick={() => setMode('join')}
        >
          Присоединиться
        </button>
      </div>

      {mode === 'create' ? (
        <>
          <p className="small" style={{ marginTop: 0 }}>
            Вы заводите компанию и становитесь её администратором: создаёте подразделения,
            справочник скиллов и добавляете сотрудников.
          </p>
          <label>
            <span>Название компании</span>
            <input
              value={companyName}
              onChange={(e) => setCompanyName(e.target.value)}
              placeholder="ООО «Ромашка»"
              required
            />
          </label>
        </>
      ) : (
        <>
          <p className="small" style={{ marginTop: 0 }}>
            Вы вступаете как сотрудник. Пока администратор не добавит вас в подразделение, вы
            видите только себя.
          </p>
          <label>
            <span>Компания</span>
            <select
              value={companyId}
              onChange={(e) => setCompanyId(e.target.value === '' ? '' : Number(e.target.value))}
              required
            >
              <option value="">Выберите компанию…</option>
              {companies.map((company) => (
                <option key={company.id} value={company.id}>
                  {company.name} ({company.employees})
                </option>
              ))}
            </select>
          </label>
          {companies.length === 0 ? (
            <p className="small">
              Пока ни одной компании не создано — выберите «Создать компанию».
            </p>
          ) : null}
        </>
      )}

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
        {busy
          ? 'Регистрируем…'
          : mode === 'create'
            ? 'Создать компанию'
            : 'Присоединиться к компании'}
      </button>
    </form>
  )
}
