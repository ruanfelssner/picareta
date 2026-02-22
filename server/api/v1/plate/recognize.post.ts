import { createError, readBody } from 'h3'
import { z } from 'zod'

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
  const base = String(runtimeConfig.flaskBaseUrl || 'http://127.0.0.1:5000').replace(/\/+$/, '')
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

    throw createError({
      statusCode: Number(fetchError.statusCode || fetchError.response?.status || 502),
      statusMessage:
        fetchError.statusMessage ||
        'Falha ao consultar servico OCR interno (Flask). Verifique NUXT_FLASK_BASE_URL e o processo Flask.',
      data: fetchError.data,
    })
  }
})
