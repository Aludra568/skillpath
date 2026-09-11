import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { api, type Event } from '../api'
import { useAsync } from '../hooks'
import { ErrorBox, Loading, dateInput } from '../ui'

const WEEKDAYS = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
const MONTHS = [
  'Январь',
  'Февраль',
  'Март',
  'Апрель',
  'Май',
  'Июнь',
  'Июль',
  'Август',
  'Сентябрь',
  'Октябрь',
  'Ноябрь',
  'Декабрь',
]

/** Календарь: встречи и плановые даты подтверждения скиллов в одной сетке. */
export default function CalendarPage() {
  const navigate = useNavigate()
  const [month, setMonth] = useState(() => {
    const now = new Date()
    return new Date(now.getFullYear(), now.getMonth(), 1)
  })

  // Сетка всегда начинается с понедельника и заканчивается воскресеньем.
  const days = useMemo(() => {
    const first = new Date(month.getFullYear(), month.getMonth(), 1)
    const last = new Date(month.getFullYear(), month.getMonth() + 1, 0)
    const start = new Date(first)
    start.setDate(first.getDate() - ((first.getDay() + 6) % 7))
    const end = new Date(last)
    end.setDate(last.getDate() + (6 - ((last.getDay() + 6) % 7)))

    const result: Date[] = []
    for (const day = new Date(start); day <= end; day.setDate(day.getDate() + 1)) {
      result.push(new Date(day))
    }
    return result
  }, [month])

  const events = useAsync(
    () =>
      api.get<Event[]>('/api/events', {
        date_from: dateInput(days[0]),
        date_to: dateInput(days[days.length - 1]),
      }),
    [month.getTime()],
  )

  const byDay = useMemo(() => {
    const map = new Map<string, Event[]>()
    for (const event of events.data ?? []) {
      const key = dateInput(new Date(event.date))
      map.set(key, [...(map.get(key) ?? []), event])
    }
    return map
  }, [events.data])

  const todayKey = dateInput(new Date())

  function shift(step: number) {
    setMonth(new Date(month.getFullYear(), month.getMonth() + step, 1))
  }

  return (
    <div>
      <div className="head">
        <h1>Календарь</h1>
        <p>PR-встречи и плановые даты подтверждения скиллов вместе — видно, где срок раньше встречи.</p>
      </div>

      <div className="box">
        <div className="box-head">
          <div className="row">
            <button className="grey small" onClick={() => shift(-1)}>
              ←
            </button>
            <h2>
              {MONTHS[month.getMonth()]} {month.getFullYear()}
            </h2>
            <button className="grey small" onClick={() => shift(1)}>
              →
            </button>
          </div>
          <button
            className="grey small"
            onClick={() => {
              const now = new Date()
              setMonth(new Date(now.getFullYear(), now.getMonth(), 1))
            }}
          >
            Сегодня
          </button>
        </div>

        <ErrorBox text={events.error} />

        {events.loading ? (
          <Loading />
        ) : (
          <>
            <div className="cal">
              {WEEKDAYS.map((weekday) => (
                <div key={weekday} className="weekday">
                  {weekday}
                </div>
              ))}

              {days.map((day) => {
                const key = dateInput(day)
                const dayEvents = byDay.get(key) ?? []
                const otherMonth = day.getMonth() !== month.getMonth()
                return (
                  <div
                    key={key}
                    className={`day${otherMonth ? ' other' : ''}${key === todayKey ? ' today' : ''}`}
                  >
                    <div className="num">{day.getDate()}</div>
                    {dayEvents.slice(0, 3).map((event) => (
                      <button
                        key={event.kind + event.id}
                        className={`event ${event.kind === 'deadline' ? 'deadline' : event.done ? 'done' : ''}`}
                        title={`${event.employee_name} — ${event.title}`}
                        onClick={() =>
                          navigate(
                            event.kind === 'meeting'
                              ? `/meetings/${event.id}`
                              : `/employees/${event.employee_id}`,
                          )
                        }
                      >
                        {event.employee_name.split(' ')[0]}: {event.title}
                      </button>
                    ))}
                    {dayEvents.length > 3 ? (
                      <span className="small">ещё {dayEvents.length - 3}</span>
                    ) : null}
                  </div>
                )
              })}
            </div>

            <div className="legend">
              <span>
                <i style={{ background: '#4a5ce8' }} />
                встреча запланирована
              </span>
              <span>
                <i style={{ background: '#17805a' }} />
                встреча проведена
              </span>
              <span>
                <i style={{ background: '#a8680c' }} />
                срок подтверждения скилла
              </span>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
