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

const getFirstDefined = (obj: Record<string, unknown>, keys: string[]) => {
  for (const key of keys) {
    if (obj[key] != null) return obj[key]
  }
  return undefined
}

const unwrapProviderPayload = (response: Record<string, unknown>) => {
  const candidates = [
    response.response,
    response.result,
    response.resultado,
    response.data,
    response.vehicle,
    response.veiculo,
    response,
  ]

  for (const candidate of candidates) {
    if (candidate && typeof candidate === 'object' && !Array.isArray(candidate)) {
      return candidate as Record<string, unknown>
    }
  }

  return response
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
    accept: '*/*',
    'user-agent': String(
      runtimeConfig.placaFipeUserAgent || 'Thunder Client (https://www.thunderclient.com)',
    ),
  }

  if (runtimeConfig.placaFipeToken) {
    headers.authorization = `Bearer ${runtimeConfig.placaFipeToken}`
  }
  if (runtimeConfig.placaFipeDeviceToken) {
    headers.DeviceToken = String(runtimeConfig.placaFipeDeviceToken)
  }

  const plateField = String(runtimeConfig.placaFipeRequestPlateField || 'placa').trim() || 'placa'
  const requestBody: Record<string, unknown> = {
    [plateField]: payload.plate,
  }
  if (plateField !== 'placa') requestBody.placa = payload.plate
  if (plateField !== 'plate') requestBody.plate = payload.plate

  const method = String(runtimeConfig.placaFipeLookupMethod || 'POST').toUpperCase() === 'GET' ? 'GET' : 'POST'

  const response = await $fetch<Record<string, unknown>>(apiUrl.toString(), {
    method,
    headers,
    ...(method === 'POST' ? { body: requestBody } : { query: requestBody }),
    timeout: Number(runtimeConfig.placaFipeTimeoutMs) || 12000,
  })

  const data = unwrapProviderPayload(response)

  return {
    plate: normalizePlate(String(getFirstDefined(data, ['plate', 'placa']) || payload.plate || '')),
    brand: String(getFirstDefined(data, ['brand', 'marca', 'Marca']) || ''),
    model: String(getFirstDefined(data, ['model', 'modelo', 'Modelo']) || ''),
    year: toNumberOrNull(getFirstDefined(data, ['year', 'anoModelo', 'ano', 'Ano'])),
    fipeValue: toNumberOrNull(getFirstDefined(data, ['fipeValue', 'valorFipe', 'valor_fipe', 'fipe'])),
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
  const lookupStrategyRaw = String(runtimeConfig.placaFipeLookupStrategy || 'scrape-first').toLowerCase()
  const lookupStrategy =
    lookupStrategyRaw === 'provider-first' ||
    lookupStrategyRaw === 'scrape-only' ||
    lookupStrategyRaw === 'provider-only'
      ? lookupStrategyRaw
      : 'scrape-first'

  if (!plate) {
    throw createError({
      statusCode: 400,
      statusMessage: 'Informe uma placa valida para consulta.',
    })
  }

  const hasExternalProvider = Boolean(runtimeConfig.placaFipeBaseUrl)
  let providerFailureMessage = ''
  let scrapingFailureMessage = ''

  const attemptOrder: Array<'scrape' | 'provider'> =
    lookupStrategy === 'provider-first'
      ? ['provider', 'scrape']
      : lookupStrategy === 'provider-only'
        ? ['provider']
        : lookupStrategy === 'scrape-only'
          ? ['scrape']
          : ['scrape', 'provider']

  for (const mode of attemptOrder) {
    if (mode === 'provider') {
      if (!hasExternalProvider) continue
      try {
        const providerResult = await lookupOnExternalProvider(runtimeConfig, { plate })
        if (providerResult) {
          return {
            result: providerResult,
          }
        }
      } catch (error) {
        providerFailureMessage = error instanceof Error ? error.message : String(error)
      }
      continue
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
      scrapingFailureMessage = error instanceof Error ? error.message : String(error)
    }
  }

  const detail = [scrapingFailureMessage, providerFailureMessage].filter(Boolean).join(' | ')
  const warning =
    lookupStrategy === 'provider-only'
      ? hasExternalProvider
        ? 'Consulta via provider indisponivel no momento. Resultado local de contingencia.'
        : 'Provider nao configurado. Defina NUXT_PLACA_FIPE_BASE_URL e NUXT_PLACA_FIPE_TOKEN.'
      : lookupStrategy === 'scrape-only' || (!hasExternalProvider && lookupStrategy === 'scrape-first')
        ? 'Scraping indisponivel no momento (site pode bloquear a requisicao). Resultado local de contingencia.'
        : 'Consulta externa indisponivel no momento. Resultado local de contingencia.'

  return {
    result: buildMock(plate),
    warning,
    detail: detail || undefined,
    debug: {
      lookupStrategy,
      providerFailureMessage: providerFailureMessage || undefined,
      scrapingFailureMessage: scrapingFailureMessage || undefined,
    },
  }
})
