/** Запросы к серверу и типы данных. */

const TOKEN = 'skillpath.token'

export function getToken(): string | null {
  return localStorage.getItem(TOKEN)
}

export function setToken(token: string | null): void {
  if (token) localStorage.setItem(TOKEN, token)
  else localStorage.removeItem(TOKEN)
}

type Params = Record<string, string | number | boolean | undefined | null>

async function request<T>(method: string, path: string, body?: unknown, params?: Params): Promise<T> {
  let url = path
  if (params) {
    const search = new URLSearchParams()
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null && value !== '') search.set(key, String(value))
    }
    if (search.toString()) url += '?' + search.toString()
  }

  const headers: Record<string, string> = {}
  const token = getToken()
  if (token) headers.Authorization = 'Bearer ' + token
  if (body !== undefined) headers['Content-Type'] = 'application/json'

  const response = await fetch(url, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  })

  if (response.status === 401) {
    // Страницу не перезагружаем: на экране входа токена нет, и перезагрузка
    // зациклилась бы. Просто чистим токен и сообщаем приложению.
    setToken(null)
    window.dispatchEvent(new Event('logout'))
    throw new Error('Сессия истекла, войдите заново')
  }
  if (!response.ok) {
    let message = 'Ошибка ' + response.status
    try {
      const data = await response.json()
      if (typeof data.detail === 'string') message = data.detail
    } catch {
      // тело не JSON, оставляем общее сообщение
    }
    throw new Error(message)
  }
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

export const api = {
  get: <T>(path: string, params?: Params) => request<T>('GET', path, undefined, params),
  post: <T>(path: string, body?: unknown, params?: Params) => request<T>('POST', path, body, params),
  put: <T>(path: string, body?: unknown) => request<T>('PUT', path, body),
  patch: <T>(path: string, body?: unknown) => request<T>('PATCH', path, body),
  del: <T>(path: string) => request<T>('DELETE', path),
}

export interface Direction {
  id: number
  code: string
  name: string
}

export interface Skill {
  id: number
  name: string
  description: string
  direction_id: number
  direction: Direction | null
}

export interface Department {
  id: number
  name: string
  parent_id: number | null
  head_id: number | null
}

export interface UserBrief {
  id: number
  full_name: string
  position: string
}

export interface DepartmentNode extends Department {
  head_name: string | null
  members: UserBrief[]
  children: DepartmentNode[]
}

export interface Progress {
  total: number
  confirmed: number
  overdue: number
  issues: number
  percent: number
}

export interface User {
  id: number
  email: string
  full_name: string
  position: string
  is_admin: boolean
  direction: Direction | null
  department: Department | null
  department_path: string[]
  manager_name: string | null
  relation: 'admin' | 'manager' | 'self' | 'none'
  progress: Progress
}

export interface Me {
  user: User
  is_admin: boolean
  subordinates: number
}

export interface PlanItem {
  id: number
  skill: Skill
  target_date: string
  is_confirmed: boolean
  confirmed_at: string | null
  is_overdue: boolean
}

export interface Plan {
  id: number
  year: number
  items: PlanItem[]
  progress: Progress
}

export interface Mark {
  id: number
  plan_item_id: number
  is_confirmed: boolean
  comment: string
  skill_name: string
}

export interface Link {
  id: number
  title: string
  url: string
}

export interface Issue {
  id: number
  employee_id: number
  meeting_id: number | null
  comment: string
  is_resolved: boolean
  created_at: string
  skill_name: string | null
  employee_name: string
}

export interface Meeting {
  id: number
  employee: UserBrief
  reviewer: UserBrief
  scheduled_at: string
  held_at: string | null
  title: string
  notes_md: string
  marks: Mark[]
  links: Link[]
  issues: Issue[]
}

export interface MeetingBrief {
  id: number
  employee: UserBrief
  reviewer: UserBrief
  scheduled_at: string
  held_at: string | null
  title: string
}

export interface DepartmentStats {
  id: number
  name: string
  employees: number
  progress: Progress
  meetings_held: number
  at_risk: User[]
}

export interface EmployeeStats {
  progress: Progress
  confirmed: PlanItem[]
  overdue: PlanItem[]
  issues: Issue[]
  meetings_held: number
  next_meeting_at: string | null
}

export interface Event {
  kind: 'meeting' | 'deadline'
  id: number
  date: string
  title: string
  employee_id: number
  employee_name: string
  done: boolean
}
