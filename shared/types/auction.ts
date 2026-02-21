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

export interface AuctionCarRecord {
  id: string
  plate: string
  photoDataUrl?: string
  brand: string
  model: string
  year: number | null
  fipeValue: number
  purchaseValue: number
  costs: CostItem[]
  targetMarginPercent: number
  notes: string
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
  raw: Record<string, string>
}

export interface PlateLookupResult {
  plate: string
  brand: string
  model: string
  year: number | null
  fipeValue: number | null
  source: 'placa-fipe' | 'placafipe-site' | 'mock'
  details?: PlateFipeDetails
}
