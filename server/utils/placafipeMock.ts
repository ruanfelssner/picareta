import { normalizePlate } from '@core/shared/valuation'
import type {
  PlateFipeDetails,
  PlateFipeMatch,
  PlateFipeQuotaInfo,
  PlateLookupResult,
} from '@core/shared/types/auction'

type MockRuntimeConfig = {
  placaFipeMock?: string | boolean
}

type MockTemplate = {
  marca: string
  modelo: string
  codigoMarca: string
  codigoModelo: string
  codigoFipeBase: string
  combustivel: string
  cilindrada: string
  potencia: string
  segmento: string
  subSegmento: string
}

type MockCity = {
  uf: string
  municipio: string
}

type MockOverride = {
  brand: string
  model: string
  year: number
  fipeValue: number
  color: string
  fuel: string
  city: string
  state: string
}

const YES_VALUES = new Set(['1', 'true', 'yes', 'on'])

const MOCK_TEMPLATES: MockTemplate[] = [
  {
    marca: 'VOLKSWAGEN',
    modelo: 'GOL 1.6 MSI FLEX 8V 4P',
    codigoMarca: '59',
    codigoModelo: '5194',
    codigoFipeBase: '005340-1',
    combustivel: 'FLEX',
    cilindrada: '1598',
    potencia: '104',
    segmento: 'AUTO',
    subSegmento: 'AU - HATCH PEQUENO',
  },
  {
    marca: 'FIAT',
    modelo: 'ARGO DRIVE 1.3 FLEX 4P',
    codigoMarca: '21',
    codigoModelo: '9103',
    codigoFipeBase: '001553-4',
    combustivel: 'FLEX',
    cilindrada: '1332',
    potencia: '109',
    segmento: 'AUTO',
    subSegmento: 'AU - HATCH COMPACTO',
  },
  {
    marca: 'CHEVROLET',
    modelo: 'ONIX LT 1.0 FLEX 4P',
    codigoMarca: '23',
    codigoModelo: '12443',
    codigoFipeBase: '004482-8',
    combustivel: 'FLEX',
    cilindrada: '999',
    potencia: '82',
    segmento: 'AUTO',
    subSegmento: 'AU - HATCH COMPACTO',
  },
  {
    marca: 'TOYOTA',
    modelo: 'COROLLA XEI 2.0 FLEX 16V AUT.',
    codigoMarca: '56',
    codigoModelo: '11168',
    codigoFipeBase: '002183-6',
    combustivel: 'FLEX',
    cilindrada: '1987',
    potencia: '177',
    segmento: 'AUTO',
    subSegmento: 'AU - SEDAN MEDIO',
  },
  {
    marca: 'HONDA',
    modelo: 'CIVIC EXL 2.0 FLEXONE 16V AUT. 4P',
    codigoMarca: '25',
    codigoModelo: '9680',
    codigoFipeBase: '014087-7',
    combustivel: 'FLEX',
    cilindrada: '1997',
    potencia: '155',
    segmento: 'AUTO',
    subSegmento: 'AU - SEDAN MEDIO',
  },
  {
    marca: 'HYUNDAI',
    modelo: 'HB20 COMFORT 1.0 FLEX 12V MEC.',
    codigoMarca: '26',
    codigoModelo: '9738',
    codigoFipeBase: '015113-5',
    combustivel: 'FLEX',
    cilindrada: '999',
    potencia: '80',
    segmento: 'AUTO',
    subSegmento: 'AU - HATCH COMPACTO',
  },
  {
    marca: 'RENAULT',
    modelo: 'LOGAN EXPRESSION HI-FLEX 1.6 8V 4P',
    codigoMarca: '48',
    codigoModelo: '4481',
    codigoFipeBase: '025139-9',
    combustivel: 'FLEX',
    cilindrada: '1598',
    potencia: '98',
    segmento: 'AUTO',
    subSegmento: 'AU - SEDAN PEQUENO',
  },
]

const MOCK_COLORS = ['Branca', 'Prata', 'Preta', 'Cinza', 'Vermelha', 'Azul']

const MOCK_CITIES: MockCity[] = [
  { uf: 'PR', municipio: 'CURITIBA' },
  { uf: 'SP', municipio: 'SAO PAULO' },
  { uf: 'SC', municipio: 'FLORIANOPOLIS' },
  { uf: 'RS', municipio: 'PORTO ALEGRE' },
  { uf: 'MG', municipio: 'BELO HORIZONTE' },
  { uf: 'RJ', municipio: 'RIO DE JANEIRO' },
]

const MOCK_OVERRIDES: Record<string, MockOverride> = {
  AVR8J90: {
    brand: 'VOLKSWAGEN',
    model: 'GOL 1.6 MSI FLEX 8V 4P',
    year: 2018,
    fipeValue: 46200,
    color: 'Prata',
    fuel: 'FLEX',
    city: 'CURITIBA',
    state: 'PR',
  },
  MIH5B55: {
    brand: 'RENAULT',
    model: 'LOGAN EXPRESSION HI-FLEX 1.6 8V 4P',
    year: 2010,
    fipeValue: 22125,
    color: 'Branca',
    fuel: 'FLEX',
    city: 'PALHOCA',
    state: 'SC',
  },
}

const moneyFormatter = new Intl.NumberFormat('pt-BR', {
  style: 'currency',
  currency: 'BRL',
  maximumFractionDigits: 2,
})

const toBoolean = (value: unknown) => {
  if (typeof value === 'boolean') return value
  if (typeof value === 'number') return value === 1
  if (typeof value !== 'string') return false
  return YES_VALUES.has(value.trim().toLowerCase())
}

const hashPlate = (plate: string) => {
  let hash = 0
  for (let index = 0; index < plate.length; index += 1) {
    hash = (hash * 31 + plate.charCodeAt(index)) >>> 0
  }
  return hash
}

const pickByHash = <T>(items: T[], hash: number, shift = 0) => {
  if (!items.length) {
    throw new Error('Mock plate template list is empty.')
  }
  return items[(hash + shift) % items.length]
}

const formatMonthReference = () => {
  const now = new Date()
  const month = new Intl.DateTimeFormat('pt-BR', { month: 'long' }).format(now)
  const cappedMonth = month.charAt(0).toUpperCase() + month.slice(1)
  return `${cappedMonth} de ${now.getFullYear()}`
}

const buildChassi = (hash: number) => {
  const suffix = String(hash % 10000).padStart(4, '0')
  return `******${suffix}`
}

const buildMotor = (hash: number) => {
  const suffix = String((hash >> 1) % 10000).padStart(4, '0')
  return `******${suffix}`
}

const buildMockFromTemplate = (plate: string) => {
  const hash = hashPlate(plate)
  const template = pickByHash(MOCK_TEMPLATES, hash)
  const color = pickByHash(MOCK_COLORS, hash, 2)
  const city = pickByHash(MOCK_CITIES, hash, 4)

  const year = 2010 + (hash % 14)
  const baseValue = 22000 + (hash % 90000)
  const roundedValue = Math.round(baseValue / 100) * 100

  return {
    plate,
    brand: template.marca,
    model: template.modelo,
    year,
    fipeValue: roundedValue,
    color,
    fuel: template.combustivel,
    city: city.municipio,
    state: city.uf,
    template,
    hash,
  }
}

const buildMockOverride = (plate: string, override: MockOverride) => {
  const template =
    MOCK_TEMPLATES.find(
      (item) => item.marca === override.brand && item.modelo === override.model,
    ) || MOCK_TEMPLATES[0]

  const hash = hashPlate(plate)

  return {
    plate,
    brand: override.brand,
    model: override.model,
    year: override.year,
    fipeValue: override.fipeValue,
    color: override.color,
    fuel: override.fuel,
    city: override.city,
    state: override.state,
    template,
    hash,
  }
}

export function isPlacafipeMockEnabled(runtimeConfig: MockRuntimeConfig) {
  return toBoolean(runtimeConfig.placaFipeMock)
}

export function buildMockQuotaInfo(): PlateFipeQuotaInfo {
  return {
    codigo: 1,
    mensagem: 'Mock ativo: nenhuma consulta externa foi consumida.',
    dailyLimit: 9999,
    usedToday: 0,
    remainingToday: 9999,
    hasChassiAccess: true,
    raw: {
      mock: true,
      codigo: 1,
      msg: 'Mock ativo: nenhuma consulta externa foi consumida.',
      limite_diario: 9999,
      uso_diario: 0,
    },
  }
}

export function buildMockLookupResultByPlate(plateInput: string): PlateLookupResult {
  const plate = normalizePlate(plateInput)
  const override = MOCK_OVERRIDES[plate]
  const resolved = override ? buildMockOverride(plate, override) : buildMockFromTemplate(plate)

  const similaridade = 96
  const correspondencia = 100
  const mesReferencia = formatMonthReference()

  const details: PlateFipeDetails = {
    marca: resolved.brand,
    modelo: resolved.model,
    importado: 'NAO',
    ano: resolved.year,
    anoModelo: resolved.year,
    cor: resolved.color,
    cilindrada: resolved.template.cilindrada,
    potencia: resolved.template.potencia,
    combustivel: resolved.fuel,
    chassi: buildChassi(resolved.hash),
    motor: buildMotor(resolved.hash),
    passageiros: 5,
    uf: resolved.state,
    municipio: resolved.city,
    segmento: resolved.template.segmento,
    subSegmento: resolved.template.subSegmento,
    placaAlternativa: `${plate.slice(0, 3)}-${plate.slice(3)}`,
    raw: {
      mock: true,
      placa: plate,
      marca: resolved.brand,
      modelo: resolved.model,
      ano: resolved.year,
      ano_modelo: resolved.year,
      cor: resolved.color,
      combustivel: resolved.fuel,
      uf: resolved.state,
      municipio: resolved.city,
    },
  }

  const fipeMatch: PlateFipeMatch = {
    marca: resolved.brand,
    modelo: resolved.model,
    anoModelo: resolved.year,
    codigoFipe: resolved.template.codigoFipeBase,
    codigoMarca: resolved.template.codigoMarca,
    codigoModelo: resolved.template.codigoModelo,
    mesReferencia,
    combustivel: resolved.fuel,
    valor: resolved.fipeValue,
    valorFormatado: moneyFormatter.format(resolved.fipeValue),
    similaridade,
    correspondencia,
    raw: {
      mock: true,
      marca: resolved.brand,
      modelo: resolved.model,
      ano_modelo: resolved.year,
      codigo_fipe: resolved.template.codigoFipeBase,
      codigo_marca: resolved.template.codigoMarca,
      codigo_modelo: resolved.template.codigoModelo,
      mes_referencia: mesReferencia,
      combustivel: resolved.fuel,
      valor: resolved.fipeValue.toFixed(2),
      unidade_valor: 'R$',
      similaridade,
      correspondencia,
    },
  }

  return {
    plate,
    brand: resolved.brand,
    model: resolved.model,
    year: resolved.year,
    fipeValue: resolved.fipeValue,
    source: 'mock',
    details,
    fipeMatch,
    fipeMatches: [fipeMatch],
  }
}
