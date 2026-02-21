import { createError } from 'h3'
import type { PlateFipeDetails } from '@core/shared/types/auction'

const stripTags = (value: string) => value.replace(/<[^>]*>/g, ' ')

const decodeEntities = (value: string) => {
  const namedMap: Record<string, string> = {
    nbsp: ' ',
    amp: '&',
    quot: '"',
    apos: "'",
    lt: '<',
    gt: '>',
    aacute: 'á',
    eacute: 'é',
    iacute: 'í',
    oacute: 'ó',
    uacute: 'ú',
    acirc: 'â',
    ecirc: 'ê',
    ocirc: 'ô',
    atilde: 'ã',
    otilde: 'õ',
    ccedil: 'ç',
    auml: 'ä',
    euml: 'ë',
    iuml: 'ï',
    ouml: 'ö',
    uuml: 'ü',
  }

  const partiallyDecoded = value
    .replace(/&nbsp;/gi, ' ')
    .replace(/&amp;/gi, '&')
    .replace(/&quot;/gi, '"')
    .replace(/&#39;/gi, "'")
    .replace(/&lt;/gi, '<')
    .replace(/&gt;/gi, '>')

  return partiallyDecoded
    .replace(/&#(\d+);/g, (entity, code) => {
      const parsed = Number(code)
      return Number.isFinite(parsed) ? String.fromCodePoint(parsed) : entity
    })
    .replace(/&#x([0-9a-f]+);/gi, (entity, hex) => {
      const parsed = Number.parseInt(hex, 16)
      return Number.isFinite(parsed) ? String.fromCodePoint(parsed) : entity
    })
    .replace(/&([a-z]+);/gi, (entity, name) => namedMap[name.toLowerCase()] ?? entity)
}

const cleanText = (value: string) => decodeEntities(stripTags(value)).replace(/\s+/g, ' ').trim()

const normalizeLabel = (value: string) =>
  value
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9 ]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()

const parseNumber = (value: string) => {
  const match = value.match(/-?\d+/)
  return match ? Number(match[0]) : null
}

const parseMoney = (value: string) => {
  const normalized = value.replace(/\./g, '').replace(',', '.').replace(/[^0-9.-]/g, '')
  const parsed = Number(normalized)
  return Number.isFinite(parsed) ? parsed : null
}

const toDetails = (raw: Record<string, string>): PlateFipeDetails => ({
  marca: raw.marca || '',
  modelo: raw.modelo || '',
  importado: raw.importado || '',
  ano: parseNumber(raw.ano || ''),
  anoModelo: parseNumber(raw['ano modelo'] || ''),
  cor: raw.cor || '',
  cilindrada: raw.cilindrada || '',
  potencia: raw.potencia || '',
  combustivel: raw.combustivel || '',
  chassi: raw.chassi || '',
  motor: raw.motor || '',
  passageiros: parseNumber(raw.passageiros || ''),
  uf: raw.uf || '',
  municipio: raw.municipio || '',
  raw,
})

const extractTableRows = (html: string) => {
  const tableMatch = html.match(/<table[^>]*class=['"][^'"]*fipeTablePriceDetail[^'"]*['"][^>]*>([\s\S]*?)<\/table>/i)

  if (!tableMatch?.[1]) {
    return null
  }

  const tableContent = tableMatch[1]
  const rows = [...tableContent.matchAll(/<tr[^>]*>([\s\S]*?)<\/tr>/gi)]
  const result: Record<string, string> = {}

  for (const rowMatch of rows) {
    const rowHtml = rowMatch[1] || ''
    const cells = [...rowHtml.matchAll(/<td[^>]*>([\s\S]*?)<\/td>/gi)]

    if (cells.length < 2) continue

    const rawLabel = cleanText(cells[0]?.[1] || '').replace(/:$/, '')
    const rawValue = cleanText(cells[1]?.[1] || '')
    const label = normalizeLabel(rawLabel)

    if (!label) continue
    result[label] = rawValue
  }

  return Object.keys(result).length > 0 ? result : null
}

const extractFipeValue = (html: string) => {
  const contextual = html.match(/(?:valor|preco|preço)[^\n<]{0,80}fipe[\s\S]{0,80}?R\$\s*([0-9.,]+)/i)
  if (contextual?.[1]) {
    return parseMoney(contextual[1])
  }

  const generic = html.match(/R\$\s*([0-9.,]+)/i)
  if (generic?.[1]) {
    return parseMoney(generic[1])
  }

  return null
}

const isCloudflareBlock = (html: string) => {
  const text = html.toLowerCase()
  return (
    text.includes('attention required! | cloudflare') ||
    text.includes('sorry, you have been blocked') ||
    text.includes('performing security verification')
  )
}

export async function fetchPlacafipeByPlate(plate: string, timeout = 12000) {
  const url = `https://placafipe.com/placa/${encodeURIComponent(plate)}`

  const runtimeConfig = useRuntimeConfig()
  const cfClearance = String(runtimeConfig.placaFipeCfClearance || '').trim()

  let response
  try {
    response = await $fetch.raw<string>(url, {
      method: 'GET',
      responseType: 'text',
      timeout,
      headers: {
        'user-agent':
          'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36',
        accept:
          'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'en,pt-BR;q=0.9,pt;q=0.8,es;q=0.7,en-US;q=0.6,und;q=0.5',
        'cache-control': 'no-cache',
        pragma: 'no-cache',
        referer: 'https://placafipe.com/',
        origin: 'https://placafipe.com',
        'upgrade-insecure-requests': '1',
        priority: 'u=0, i',
        'sec-ch-ua': '"Not:A-Brand";v="99", "Google Chrome";v="145", "Chromium";v="145"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-user': '?1',
        ...(cfClearance ? { cookie: `cf_clearance=${cfClearance}` } : {}),
      },
    })
  } catch (error: unknown) {
    const statusCode = Number((error as { statusCode?: number }).statusCode || 0)
    if (statusCode === 403) {
      throw createError({
        statusCode: 502,
        statusMessage: cfClearance
          ? 'placafipe.com bloqueou a requisicao mesmo com cf_clearance.'
          : 'placafipe.com bloqueou a requisicao (403). Defina NUXT_PLACA_FIPE_CF_CLEARANCE com cookie valido do navegador.',
      })
    }
    throw error
  }

  const html = String(response._data || '')

  if (isCloudflareBlock(html)) {
    throw createError({
      statusCode: 502,
      statusMessage: 'placafipe.com bloqueou a requisicao do servidor (Cloudflare).',
    })
  }

  const rows = extractTableRows(html)

  if (!rows) {
    throw createError({
      statusCode: 502,
      statusMessage: 'Nao foi possivel localizar a tabela fipeTablePriceDetail no HTML retornado.',
    })
  }

  const details = toDetails(rows)

  return {
    plate,
    brand: details.marca,
    model: details.modelo,
    year: details.anoModelo ?? details.ano,
    fipeValue: extractFipeValue(html),
    details,
  }
}
