import type { AuctionSummary, CostItem } from './types/auction'

type SummaryInput = {
  fipeValue: number
  purchaseValue: number
  costs: CostItem[]
  targetMarginPercent: number
}

const toMoney = (value: number) => {
  if (!Number.isFinite(value)) return 0
  return Math.max(0, Number(value))
}

export function calculateTotalCosts(costs: CostItem[]) {
  return costs.reduce((acc, item) => acc + toMoney(item.amount), 0)
}

export function calculateAuctionSummary(input: SummaryInput): AuctionSummary {
  const fipeValue = toMoney(input.fipeValue)
  const purchaseValue = toMoney(input.purchaseValue)
  const targetMarginPercent = Math.max(0, Number(input.targetMarginPercent) || 0)
  const totalCosts = calculateTotalCosts(input.costs)
  const totalInvestment = purchaseValue + totalCosts
  const expectedProfit = fipeValue - totalInvestment
  const marginPercent = fipeValue > 0 ? (expectedProfit / fipeValue) * 100 : 0

  return {
    totalCosts,
    totalInvestment,
    expectedProfit,
    marginPercent,
    fipeGap: fipeValue - totalInvestment,
    targetMarginPercent,
    targetReached: marginPercent >= targetMarginPercent,
  }
}

export function normalizePlate(value: string) {
  return value.toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 7)
}
