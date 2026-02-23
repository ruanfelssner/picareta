import { createError, readBody } from 'h3'
import { z } from 'zod'
import { normalizePlate } from '@core/shared/valuation'
import { isMongoConfigured } from '@core/server/utils/mongo'
import { recordOcrFeedbackEvent } from '@core/server/repositories/ocrFeedbackRepo'

const feedbackSchema = z.object({
  recognizedPlate: z.string().optional(),
  confirmedPlate: z.string().min(1, 'Informe a placa confirmada.'),
  candidates: z.array(z.string()).optional(),
  requestId: z.string().optional(),
  source: z.string().optional(),
  timingsMs: z.record(z.number()).optional(),
  plateCropBase64: z.string().max(2_000_000).optional(),
  bbox: z.tuple([z.number(), z.number(), z.number(), z.number()]).nullable().optional(),
  imageSize: z
    .object({
      width: z.number().int().positive(),
      height: z.number().int().positive(),
    })
    .optional(),
})

const sanitizeCandidates = (items?: string[]) => {
  if (!Array.isArray(items)) return []
  return Array.from(new Set(items.map((item) => normalizePlate(item || '')).filter(Boolean))).slice(0, 10)
}

const diffPositions = (from: string, to: string) => {
  if (!from || !to || from.length !== to.length) return []

  const changes: Array<{ index: number; from: string; to: string }> = []
  for (let index = 0; index < from.length; index += 1) {
    if (from[index] === to[index]) continue
    changes.push({
      index,
      from: from[index],
      to: to[index],
    })
  }
  return changes
}

const sanitizeBase64Crop = (value?: string) => {
  if (!value) return undefined
  const trimmed = value.trim()
  if (!trimmed) return undefined
  if (!trimmed.startsWith('data:image/')) return undefined
  return trimmed
}

const resolveUsefulReason = (
  recognizedPlate: string,
  confirmedPlate: string,
  candidates: string[],
): 'corrected' | 'ambiguous' | 'missing_recognition' | null => {
  if (!recognizedPlate) return 'missing_recognition'
  if (recognizedPlate !== confirmedPlate) return 'corrected'
  if (candidates.length > 1) return 'ambiguous'
  return null
}

export default defineEventHandler(async (event) => {
  if (!isMongoConfigured()) {
    throw createError({
      statusCode: 503,
      statusMessage: 'Mongo nao configurado para persistir feedback de OCR.',
    })
  }

  const body = await readBody(event)
  const parsed = feedbackSchema.safeParse(body)

  if (!parsed.success) {
    throw createError({
      statusCode: 400,
      statusMessage: 'Payload invalido para feedback de OCR.',
      data: parsed.error.flatten(),
    })
  }

  const confirmedPlate = normalizePlate(parsed.data.confirmedPlate || '')
  const recognizedPlate = normalizePlate(parsed.data.recognizedPlate || '')
  const candidates = sanitizeCandidates(parsed.data.candidates)

  if (!confirmedPlate) {
    throw createError({
      statusCode: 400,
      statusMessage: 'Informe uma placa confirmada valida.',
    })
  }

  const diff = diffPositions(recognizedPlate, confirmedPlate)
  const corrected = Boolean(recognizedPlate && recognizedPlate !== confirmedPlate)
  const usefulReason = resolveUsefulReason(recognizedPlate, confirmedPlate, candidates)

  if (!usefulReason) {
    return {
      ok: true,
      skipped: true,
      reason: 'not_useful_feedback',
    }
  }

  const saved = await recordOcrFeedbackEvent({
    source: parsed.data.source || 'manual-confirmation',
    requestId: parsed.data.requestId?.trim() || undefined,
    usefulReason,
    recognizedPlate: recognizedPlate || null,
    confirmedPlate,
    candidates,
    corrected,
    diffPositions: diff,
    timingsMs: parsed.data.timingsMs || {},
    plateCropBase64: sanitizeBase64Crop(parsed.data.plateCropBase64),
    bbox: parsed.data.bbox || null,
    imageSize: parsed.data.imageSize,
  })

  return {
    ok: true,
    savedAt: saved.createdAt,
    usefulReason,
  }
})
