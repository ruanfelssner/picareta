import { createError, readBody, setResponseHeaders, sendStream } from 'h3'
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
      statusMessage: 'Payload invalido para OCR stream.',
      data: parsed.error.flatten(),
    })
  }

  const runtimeConfig = useRuntimeConfig(event)
  const base = resolveFlaskBaseUrl(event, runtimeConfig)

  let flaskRes: Response
  try {
    flaskRes = await fetch(`${base}/api/v1/plate/recognize-stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(parsed.data),
      // @ts-ignore - node 18+ AbortSignal.timeout
      signal: AbortSignal.timeout(55_000),
    })
  }
  catch (error) {
    throw createError({
      statusCode: 502,
      statusMessage: `Falha ao conectar ao Flask SSE em ${base}.`,
      data: { cause: error instanceof Error ? error.message : String(error) },
    })
  }

  if (!flaskRes.body) {
    throw createError({ statusCode: 502, statusMessage: 'Flask retornou stream vazio.' })
  }

  setResponseHeaders(event, {
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive',
    'X-Accel-Buffering': 'no',
  })

  return sendStream(event, flaskRes.body)
})
