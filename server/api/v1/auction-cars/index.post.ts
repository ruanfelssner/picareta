import { randomUUID } from 'node:crypto'
import { createError, readBody } from 'h3'
import { z } from 'zod'
import { AUCTION_CARS_COLLECTION, upsertAuctionCar } from '@core/server/repositories/auctionCarsRepo'
import type { AuctionCarRecord } from '@core/shared/types/auction'
import { calculateAuctionSummary, normalizePlate } from '@core/shared/valuation'

const costSchema = z.object({
  id: z.string().min(1).optional(),
  label: z.string().default(''),
  amount: z.coerce.number().min(0).default(0),
})

const payloadSchema = z.object({
  id: z.string().min(1).optional(),
  plate: z.string().default(''),
  photoDataUrl: z.string().optional(),
  brand: z.string().default(''),
  model: z.string().default(''),
  year: z.union([z.coerce.number().int().min(1900).max(2100), z.null()]).optional(),
  fipeValue: z.coerce.number().min(0).default(0),
  purchaseValue: z.coerce.number().min(0).default(0),
  costs: z.array(costSchema).default([]),
  targetMarginPercent: z.coerce.number().min(0).default(0),
  notes: z.string().default(''),
  createdAt: z.string().datetime().optional(),
})

export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const parsed = payloadSchema.safeParse(body)

  if (!parsed.success) {
    throw createError({
      statusCode: 400,
      statusMessage: 'Payload invalido para salvar carro de leilao.',
      data: parsed.error.flatten(),
    })
  }

  const value = parsed.data
  const now = new Date().toISOString()
  const id = value.id || randomUUID()

  const costs = value.costs.map((item) => ({
    id: item.id || randomUUID(),
    label: item.label.trim() || 'Custo sem nome',
    amount: Number(item.amount) || 0,
  }))

  const record: AuctionCarRecord = {
    id,
    plate: normalizePlate(value.plate),
    photoDataUrl: value.photoDataUrl || '',
    brand: value.brand.trim(),
    model: value.model.trim(),
    year: value.year ?? null,
    fipeValue: Number(value.fipeValue) || 0,
    purchaseValue: Number(value.purchaseValue) || 0,
    costs,
    targetMarginPercent: Number(value.targetMarginPercent) || 0,
    notes: value.notes.trim(),
    createdAt: value.createdAt || now,
    updatedAt: now,
    summary: calculateAuctionSummary({
      fipeValue: value.fipeValue,
      purchaseValue: value.purchaseValue,
      costs,
      targetMarginPercent: value.targetMarginPercent,
    }),
  }

  const item = await upsertAuctionCar(record)

  return {
    collection: AUCTION_CARS_COLLECTION,
    item,
  }
})
