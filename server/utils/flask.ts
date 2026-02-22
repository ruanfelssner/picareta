import type { H3Event } from 'h3'

type RuntimeConfigLike = {
  flaskBaseUrl?: string
}

export const resolveFlaskBaseUrl = (
  event: H3Event,
  runtimeConfig: RuntimeConfigLike,
) => {
  const configuredBase = String(runtimeConfig.flaskBaseUrl || 'http://127.0.0.1:5000').trim()
  const requestHost = String(event.node.req.headers.host || '').toLowerCase()
  let base = configuredBase

  try {
    const parsedConfiguredBase = new URL(configuredBase)
    if (requestHost && parsedConfiguredBase.host.toLowerCase() === requestHost) {
      const flaskPort = Number(process.env.FLASK_PORT || 5000)
      base = `http://127.0.0.1:${Number.isFinite(flaskPort) ? flaskPort : 5000}`
    }
  } catch {
    // usa valor configurado quando URL e invalida
  }

  return base.replace(/\/+$/, '')
}
