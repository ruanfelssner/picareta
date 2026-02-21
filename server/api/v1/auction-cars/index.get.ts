import { getQuery } from 'h3'
import { AUCTION_CARS_COLLECTION, listAuctionCars } from '@core/server/repositories/auctionCarsRepo'

export default defineEventHandler(async (event) => {
  const query = getQuery(event)
  const rawLimit = Number(query.limit ?? 50)
  const limit = Number.isFinite(rawLimit) ? Math.min(Math.max(rawLimit, 1), 200) : 50

  const items = await listAuctionCars(limit)

  return {
    collection: AUCTION_CARS_COLLECTION,
    items,
  }
})
