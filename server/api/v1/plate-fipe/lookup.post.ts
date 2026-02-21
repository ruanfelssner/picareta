import { createError, readBody } from 'h3'
import { z } from 'zod'
import type { PlateLookupResult } from '@core/shared/types/auction'
import { normalizePlate } from '@core/shared/valuation'

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

const pickString = (source: Record<string, unknown>, keys: string[]) => {
  for (const key of keys) {
    const value = source[key]
    if (typeof value === 'string' && value.trim()) {
      return value.trim()
    }
  }
  return ''
}

const pickNumber = (source: Record<string, unknown>, keys: string[]) => {
  for (const key of keys) {
    const value = source[key]
    if (typeof value === 'number' && Number.isFinite(value)) {
      return value
    }
    if (typeof value === 'string') {
      const normalized = value.replace(/\./g, '').replace(',', '.').replace(/[^0-9.-]/g, '')
      const parsed = Number(normalized)
      if (Number.isFinite(parsed)) {
        return parsed
      }
    }
  }
  return null
}

const buildMock = (plate: string): PlateLookupResult => {
  const normalizedPlate = normalizePlate(plate || 'SEM0000')
  const seed = normalizedPlate.split('').reduce((acc, current) => acc + current.charCodeAt(0), 0)
  const brands = ['Chevrolet', 'Volkswagen', 'Fiat', 'Toyota', 'Hyundai']
  const models = ['Onix', 'Gol', 'Mobi', 'Corolla', 'HB20']

  return {
    plate: normalizedPlate,
    brand: brands[seed % brands.length] || '',
    model: models[seed % models.length] || '',
    year: 2016 + (seed % 9),
    fipeValue: 28000 + (seed % 180) * 420,
    source: 'mock',
  }
}

const normalizeResult = (raw: Record<string, unknown>, fallbackPlate: string): PlateLookupResult => {
  const plate = normalizePlate(pickString(raw, ['plate', 'placa']) || fallbackPlate)
  const year = pickNumber(raw, ['year', 'ano'])
  const fipeValue = pickNumber(raw, ['fipeValue', 'valorFipe', 'fipe', 'precoFipe'])

  return {
    plate,
    brand: pickString(raw, ['brand', 'marca']),
    model: pickString(raw, ['model', 'modelo']),
    year,
    fipeValue,
    source: 'placa-fipe',
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

  const requestData = parsed.data
  const fallbackPlate = normalizePlate(requestData.plate || '')
  const config = useRuntimeConfig(event)

  if (!config.placaFipeBaseUrl) {
    return {
      result: buildMock(fallbackPlate),
    }
  }

  try {
    const url = new URL(String(config.placaFipeLookupPath || '/lookup'), String(config.placaFipeBaseUrl))
    const headers: Record<string, string> = {
      'content-type': 'application/json',
    }

    if (config.placaFipeToken) {
      headers.authorization = `Bearer ${config.placaFipeToken}`
    }

    const response = await $fetch<Record<string, unknown>>(url.toString(), {
      method: 'POST',
      headers,
      body: {
        plate: fallbackPlate || undefined,
        imageBase64: requestData.imageBase64 || undefined,
      },
      timeout: Number(config.placaFipeTimeoutMs) || 8000,
    })

    return {
      result: normalizeResult(response, fallbackPlate),
    }
  } catch (error) {
    throw createError({
      statusCode: 502,
      statusMessage: 'Falha ao consultar provedor Placa/FIPE.',
      data: {
        cause: error instanceof Error ? error.message : String(error),
      },
    })
  }
})
