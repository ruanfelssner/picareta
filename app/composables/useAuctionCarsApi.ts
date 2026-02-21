import type { AuctionCarRecord, PlateLookupResult } from '@core/shared/types/auction'

export function useAuctionCarsApi() {
  const extractPlateFromImage = async (payload: { imageBase64: string }) =>
    $fetch<{
      result: {
        plate: string
        candidates: string[]
        bestScore: number
        secondScore: number
        margin: number
        highConfidence: boolean
        rawText: string
        engine?: 'python'
      }
      warning?: string
    }>('/api/v1/plate-fipe/extract', {
      method: 'POST',
      body: payload,
    })

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
    $fetch<{
      result: PlateLookupResult
      warning?: string
      data?: {
        candidates?: string[]
        bestScore?: number
        secondScore?: number
        rawText?: string
      }
    }>('/api/v1/plate-fipe/lookup', {
      method: 'POST',
      body: payload,
    })

  return {
    extractPlateFromImage,
    listRemoteCars,
    saveRemoteCar,
    deleteRemoteCar,
    lookupPlateAndFipe,
  }
}
