import type { AuctionCarRecord, PlateLookupResult } from '@core/shared/types/auction'

type PlateRecognitionCandidate = {
  plate: string
  confidence: number
  bbox: number[] | null
  source: string
  raw_text?: string
  ocr_confidence?: number
  normalization_penalty?: number
  pattern?: string
}

type PlateRecognitionResult = {
  plate: string | null
  confidence: number
  bbox: number[] | null
  candidates: PlateRecognitionCandidate[]
  engine?: {
    ocr?: string
    yolo_model?: string | null
    yolo_error?: string | null
    pipeline?: string[]
  }
}

export function useAuctionCarsApi() {
  const runtimeConfig = useRuntimeConfig()

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

  const lookupPlateAndFipe = async (payload: { plate: string }) =>
    $fetch<{
      result: PlateLookupResult
      warning?: string
    }>('/api/v1/plate-fipe/lookup', {
      method: 'POST',
      body: payload,
    })

  const extractPlateFromImage = async (payload: {
    imageBase64: string
    filename?: string
    requestId?: string
  }) => {
    const base = String(runtimeConfig.public.flaskBaseUrl || 'http://localhost:5000').replace(/\/+$/, '')
    const timeout = Number(runtimeConfig.public.flaskTimeoutMs) || 120000
    return $fetch<{
      ok: boolean
      input: {
        source: 'base64'
        mime_type?: string | null
        bytes: number
        width: number
        height: number
        filename?: string
      }
      result: PlateRecognitionResult
      requestId?: string
    }>(`${base}/api/v1/plate/recognize`, {
      method: 'POST',
      body: payload,
      timeout,
    })
  }

  return {
    listRemoteCars,
    saveRemoteCar,
    deleteRemoteCar,
    lookupPlateAndFipe,
    extractPlateFromImage,
  }
}
