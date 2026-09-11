import { useCallback, useEffect, useState } from 'react'

/** Загрузка данных с состояниями ошибки/загрузки и ручным обновлением. */
export function useAsync<T>(
  loader: () => Promise<T>,
  deps: unknown[],
): { data: T | null; error: string | null; loading: boolean; reload: () => void } {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [tick, setTick] = useState(0)

  // Загрузчик пересоздаётся на каждый рендер, поэтому зависимости задаёт вызывающий код.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const run = useCallback(loader, deps)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    run()
      .then((result) => {
        if (!cancelled) {
          setData(result)
          setError(null)
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Ошибка загрузки')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [run, tick])

  return { data, error, loading, reload: () => setTick((value) => value + 1) }
}
