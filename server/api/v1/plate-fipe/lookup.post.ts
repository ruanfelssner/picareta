import { createError, readBody } from 'h3'
import { z } from 'zod'
import type { PlateLookupResponse, PlateLookupResult } from '@core/shared/types/auction'
import { normalizePlate } from '@core/shared/valuation'
import { findPlateLookupCache, upsertPlateLookupCache } from '@core/server/repositories/plateLookupCacheRepo'
import { isMongoConfigured } from '@core/server/utils/mongo'
import {
  buildMockLookupResultByPlate,
  buildMockQuotaInfo,
  isPlacafipeMockEnabled,
} from '@core/server/utils/placafipeMock'
import {
  buildLookupResultFromPlacafipe,
  fetchPlacafipeByPlate,
  fetchPlacafipeByPlateFipe,
  fetchPlacafipeQuotas,
  hasMeaningfulLookupData,
  isPlacafipeSuccess,
  readPlacafipeMessage,
  resolvePlacafipeContext,
} from '@core/server/utils/placafipe'

const LOOKUP_TIMEOUT_MS = 12000

const requestSchema = z.object({
  plate: z.string().min(1, 'Informe a placa para consulta.'),
})

const buildMock = (plate: string): PlateLookupResult => ({
  plate: normalizePlate(plate || ''),
  brand: '',
  model: '',
  year: null,
  fipeValue: null,
  source: 'mock',
})

const toRecord = (value: unknown): Record<string, unknown> => {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return {}
  return value as Record<string, unknown>
}

const hasVehicleInfo = (payload: Record<string, unknown>) => {
  const info = toRecord(payload.informacoes_veiculo)
  return Object.keys(info).length > 0
}

const readErrorMessage = (error: unknown) => {
  if (error && typeof error === 'object') {
    const maybeData = (error as { data?: { statusMessage?: string; message?: string } }).data
    if (maybeData?.statusMessage) return maybeData.statusMessage
    if (maybeData?.message) return maybeData.message
  }

  if (error instanceof Error && error.message) return error.message

  return 'Falha na consulta externa.'
}

const dedupeMessages = (messages: string[]) => {
  return Array.from(new Set(messages.map((message) => message.trim()).filter(Boolean)))
}

const safeFetchQuota = async (context: { baseUrl: string; token: string }) => {
  try {
    return await fetchPlacafipeQuotas(
      {
        ...context,
        timeout: LOOKUP_TIMEOUT_MS,
      },
    )
  } catch {
    return undefined
  }
}

const readProviderWarning = (payload: Record<string, unknown>, endpointName: string) => {
  const message = readPlacafipeMessage(payload)
  if (!message) return ''
  if (isPlacafipeSuccess(payload)) return ''
  return `${endpointName}: ${message}`
}

const maybeReadFromCache = async (plate: string) => {
  if (!isMongoConfigured()) {
    return {
      record: null,
      warning: '',
    }
  }

  try {
    const record = await findPlateLookupCache(plate)
    return {
      record,
      warning: '',
    }
  } catch (error) {
    return {
      record: null,
      warning: `Cache Mongo indisponivel: ${readErrorMessage(error)}`,
    }
  }
}

const maybePersistCache = async (plate: string, result: PlateLookupResult) => {
  if (!isMongoConfigured()) return ''

  try {
    await upsertPlateLookupCache(plate, result)
    return ''
  } catch (error) {
    return `Falha ao salvar cache no Mongo: ${readErrorMessage(error)}`
  }
}

export default defineEventHandler(async (event): Promise<PlateLookupResponse> => {
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

  if (isPlacafipeMockEnabled(runtimeConfig)) {
    return {
      result: buildMockLookupResultByPlate(plate),
      warning: 'Modo mock ativo para placa/FIPE. Nenhuma consulta externa foi consumida.',
      cache: {
        hit: false,
      },
      quota: buildMockQuotaInfo(),
    }
  }

  let context: { baseUrl: string; token: string }
  try {
    context = resolvePlacafipeContext(runtimeConfig)
  } catch {
    return {
      result: buildMock(plate),
      warning: 'Provider nao configurado. Defina NUXT_PLACA_FIPE_BASE_URL e NUXT_PLACA_FIPE_TOKEN.',
      cache: {
        hit: false,
      },
    }
  }

  const cacheAttempt = await maybeReadFromCache(plate)
  if (cacheAttempt.record) {
    const quota = await safeFetchQuota(context)

    return {
      result: {
        ...cacheAttempt.record.result,
        source: 'cache',
      },
      ...(cacheAttempt.warning ? { warning: cacheAttempt.warning } : {}),
      cache: {
        hit: true,
        storedAt: cacheAttempt.record.updatedAt,
      },
      ...(quota ? { quota } : {}),
    }
  }

  const detailMessages: string[] = []
  if (cacheAttempt.warning) {
    detailMessages.push(cacheAttempt.warning)
  }

  let fipePayload: Record<string, unknown> = {}
  try {
    fipePayload = await fetchPlacafipeByPlateFipe(
      {
        ...context,
        timeout: LOOKUP_TIMEOUT_MS,
      },
      plate,
    )
  } catch (error) {
    detailMessages.push(`getplacafipe: ${readErrorMessage(error)}`)
  }

  const providerWarning = readProviderWarning(fipePayload, 'getplacafipe')
  if (providerWarning) {
    detailMessages.push(providerWarning)
  }

  const needGetPlacaCall =
    !Object.keys(fipePayload).length || !isPlacafipeSuccess(fipePayload) || !hasVehicleInfo(fipePayload)

  let placaPayload: Record<string, unknown> | null = null
  if (needGetPlacaCall) {
    try {
      placaPayload = await fetchPlacafipeByPlate(
        {
          ...context,
          timeout: LOOKUP_TIMEOUT_MS,
        },
        plate,
      )
    } catch (error) {
      detailMessages.push(`getplaca: ${readErrorMessage(error)}`)
    }

    const placaWarning = readProviderWarning(placaPayload || {}, 'getplaca')
    if (placaWarning) {
      detailMessages.push(placaWarning)
    }
  }

  const hasProviderPayload = Boolean(Object.keys(fipePayload).length || Object.keys(placaPayload || {}).length)

  if (!hasProviderPayload) {
    const quota = await safeFetchQuota(context)

    return {
      result: buildMock(plate),
      warning: 'Consulta externa indisponivel no momento. Resultado local de contingencia.',
      detail: dedupeMessages(detailMessages).join(' | ') || undefined,
      cache: {
        hit: false,
      },
      ...(quota ? { quota } : {}),
    }
  }

  const result = buildLookupResultFromPlacafipe({
    requestedPlate: plate,
    fipePayload,
    placaPayload,
  })

  const warnings: string[] = []
  if (result.fipeValue == null) {
    warnings.push('Placa encontrada, mas valor FIPE indisponivel no momento.')
  }

  if (!hasMeaningfulLookupData(result)) {
    warnings.push('Consulta retornou sem dados aproveitaveis para o veiculo.')
  }

  if (hasMeaningfulLookupData(result)) {
    const cachePersistWarning = await maybePersistCache(plate, result)
    if (cachePersistWarning) {
      detailMessages.push(cachePersistWarning)
    }
  }

  const quota = await safeFetchQuota(context)

  return {
    result: hasMeaningfulLookupData(result) ? result : buildMock(plate),
    ...(warnings.length > 0 ? { warning: dedupeMessages(warnings).join(' ') } : {}),
    ...(detailMessages.length > 0 ? { detail: dedupeMessages(detailMessages).join(' | ') } : {}),
    cache: {
      hit: false,
    },
    ...(quota ? { quota } : {}),
  }
})
