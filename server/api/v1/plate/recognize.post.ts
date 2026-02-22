import { createError, readBody } from 'h3'
import { z } from 'zod'
import { resolveFlaskBaseUrl } from '@core/server/utils/flask'

const requestSchema = z.object({
  imageBase64: z.string().min(1, 'Informe a imagem em base64.'),
  filename: z.string().optional(),
  requestId: z.string().optional(),
})

export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const parsed = requestSchema.safeParse(body)

  if (!parsed.success) {
    throw createError({
      statusCode: 400,
      statusMessage: 'Payload invalido para OCR de placa.',
      data: parsed.error.flatten(),
    })
  }

  const runtimeConfig = useRuntimeConfig(event)
  const base = resolveFlaskBaseUrl(event, runtimeConfig)
  const timeout = Number(runtimeConfig.flaskTimeoutMs) || 120000

  try {
    return await $fetch(`${base}/api/v1/plate/recognize`, {
      method: 'POST',
      body: parsed.data,
      timeout,
    })
  } catch (error: unknown) {
    const fetchError = error as {
      statusCode?: number
      statusMessage?: string
      data?: unknown
      response?: { status?: number }
    }
    const causeMessage = error instanceof Error ? error.message : String(error)

    throw createError({
      statusCode: Number(fetchError.statusCode || fetchError.response?.status || 502),
      statusMessage:
        fetchError.statusMessage ||
        `Falha ao consultar servico OCR interno (Flask) em ${base}. Verifique NUXT_FLASK_BASE_URL e o processo Flask.`,
      data:
        fetchError.data && typeof fetchError.data === 'object'
          ? { ...(fetchError.data as Record<string, unknown>), targetBaseUrl: base, cause: causeMessage }
          : { targetBaseUrl: base, cause: causeMessage },
    })
  }
})
