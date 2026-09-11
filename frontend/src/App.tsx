import { NavLink, Navigate, Route, Routes } from 'react-router-dom'

import { useAuth } from './auth'
import AdminPage from './pages/AdminPage'
import CalendarPage from './pages/CalendarPage'
import DashboardPage from './pages/DashboardPage'
import EmployeePage from './pages/EmployeePage'
import EmployeesPage from './pages/EmployeesPage'
import LoginPage from './pages/LoginPage'
import MeetingPage from './pages/MeetingPage'
import StructurePage from './pages/StructurePage'
import { Loading } from './ui'

export default function App() {
  const { me, loading, logout } = useAuth()

  if (loading) return <Loading />
  if (!me) return <LoginPage />

  const role = me.is_admin
    ? 'администратор'
    : me.subordinates > 0
      ? `руководитель, подчинённых: ${me.subordinates}`
      : 'сотрудник'

  return (
    <div className="layout">
      <div className="menu">
        <div className="brand">
          <span className="mark">S</span>
          <div>
            SkillPath
            <span>Performance Review</span>
          </div>
        </div>

        <NavLink to="/" end>
          Главная
        </NavLink>
        <NavLink to="/calendar">Календарь</NavLink>
        <NavLink to="/employees">Сотрудники</NavLink>
        <NavLink to="/structure">Структура</NavLink>
        <NavLink to={`/employees/${me.user.id}`}>Моё развитие</NavLink>
        {me.is_admin ? <NavLink to="/admin">Администрирование</NavLink> : null}

        <div className="who">
          <b>{me.user.full_name}</b>
          {role}
          <br />
          <button className="link" style={{ marginLeft: -6 }} onClick={logout}>
            выйти
          </button>
        </div>
      </div>

      <div className="content">
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/calendar" element={<CalendarPage />} />
          <Route path="/employees" element={<EmployeesPage />} />
          <Route path="/employees/:id" element={<EmployeePage />} />
          <Route path="/meetings/:id" element={<MeetingPage />} />
          <Route path="/structure" element={<StructurePage />} />
          <Route path="/admin" element={me.is_admin ? <AdminPage /> : <Navigate to="/" />} />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </div>
    </div>
  )
}
