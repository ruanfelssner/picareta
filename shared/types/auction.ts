export interface CostItem {
  id: string
  label: string
  amount: number
}

export interface AuctionSummary {
  totalCosts: number
  totalInvestment: number
  expectedProfit: number
  marginPercent: number
  fipeGap: number
  targetMarginPercent: number
  targetReached: boolean
}

export type MountClass = 'sem_monta' | 'pequena' | 'media'

export type AuctionCarStatus = 'em_andamento' | 'adquirido' | 'anunciado' | 'vendido'
export type AuctionCarInterestedPreset = 'ruan' | 'vinicius' | 'jhow' | 'outro'

export interface AuctionCarRecord {
  id: string
  plate: string
  photoDataUrl?: string
  plateCropDataUrl?: string
  galleryPhotos?: string[]
  brand: string
  model: string
  year: number | null
  km?: number | null
  fipeValue: number
  purchaseValue: number
  purchaseOverrideEnabled?: boolean
  costs: CostItem[]
  targetMarginPercent: number
  mountClass: MountClass
  interested?: string
  interestedPreset?: AuctionCarInterestedPreset | null
  notes: string
  status?: AuctionCarStatus
  createdAt: string
  updatedAt: string
  summary: AuctionSummary
}

export interface PlateFipeDetails {
  marca: string
  modelo: string
  importado: string
  ano: number | null
  anoModelo: number | null
  cor: string
  cilindrada: string
  potencia: string
  combustivel: string
  chassi: string
  motor: string
  passageiros: number | null
  uf: string
  municipio: string
  segmento: string
  subSegmento: string
  placaAlternativa: string
  raw: Record<string, unknown>
}

export interface PlateFipeMatch {
  marca: string
  modelo: string
  anoModelo: number | null
  codigoFipe: string
  codigoMarca: string
  codigoModelo: string
  mesReferencia: string
  combustivel: string
  valor: number | null
  valorFormatado: string
  similaridade: number | null
  correspondencia: number | null
  raw: Record<string, unknown>
}

export interface PlateFipeQuotaInfo {
  codigo: number | null
  mensagem: string
  dailyLimit: number | null
  usedToday: number | null
  remainingToday: number | null
  hasChassiAccess: boolean | null
  raw: Record<string, unknown>
}

export interface PlateLookupResult {
  plate: string
  brand: string
  model: string
  year: number | null
  fipeValue: number | null
  source: 'placafipe-api' | 'cache' | 'mock'
  details?: PlateFipeDetails
  fipeMatch?: PlateFipeMatch
  fipeMatches?: PlateFipeMatch[]
}

export interface PlateLookupResponse {
  result: PlateLookupResult
  warning?: string
  detail?: string
  cache: {
    hit: boolean
    storedAt?: string
  }
  quota?: PlateFipeQuotaInfo
}
