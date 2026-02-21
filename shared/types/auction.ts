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

export interface PlateLookupResult {
  plate: string
  brand: string
  model: string
  year: number | null
  fipeValue: number | null
  source: 'placa-fipe' | 'mock'
}
