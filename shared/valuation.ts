import type { AuctionSummary, CostItem, MountClass } from './types/auction'

type SummaryInput = {
  fipeValue: number
  purchaseValue: number
  costs: CostItem[]
  targetMarginPercent: number
  mountClass: MountClass
}

const toMoney = (value: number) => {
  if (!Number.isFinite(value)) return 0
  return Math.max(0, Number(value))
}

export function calculateTotalCosts(costs: CostItem[]) {
  return costs.reduce((acc, item) => acc + toMoney(item.amount), 0)
}

export function calculateSaleValue(fipeValue: number, mountClass: MountClass): number {
  const fipe = toMoney(fipeValue)
  if (mountClass === 'pequena') {
    return fipe * 0.95 // 5% abaixo da FIPE
  } else {
    return fipe * 0.80 // 20% abaixo da FIPE
  }
}

export function calculateAuctionSummary(input: SummaryInput): AuctionSummary {
  const fipeValue = toMoney(input.fipeValue)
  const purchaseValue = toMoney(input.purchaseValue)
  const targetMarginPercent = Math.max(0, Number(input.targetMarginPercent) || 0)
  const totalCosts = calculateTotalCosts(input.costs)
  const totalInvestment = purchaseValue + totalCosts
  const saleValue = calculateSaleValue(fipeValue, input.mountClass)
  const expectedProfit = saleValue - totalInvestment
  const marginPercent = saleValue > 0 ? (expectedProfit / saleValue) * 100 : 0

  return {
    totalCosts,
    totalInvestment,
    expectedProfit,
    marginPercent,
    fipeGap: saleValue - totalInvestment,
    targetMarginPercent,
    targetReached: marginPercent >= targetMarginPercent,
  }
}

export function normalizePlate(value: string) {
  return value.toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 7)
}
