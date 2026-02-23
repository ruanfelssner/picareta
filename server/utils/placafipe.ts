import { createError } from 'h3'
import { normalizePlate } from '@core/shared/valuation'
import type {
  PlateFipeDetails,
  PlateFipeMatch,
  PlateFipeQuotaInfo,
  PlateLookupResult,
} from '@core/shared/types/auction'

type PlacafipePayload = Record<string, unknown>

type RequestContext = {
  baseUrl: string
  token: string
  timeout?: number
}

const DEFAULT_TIMEOUT_MS = 12000

const toRecord = (value: unknown): PlacafipePayload => {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return {}
  return value as PlacafipePayload
}

const toStringSafe = (value: unknown) => (value == null ? '' : String(value).trim())

const toNumberOrNull = (value: unknown) => {
  if (typeof value === 'number' && Number.isFinite(value)) return value
  if (typeof value !== 'string') return null

  const sanitized = value.replace(/[^0-9,.-]/g, '').trim()
  if (!sanitized) return null

  const lastComma = sanitized.lastIndexOf(',')
  const lastDot = sanitized.lastIndexOf('.')

  let normalized = sanitized
  if (lastComma >= 0 && lastDot >= 0) {
    normalized =
      lastComma > lastDot
        ? sanitized.replace(/\./g, '').replace(',', '.')
        : sanitized.replace(/,/g, '')
  } else if (lastComma >= 0) {
    normalized = sanitized.replace(',', '.')
  }

  const parsed = Number(normalized)
  return Number.isFinite(parsed) ? parsed : null
}

const toBooleanOrNull = (value: unknown) => {
  if (typeof value === 'boolean') return value
  if (typeof value === 'string') {
    const normalized = value.trim().toLowerCase()
    if (normalized === 'true' || normalized === '1') return true
    if (normalized === 'false' || normalized === '0') return false
  }
  return null
}

const getFirstDefined = (obj: PlacafipePayload, keys: string[]) => {
  for (const key of keys) {
    if (obj[key] != null) return obj[key]
  }
  return undefined
}

const normalizeBaseUrl = (value: string) => {
  const trimmed = String(value || '').trim()
  if (!trimmed) {
    throw createError({
      statusCode: 500,
      statusMessage: 'Provider nao configurado. Defina NUXT_PLACA_FIPE_BASE_URL.',
    })
  }

  return trimmed.endsWith('/') ? trimmed : `${trimmed}/`
}

const readHttpStatus = (error: unknown) => {
  if (!error || typeof error !== 'object') return 0
  const candidate = error as {
    status?: number
    statusCode?: number
    response?: {
      status?: number
    }
    data?: {
      status?: number
      statusCode?: number
    }
  }

  const status =
    Number(candidate.statusCode) ||
    Number(candidate.status) ||
    Number(candidate.response?.status) ||
    Number(candidate.data?.statusCode) ||
    Number(candidate.data?.status)

  return Number.isFinite(status) ? status : 0
}

export const readPlacafipeMessage = (payload: unknown) => {
  const data = toRecord(payload)
  const messageCandidate = getFirstDefined(data, ['msg', 'message', 'mensagem', 'erro'])
  return toStringSafe(messageCandidate)
}

const readPlacafipeCode = (payload: unknown) => {
  const data = toRecord(payload)
  const codeValue = getFirstDefined(data, ['codigo', 'code', 'statusCode'])
  const parsed = toNumberOrNull(codeValue)
  return parsed != null ? parsed : null
}

export const isPlacafipeSuccess = (payload: unknown) => {
  const code = readPlacafipeCode(payload)
  return code === 1
}

const formatMoneyBr = (value: number | null, currencyPrefix: string) => {
  if (value == null) return ''
  const formatter = new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
    maximumFractionDigits: 2,
  })

  if (!currencyPrefix || currencyPrefix === 'R$') {
    return formatter.format(value)
  }

  return `${currencyPrefix} ${value.toFixed(2)}`
}

async function postPlacafipe(
  context: RequestContext,
  endpointPath: string,
  body: PlacafipePayload,
): Promise<PlacafipePayload> {
  const baseUrl = normalizeBaseUrl(context.baseUrl)
  const timeout = Number(context.timeout || DEFAULT_TIMEOUT_MS)
  const url = new URL(endpointPath.replace(/^\/+/, ''), baseUrl)

  try {
    const response = await $fetch<PlacafipePayload>(url.toString(), {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
      },
      body,
      timeout,
    })

    return toRecord(response)
  } catch (error: unknown) {
    const statusCode = readHttpStatus(error)
    const maybeData =
      error && typeof error === 'object'
        ? toRecord((error as { data?: unknown }).data)
        : {}
    const providerMessage = readPlacafipeMessage(maybeData)

    throw createError({
      statusCode: 502,
      statusMessage:
        providerMessage ||
        (statusCode === 401
          ? 'Token da API placa FIPE invalido ou expirado.'
          : `Falha na chamada da API placa FIPE (${endpointPath}).`),
      data: {
        providerStatus: statusCode || undefined,
        providerEndpoint: endpointPath,
      },
    })
  }
}

export async function fetchPlacafipeByPlateFipe(context: RequestContext, plate: string) {
  return postPlacafipe(context, '/getplacafipe', {
    placa: plate,
    token: context.token,
  })
}

export async function fetchPlacafipeByPlate(context: RequestContext, plate: string) {
  return postPlacafipe(context, '/getplaca', {
    placa: plate,
    token: context.token,
  })
}

export async function fetchPlacafipeQuotas(context: RequestContext) {
  const raw = await postPlacafipe(context, '/getquotas', {
    token: context.token,
  })

  const dailyLimit = toNumberOrNull(raw.limite_diario)
  const usedToday = toNumberOrNull(raw.uso_diario)
  const remainingToday =
    dailyLimit != null && usedToday != null ? Math.max(0, dailyLimit - usedToday) : null

  return {
    codigo: readPlacafipeCode(raw),
    mensagem: readPlacafipeMessage(raw),
    dailyLimit,
    usedToday,
    remainingToday,
    hasChassiAccess: toBooleanOrNull(raw.chassi),
    raw,
  } satisfies PlateFipeQuotaInfo
}

const mapDetails = (rawInfo: unknown): PlateFipeDetails | undefined => {
  const data = toRecord(rawInfo)

  const details: PlateFipeDetails = {
    marca: toStringSafe(getFirstDefined(data, ['marca', 'brand'])),
    modelo: toStringSafe(getFirstDefined(data, ['modelo', 'model'])),
    importado: toStringSafe(getFirstDefined(data, ['importado'])),
    ano: toNumberOrNull(getFirstDefined(data, ['ano', 'fabricacao_ano'])),
    anoModelo: toNumberOrNull(getFirstDefined(data, ['ano_modelo', 'anoModelo'])),
    cor: toStringSafe(getFirstDefined(data, ['cor', 'color'])),
    cilindrada: toStringSafe(getFirstDefined(data, ['cilindradas', 'cilindrada'])),
    potencia: toStringSafe(getFirstDefined(data, ['potencia'])),
    combustivel: toStringSafe(getFirstDefined(data, ['combustivel', 'fuel'])),
    chassi: toStringSafe(getFirstDefined(data, ['chassi', 'chassis'])),
    motor: toStringSafe(getFirstDefined(data, ['motor'])),
    passageiros: toNumberOrNull(getFirstDefined(data, ['passageiros'])),
    uf: toStringSafe(getFirstDefined(data, ['uf', 'state'])),
    municipio: toStringSafe(getFirstDefined(data, ['municipio', 'city'])),
    segmento: toStringSafe(getFirstDefined(data, ['segmento'])),
    subSegmento: toStringSafe(getFirstDefined(data, ['sub_segmento', 'subSegmento'])),
    placaAlternativa: toStringSafe(getFirstDefined(data, ['placa_alternativa', 'placaAlternativa'])),
    raw: data,
  }

  const hasAnyValue =
    details.marca ||
    details.modelo ||
    details.ano != null ||
    details.anoModelo != null ||
    details.cor ||
    details.chassi ||
    details.uf ||
    details.municipio ||
    details.combustivel

  return hasAnyValue ? details : undefined
}

const mapFipeMatch = (rawEntry: unknown): PlateFipeMatch | null => {
  const entry = toRecord(rawEntry)
  if (!Object.keys(entry).length) return null

  const valor = toNumberOrNull(getFirstDefined(entry, ['valor', 'preco', 'price']))
  const unidadeValor = toStringSafe(getFirstDefined(entry, ['unidade_valor', 'unidadeValor']))

  return {
    marca: toStringSafe(getFirstDefined(entry, ['marca', 'brand'])),
    modelo: toStringSafe(getFirstDefined(entry, ['modelo', 'model'])),
    anoModelo: toNumberOrNull(getFirstDefined(entry, ['ano_modelo', 'anoModelo'])),
    codigoFipe: toStringSafe(getFirstDefined(entry, ['codigo_fipe', 'codigoFipe'])),
    codigoMarca: toStringSafe(getFirstDefined(entry, ['codigo_marca', 'codigoMarca'])),
    codigoModelo: toStringSafe(getFirstDefined(entry, ['codigo_modelo', 'codigoModelo'])),
    mesReferencia: toStringSafe(getFirstDefined(entry, ['mes_referencia', 'mesReferencia'])),
    combustivel: toStringSafe(getFirstDefined(entry, ['combustivel', 'fuel'])),
    valor,
    valorFormatado: formatMoneyBr(valor, unidadeValor),
    similaridade: toNumberOrNull(getFirstDefined(entry, ['similaridade'])),
    correspondencia: toNumberOrNull(getFirstDefined(entry, ['correspondencia'])),
    raw: entry,
  }
}

const sortMatches = (matches: PlateFipeMatch[]) => {
  return [...matches].sort((a, b) => {
    const bCorrespondencia = b.correspondencia ?? -1
    const aCorrespondencia = a.correspondencia ?? -1

    if (bCorrespondencia !== aCorrespondencia) {
      return bCorrespondencia - aCorrespondencia
    }

    const bSimilaridade = b.similaridade ?? -1
    const aSimilaridade = a.similaridade ?? -1

    return bSimilaridade - aSimilaridade
  })
}

const buildMatches = (raw: PlacafipePayload) => {
  const values = Array.isArray(raw.fipe) ? raw.fipe : []
  const mapped = values.map(mapFipeMatch).filter((item): item is PlateFipeMatch => Boolean(item))
  return sortMatches(mapped)
}

export function buildLookupResultFromPlacafipe(options: {
  requestedPlate: string
  fipePayload: PlacafipePayload
  placaPayload?: PlacafipePayload | null
}): PlateLookupResult {
  const fipePayload = toRecord(options.fipePayload)
  const placaPayload = toRecord(options.placaPayload)

  const fipeInfo = toRecord(getFirstDefined(fipePayload, ['informacoes_veiculo']))
  const placaInfo = toRecord(getFirstDefined(placaPayload, ['informacoes_veiculo']))

  const details = mapDetails(Object.keys(fipeInfo).length ? fipeInfo : placaInfo)
  const fipeMatches = buildMatches(fipePayload)
  const fipeMatch = fipeMatches[0]

  const responsePlate = normalizePlate(
    toStringSafe(
      getFirstDefined(fipePayload, ['placa']) ||
        getFirstDefined(placaPayload, ['placa']) ||
        getFirstDefined(fipeInfo, ['placa']) ||
        getFirstDefined(placaInfo, ['placa']) ||
        options.requestedPlate,
    ),
  )

  return {
    plate: responsePlate,
    brand: toStringSafe(fipeMatch?.marca || details?.marca),
    model: toStringSafe(fipeMatch?.modelo || details?.modelo),
    year: fipeMatch?.anoModelo ?? details?.anoModelo ?? details?.ano ?? null,
    fipeValue: fipeMatch?.valor ?? null,
    source: 'placafipe-api',
    ...(details ? { details } : {}),
    ...(fipeMatch ? { fipeMatch } : {}),
    ...(fipeMatches.length ? { fipeMatches } : {}),
  }
}

export function hasMeaningfulLookupData(result: PlateLookupResult) {
  return Boolean(
    result.brand ||
      result.model ||
      result.year != null ||
      result.fipeValue != null ||
      result.details ||
      (result.fipeMatches && result.fipeMatches.length > 0),
  )
}

export function resolvePlacafipeContext(runtimeConfig: {
  placaFipeBaseUrl?: string
  placaFipeToken?: string
}) {
  const baseUrl = String(runtimeConfig.placaFipeBaseUrl || '').trim()
  const token = String(runtimeConfig.placaFipeToken || '').trim()

  if (!baseUrl || !token) {
    throw createError({
      statusCode: 500,
      statusMessage:
        'Provider nao configurado. Defina NUXT_PLACA_FIPE_BASE_URL e NUXT_PLACA_FIPE_TOKEN.',
    })
  }

  return {
    baseUrl,
    token,
  }
}
