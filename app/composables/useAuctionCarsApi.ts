import type { AuctionCarRecord, PlateLookupResult } from '@core/shared/types/auction'

export function useAuctionCarsApi() {
  const listRemoteCars = async (limit = 50) =>
    $fetch<{ items: AuctionCarRecord[]; collection: string }>('/api/v1/auction-cars', {
      method: 'GET',
      query: { limit },
    })

  const saveRemoteCar = async (payload: Partial<AuctionCarRecord>) =>
    $fetch<{ item: AuctionCarRecord; collection: string }>('/api/v1/auction-cars', {
      method: 'POST',
      body: payload,
    })

  const deleteRemoteCar = async (id: string) =>
    $fetch<{ ok: true; id: string }>('/api/v1/auction-cars/' + encodeURIComponent(id), {
      method: 'DELETE',
    })

  const lookupPlateAndFipe = async (payload: { plate?: string; imageBase64?: string }) =>
    $fetch<{ result: PlateLookupResult }>('/api/v1/plate-fipe/lookup', {
      method: 'POST',
      body: payload,
    })

  return {
    listRemoteCars,
    saveRemoteCar,
    deleteRemoteCar,
    lookupPlateAndFipe,
  }
}
