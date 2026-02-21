import { createError, getRouterParam } from 'h3'
import { removeAuctionCar } from '@core/server/repositories/auctionCarsRepo'

export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, 'id')

  if (!id) {
    throw createError({
      statusCode: 400,
      statusMessage: 'ID obrigatorio para exclusao.',
    })
  }

  await removeAuctionCar(id)

  return {
    ok: true as const,
    id,
  }
})
