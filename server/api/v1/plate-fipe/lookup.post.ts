import { createError, readBody } from 'h3'
import { z } from 'zod'
import type { PlateLookupResult } from '@core/shared/types/auction'
import { normalizePlate } from '@core/shared/valuation'
import { fetchPlacafipeByPlate } from '@core/server/utils/placafipe'

const requestSchema = z.object({
  plate: z.string().min(1, 'Informe a placa para consulta.'),
})

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
  payload: { plate: string },
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
      plate: payload.plate,
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

  const runtimeConfig = useRuntimeConfig(event)
  const plate = normalizePlate(parsed.data.plate || '')

  if (!plate) {
    throw createError({
      statusCode: 400,
      statusMessage: 'Informe uma placa valida para consulta.',
    })
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
    }
  }
})
