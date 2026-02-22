import { resolveFlaskBaseUrl } from '@core/server/utils/flask'

export default defineEventHandler(async (event) => {
  const runtimeConfig = useRuntimeConfig(event)
  const base = resolveFlaskBaseUrl(event, runtimeConfig)
  const timeout = Math.min(Number(runtimeConfig.flaskTimeoutMs) || 120000, 5000)

  try {
    const upstream = await $fetch<Record<string, unknown>>(`${base}/`, {
      method: 'GET',
      timeout,
    })

    return {
      ok: true,
      targetBaseUrl: base,
      timeoutMs: timeout,
      upstream,
    }
  } catch (error: unknown) {
    const cause = error instanceof Error ? error.message : String(error)
    const fetchError = error as {
      statusCode?: number
      statusMessage?: string
      data?: unknown
      response?: { status?: number }
    }

    return {
      ok: false,
      targetBaseUrl: base,
      timeoutMs: timeout,
      statusCode: Number(fetchError.statusCode || fetchError.response?.status || 502),
      statusMessage: fetchError.statusMessage || 'Falha no ping do Flask interno.',
      cause,
      data: fetchError.data,
    }
  }
})
