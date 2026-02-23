import { createError } from 'h3'
import { fetchPlacafipeQuotas, resolvePlacafipeContext } from '@core/server/utils/placafipe'
import { buildMockQuotaInfo, isPlacafipeMockEnabled } from '@core/server/utils/placafipeMock'

const QUOTA_TIMEOUT_MS = 12000

export default defineEventHandler(async (event) => {
  const runtimeConfig = useRuntimeConfig(event)

  if (isPlacafipeMockEnabled(runtimeConfig)) {
    return {
      quota: buildMockQuotaInfo(),
    }
  }

  const context = resolvePlacafipeContext(runtimeConfig)

  try {
    const quota = await fetchPlacafipeQuotas(
      {
        ...context,
        timeout: QUOTA_TIMEOUT_MS,
      },
    )

    return {
      quota,
    }
  } catch (error) {
    throw createError({
      statusCode: 502,
      statusMessage:
        error instanceof Error ? error.message : 'Falha ao consultar quotas do provider placa FIPE.',
    })
  }
})
