import { createError, readBody } from 'h3'
import { z } from 'zod'
import type { PlateLookupResult } from '@core/shared/types/auction'
import { normalizePlate } from '@core/shared/valuation'
import { fetchPlacafipeByPlate } from '@core/server/utils/placafipe'
import { detectPlateFromImageSmart } from '@core/server/utils/plate-ocr-provider'

const requestSchema = z
  .object({
    plate: z.string().optional(),
    imageBase64: z.string().optional(),
  })
  .superRefine((value, context) => {
    if (!value.plate && !value.imageBase64) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        message: 'Informe placa ou imagem para consulta.',
      })
    }
  })

const OCR_MIN_CONFIDENCE = 2.2
const OCR_MIN_MARGIN_TO_SECOND = 0.9

const buildMock = (plate: string): PlateLookupResult => {
  const normalizedPlate = normalizePlate(plate || '')

  return {
    plate: normalizedPlate,
    brand: '',
    model: '',
    year: null,
    fipeValue: null,
    source: 'mock',
  }
}

const toNumberOrNull = (value: unknown) => {
  if (typeof value === 'number' && Number.isFinite(value)) return value
  if (typeof value === 'string') {
    const parsed = Number(value.replace(/\./g, '').replace(',', '.').replace(/[^0-9.-]/g, ''))
    if (Number.isFinite(parsed)) return parsed
  }
  return null
}

const lookupOnExternalProvider = async (
  runtimeConfig: ReturnType<typeof useRuntimeConfig>,
  payload: { plate?: string; imageBase64?: string },
) => {
  if (!runtimeConfig.placaFipeBaseUrl) {
    return null
  }

  const apiUrl = new URL(
    String(runtimeConfig.placaFipeLookupPath || '/lookup'),
    String(runtimeConfig.placaFipeBaseUrl),
  )

  const headers: Record<string, string> = {
    'content-type': 'application/json',
  }

  if (runtimeConfig.placaFipeToken) {
    headers.authorization = `Bearer ${runtimeConfig.placaFipeToken}`
  }

  const response = await $fetch<Record<string, unknown>>(apiUrl.toString(), {
    method: 'POST',
    headers,
    body: {
      plate: payload.plate || undefined,
      imageBase64: payload.imageBase64 || undefined,
    },
    timeout: Number(runtimeConfig.placaFipeTimeoutMs) || 12000,
  })

  return {
    plate: normalizePlate(String(response.plate || response.placa || payload.plate || '')),
    brand: String(response.brand || response.marca || ''),
    model: String(response.model || response.modelo || ''),
    year: toNumberOrNull(response.year),
    fipeValue: toNumberOrNull(response.fipeValue),
    source: 'placa-fipe' as const,
  }
}

export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const parsed = requestSchema.safeParse(body)

  if (!parsed.success) {
    throw createError({
      statusCode: 400,
      statusMessage: 'Payload invalido para consulta de placa/FIPE.',
      data: parsed.error.flatten(),
    })
  }

  const input = parsed.data
  const runtimeConfig = useRuntimeConfig(event)
  let plate = normalizePlate(input.plate || '')
  let ocrCandidates: string[] = []
  let ocrRawText = ''
  let ocrBestScore = 0
  let ocrSecondScore = 0

  if (!plate && input.imageBase64) {
    try {
      const ocrResult = await detectPlateFromImageSmart(input.imageBase64)
      ocrBestScore = Number(ocrResult.bestScore) || 0
      ocrSecondScore = Number(ocrResult.secondScore) || 0
      const ocrMargin = ocrBestScore - ocrSecondScore
      if (ocrBestScore >= OCR_MIN_CONFIDENCE && ocrMargin >= OCR_MIN_MARGIN_TO_SECOND) {
        plate = normalizePlate(ocrResult.plate)
      }
      ocrCandidates = ocrResult.candidates
      ocrRawText = ocrResult.rawText
    } catch (error) {
      ocrRawText = `[ocr-python-error] ${error instanceof Error ? error.message : String(error)}`
    }
  }

  if (!plate) {
    let providerFailureMessage = ''
    try {
      const providerResult = await lookupOnExternalProvider(runtimeConfig, {
        imageBase64: input.imageBase64,
      })

      if (providerResult) {
        return {
          result: providerResult,
        }
      }
    } catch (error) {
      providerFailureMessage = error instanceof Error ? error.message : String(error)
    }

    return {
      result: buildMock(''),
      warning:
        'Nao foi possivel identificar a placa automaticamente. Informe a placa manualmente.' +
        (providerFailureMessage ? ` Provedor externo: ${providerFailureMessage}` : ''),
      data: {
        candidates: ocrCandidates,
        bestScore: ocrBestScore,
        secondScore: ocrSecondScore,
        rawText: ocrRawText,
      },
    }
  }

  try {
    const scraped = await fetchPlacafipeByPlate(plate, Number(runtimeConfig.placaFipeTimeoutMs) || 12000)

    return {
      result: {
        plate: scraped.plate,
        brand: scraped.brand,
        model: scraped.model,
        year: scraped.year,
        fipeValue: scraped.fipeValue,
        details: scraped.details,
        source: 'placafipe-site' as const,
      },
    }
  } catch (error) {
    const scrapingFailureMessage = error instanceof Error ? error.message : String(error)
    try {
      const providerResult = await lookupOnExternalProvider(runtimeConfig, {
        plate,
        imageBase64: input.imageBase64,
      })

      if (providerResult) {
        return {
          result: providerResult,
        }
      }
    } catch {
      // keep fallback below
    }

    return {
      result: buildMock(plate),
      warning:
        'Consulta externa indisponivel no momento. Resultado local de contingencia.' +
        (scrapingFailureMessage ? ` Detalhe: ${scrapingFailureMessage}` : ''),
      data: {
        candidates: ocrCandidates,
        bestScore: ocrBestScore,
        secondScore: ocrSecondScore,
        rawText: ocrRawText,
      },
    }
  }
})
