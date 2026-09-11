import { useState } from 'react'
import { api, type Department, type DepartmentNode, type User } from '../api'
import { useAuth } from '../auth'
import { useAsync } from '../hooks'
import { ErrorBox, Loading, Modal, Person } from '../ui'

function Node({
  node,
  isAdmin,
  onEdit,
}: {
  node: DepartmentNode
  isAdmin: boolean
  onEdit: (node: DepartmentNode) => void
}) {
  return (
    <div className="tree-item">
      <div className="item">
        <span className="grow">
          <b className="box-title">{node.name}</b>
          <div className="small">
            {node.head_name ? `руководитель: ${node.head_name}` : 'руководитель не назначен'}
          </div>
        </span>
        {isAdmin ? (
          <button className="link" onClick={() => onEdit(node)}>
            изменить
          </button>
        ) : null}
      </div>

      <div className="tree">
        {node.members.map((member) => (
          <div key={member.id} className="tree-member">
            <Person id={member.id} name={member.full_name} />
            {member.position ? <span className="small">{member.position}</span> : null}
          </div>
        ))}
        {node.children.map((child) => (
          <Node key={child.id} node={child} isAdmin={isAdmin} onEdit={onEdit} />
        ))}
      </div>
    </div>
  )
}

export default function StructurePage() {
  const { me } = useAuth()
  const isAdmin = me?.is_admin ?? false
  const [editing, setEditing] = useState<DepartmentNode | 'new' | null>(null)
  const [error, setError] = useState<string | null>(null)

  const tree = useAsync(() => api.get<DepartmentNode[]>('/api/departments/tree'), [])
  const flat = useAsync(() => api.get<Department[]>('/api/departments'), [])
  const users = useAsync(() => api.get<User[]>('/api/users'), [])

  function reload() {
    tree.reload()
    flat.reload()
  }

  return (
    <div>
      <div className="head">
        <h1>Структура подразделений</h1>
        <p>
          Дерево любой вложенности. Руководитель подразделения ведёт PR всех сотрудников своего
          узла и всех вложенных.
        </p>
      </div>

      <ErrorBox text={error} />

      <div className="box">
        {isAdmin ? (
          <div className="box-head">
            <span />
            <button onClick={() => setEditing('new')}>Новое подразделение</button>
          </div>
        ) : null}

        {tree.loading ? (
          <Loading />
        ) : (tree.data ?? []).length === 0 ? (
          <p className="empty">Вам не подчиняется ни одно подразделение</p>
        ) : (
          tree.data?.map((node) => (
            <Node key={node.id} node={node} isAdmin={isAdmin} onEdit={setEditing} />
          ))
        )}
      </div>

      {editing ? (
        <DepartmentForm
          department={editing === 'new' ? null : editing}
          departments={flat.data ?? []}
          users={users.data ?? []}
          onClose={() => setEditing(null)}
          onDone={() => {
            setEditing(null)
            reload()
          }}
          onError={setError}
        />
      ) : null}
    </div>
  )
}

function DepartmentForm({
  department,
  departments,
  users,
  onClose,
  onDone,
  onError,
}: {
  department: DepartmentNode | null
  departments: Department[]
  users: User[]
  onClose: () => void
  onDone: () => void
  onError: (text: string) => void
}) {
  const [name, setName] = useState(department?.name ?? '')
  const [parentId, setParentId] = useState(String(department?.parent_id ?? ''))
  const [headId, setHeadId] = useState(String(department?.head_id ?? ''))
  const [error, setError] = useState<string | null>(null)

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    const body = {
      name,
      parent_id: parentId ? Number(parentId) : null,
      head_id: headId ? Number(headId) : null,
    }
    try {
      if (department) await api.patch(`/api/departments/${department.id}`, body)
      else await api.post('/api/departments', body)
      onDone()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка')
    }
  }

  async function remove() {
    if (!department || !confirm(`Удалить «${department.name}»?`)) return
    try {
      await api.del(`/api/departments/${department.id}`)
      onDone()
    } catch (err) {
      onError(err instanceof Error ? err.message : 'Ошибка')
      onClose()
    }
  }

  return (
    <Modal title={department ? department.name : 'Новое подразделение'} onClose={onClose}>
      <ErrorBox text={error} />
      <form onSubmit={submit}>
        <label>
          <span>Название</span>
          <input value={name} onChange={(e) => setName(e.target.value)} required />
        </label>
        <label>
          <span>Входит в подразделение</span>
          <select value={parentId} onChange={(e) => setParentId(e.target.value)}>
            <option value="">— верхний уровень —</option>
            {departments
              .filter((item) => item.id !== department?.id)
              .map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))}
          </select>
        </label>
        <label>
          <span>Руководитель</span>
          <select value={headId} onChange={(e) => setHeadId(e.target.value)}>
            <option value="">— не назначен —</option>
            {users.map((user) => (
              <option key={user.id} value={user.id}>
                {user.full_name}
              </option>
            ))}
          </select>
        </label>
        <div className="modal-buttons">
          {department ? (
            <button type="button" className="grey" onClick={remove}>
              Удалить
            </button>
          ) : null}
          <button type="button" className="grey" onClick={onClose}>
            Отмена
          </button>
          <button type="submit">Сохранить</button>
        </div>
      </form>
    </Modal>
  )
}
