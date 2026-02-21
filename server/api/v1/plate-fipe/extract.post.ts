import { createError, readBody } from 'h3'
import { z } from 'zod'
import { normalizePlate } from '@core/shared/valuation'
import { detectPlateFromImageSmart } from '@core/server/utils/plate-ocr-provider'

const requestSchema = z.object({
  imageBase64: z.string().min(1),
})

const HIGH_SCORE = 1.8
const MIN_MARGIN = 0.6

export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const parsed = requestSchema.safeParse(body)

  if (!parsed.success) {
    throw createError({
      statusCode: 400,
      statusMessage: 'Payload invalido para extracao de placa.',
      data: parsed.error.flatten(),
    })
  }

  let ocr
  try {
    ocr = await detectPlateFromImageSmart(parsed.data.imageBase64)
  } catch (error) {
    throw createError({
      statusCode: 503,
      statusMessage: 'OCR Python indisponivel no momento.',
      data: {
        detail: error instanceof Error ? error.message : String(error),
      },
    })
  }
  const bestScore = Number(ocr.bestScore) || 0
  const secondScore = Number(ocr.secondScore) || 0
  const margin = bestScore - secondScore

  const highConfidence = bestScore >= HIGH_SCORE && margin >= MIN_MARGIN

  return {
    result: {
      plate: highConfidence ? normalizePlate(ocr.plate) : '',
      candidates: ocr.candidates,
      bestScore,
      secondScore,
      margin,
      highConfidence,
      rawText: ocr.rawText,
      engine: ocr.engine,
    },
    warning: highConfidence
      ? undefined
      : 'OCR com baixa confianca. Selecione um candidato ou digite a placa manualmente.',
  }
})
