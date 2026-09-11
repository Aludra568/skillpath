import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'

import { api, type Meeting, type Plan, type User } from '../api'
import { useAsync } from '../hooks'
import { ErrorBox, Loading, Markdown, Person, formatDateTime } from '../ui'

export default function MeetingPage() {
  const { id } = useParams()
  const meetingId = Number(id)
  const navigate = useNavigate()

  const [error, setError] = useState<string | null>(null)
  const [notes, setNotes] = useState('')
  const [changed, setChanged] = useState(false)
  const [linkTitle, setLinkTitle] = useState('')
  const [linkUrl, setLinkUrl] = useState('')

  const meeting = useAsync(() => api.get<Meeting>(`/api/meetings/${meetingId}`), [meetingId])
  const employeeId = meeting.data?.employee.id
  const employee = useAsync(
    () => (employeeId ? api.get<User>(`/api/users/${employeeId}`) : Promise.resolve(null)),
    [employeeId],
  )
  const plan = useAsync(
    () => (employeeId ? api.get<Plan | null>(`/api/users/${employeeId}/plan`) : Promise.resolve(null)),
    [employeeId],
  )

  useEffect(() => {
    if (meeting.data && !changed) setNotes(meeting.data.notes_md)
    // черновик не затираем, пока его правят
  }, [meeting.data, changed])

  const canReview =
    employee.data?.relation === 'manager' || employee.data?.relation === 'admin'

  async function run(action: () => Promise<unknown>) {
    setError(null)
    try {
      await action()
      meeting.reload()
      plan.reload()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка')
    }
  }

  if (meeting.loading) return <Loading />
  if (!meeting.data) return <ErrorBox text={meeting.error ?? 'Встреча не найдена'} />

  const data = meeting.data
  const marks = new Map(data.marks.map((mark) => [mark.plan_item_id, mark]))

  return (
    <div>
      <div className="head">
        <div className="row" style={{ marginBottom: 6 }}>
          <Person id={data.employee.id} name={data.employee.full_name} />
          <span className="small">протокол встречи</span>
        </div>
        <h1>{data.title}</h1>
        <p className="small">
          {formatDateTime(data.held_at ?? data.scheduled_at)} · проводит {data.reviewer.full_name} ·{' '}
          {data.held_at ? 'проведена' : 'запланирована'}
        </p>
      </div>

      <ErrorBox text={error} />

      {canReview ? (
        <div className="box row">
          {data.held_at ? (
            <button
              className="grey"
              onClick={() => run(() => api.patch(`/api/meetings/${meetingId}`, { is_held: false }))}
            >
              Вернуть в запланированные
            </button>
          ) : (
            <button
              onClick={() => run(() => api.patch(`/api/meetings/${meetingId}`, { is_held: true }))}
            >
              Отметить проведённой
            </button>
          )}
          <button
            className="grey"
            onClick={async () => {
              if (!confirm('Удалить встречу вместе с протоколом?')) return
              await api.del(`/api/meetings/${meetingId}`)
              navigate(`/employees/${data.employee.id}`)
            }}
          >
            Удалить встречу
          </button>
        </div>
      ) : null}

      <div className="cols">
        <div>
          <div className="box">
            <div className="box-head">
              <h2 className="box-title">Итоги встречи</h2>
              {canReview ? (
                <button
                  disabled={!changed}
                  onClick={() =>
                    run(async () => {
                      await api.patch(`/api/meetings/${meetingId}`, { notes_md: notes })
                      setChanged(false)
                    })
                  }
                >
                  Сохранить
                </button>
              ) : null}
            </div>

            {canReview ? (
              <>
                <textarea
                  value={notes}
                  onChange={(e) => {
                    setNotes(e.target.value)
                    setChanged(true)
                  }}
                  placeholder={'## Итоги\n- что обсудили\n- о чём договорились'}
                />
                <p className="small">Можно писать в Markdown. Ниже — как это будет выглядеть.</p>
              </>
            ) : null}
            <Markdown text={notes} />
          </div>

          <div className="box">
            <h2>Ссылки</h2>
            {data.links.length === 0 ? <p className="empty">Ссылок нет</p> : null}
            <ul className="list">
              {data.links.map((link) => (
                <li key={link.id} className="item">
                  <span className="grow">
                    <a href={link.url} target="_blank" rel="noreferrer">
                      {link.title}
                    </a>
                  </span>
                  {canReview ? (
                    <button
                      className="link"
                      onClick={() => run(() => api.del(`/api/meetings/${meetingId}/links/${link.id}`))}
                    >
                      удалить
                    </button>
                  ) : null}
                </li>
              ))}
            </ul>

            {canReview ? (
              <form
                className="row"
                onSubmit={(event) => {
                  event.preventDefault()
                  void run(async () => {
                    await api.post(`/api/meetings/${meetingId}/links`, {
                      title: linkTitle,
                      url: linkUrl,
                    })
                    setLinkTitle('')
                    setLinkUrl('')
                  })
                }}
              >
                <input
                  placeholder="Название"
                  value={linkTitle}
                  onChange={(e) => setLinkTitle(e.target.value)}
                  style={{ width: 150 }}
                />
                <input
                  placeholder="https://..."
                  value={linkUrl}
                  onChange={(e) => setLinkUrl(e.target.value)}
                  style={{ width: 220 }}
                  required
                />
                <button type="submit" className="grey">
                  Добавить
                </button>
              </form>
            ) : null}
          </div>
        </div>

        <div>
          <div className="box">
            <h2>Скиллы из плана</h2>
            {plan.loading ? (
              <Loading />
            ) : !plan.data || plan.data.items.length === 0 ? (
              <p className="empty">
                У сотрудника нет плана.{' '}
                <Link to={`/employees/${data.employee.id}`}>Создать план</Link>
              </p>
            ) : (
              <ul className="list">
                {plan.data.items.map((item) => {
                  const mark = marks.get(item.id)
                  return (
                    <li key={item.id} className="item">
                      <span className="grow">
                        {item.skill.name}
                        {/* Скилл могли зачесть на другой встрече — показываем это,
                            чтобы руководитель не зачитывал его повторно. */}
                        {item.is_confirmed && !mark?.is_confirmed ? (
                          <span className="tag green" style={{ marginLeft: 8 }}>
                            уже зачтён
                          </span>
                        ) : null}
                        <div className="small">
                          план до {new Date(item.target_date).toLocaleDateString('ru-RU')}
                          {mark && !mark.is_confirmed ? ' · обсуждали' : ''}
                          {mark?.is_confirmed ? ' · зачтён на этой встрече' : ''}
                          {item.is_confirmed && !mark?.is_confirmed && item.confirmed_at
                            ? ` · зачтён ${new Date(item.confirmed_at).toLocaleDateString('ru-RU')}`
                            : ''}
                        </div>
                      </span>

                      {canReview ? (
                        <>
                          <button
                            className={mark && !mark.is_confirmed ? '' : 'grey'}
                            onClick={() =>
                              run(() =>
                                api.put(`/api/meetings/${meetingId}/marks`, {
                                  plan_item_id: item.id,
                                  is_confirmed: false,
                                }),
                              )
                            }
                          >
                            обсуждали
                          </button>
                          <button
                            className={mark?.is_confirmed ? '' : 'grey'}
                            onClick={() =>
                              run(() =>
                                api.put(`/api/meetings/${meetingId}/marks`, {
                                  plan_item_id: item.id,
                                  is_confirmed: true,
                                }),
                              )
                            }
                          >
                            зачесть
                          </button>
                          {mark ? (
                            <button
                              className="link"
                              onClick={() =>
                                run(() =>
                                  api.del(`/api/meetings/${meetingId}/marks/${mark.id}`),
                                )
                              }
                            >
                              снять
                            </button>
                          ) : null}
                        </>
                      ) : mark ? (
                        <span className={mark.is_confirmed ? 'tag green' : 'tag'}>
                          {mark.is_confirmed ? 'зачтён' : 'обсуждали'}
                        </span>
                      ) : null}
                    </li>
                  )
                })}
              </ul>
            )}
          </div>

          <div className="box">
            <h2>Проблемы по встрече</h2>
            {data.issues.length === 0 ? (
              <p className="empty">
                Проблем нет. Завести можно в{' '}
                <Link to={`/employees/${data.employee.id}`}>карточке сотрудника</Link>.
              </p>
            ) : (
              <ul className="list">
                {data.issues.map((issue) => (
                  <li key={issue.id}>
                    {issue.skill_name ?? 'По сотруднику в целом'}
                    <div className="small">{issue.comment}</div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
