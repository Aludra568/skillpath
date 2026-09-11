/** Общие мелочи: форматирование дат, модальное окно, markdown. */

import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import DOMPurify from 'dompurify'
import { marked } from 'marked'

/** Инициалы для кружка аватара. */
export function initials(name: string): string {
  return name
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toUpperCase())
    .join('')
}

export function Avatar({ name, big }: { name: string; big?: boolean }) {
  return <span className={big ? 'ava big' : 'ava'}>{initials(name)}</span>
}

/** Кликабельная плашка с человеком — ведёт в его карточку. */
export function Person({ id, name }: { id: number; name: string }) {
  return (
    <Link className="person" to={`/employees/${id}`}>
      <Avatar name={name} />
      <span>{name}</span>
    </Link>
  )
}

export function formatDate(value: string | null): string {
  if (!value) return '—'
  return new Date(value).toLocaleDateString('ru-RU')
}

export function formatDateTime(value: string | null): string {
  if (!value) return '—'
  const date = new Date(value)
  return (
    date.toLocaleDateString('ru-RU') +
    ', ' +
    date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })
  )
}

export function dateInput(value: string | Date): string {
  const date = typeof value === 'string' ? new Date(value) : value
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

export function dateTimeInput(value: string | Date): string {
  const date = typeof value === 'string' ? new Date(value) : value
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${dateInput(date)}T${pad(date.getHours())}:${pad(date.getMinutes())}`
}

export function ErrorBox({ text }: { text: string | null }) {
  if (!text) return null
  return <div className="error">{text}</div>
}

export function Loading() {
  return <p className="empty">Загрузка…</p>
}

export function Modal({
  title,
  onClose,
  children,
}: {
  title: string
  onClose: () => void
  children: ReactNode
}) {
  return (
    <div className="overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>{title}</h2>
        {children}
      </div>
    </div>
  )
}

export function Markdown({ text }: { text: string }) {
  const [html, setHtml] = useState('')
  useEffect(() => {
    const parsed = marked.parse(text || '_Протокол пока пустой._', { async: false })
    setHtml(DOMPurify.sanitize(parsed as string))
  }, [text])
  return <div className="md" dangerouslySetInnerHTML={{ __html: html }} />
}
