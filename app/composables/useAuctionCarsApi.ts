import type {
  AuctionCarRecord,
  PlateFipeQuotaInfo,
  PlateLookupResponse,
} from '@core/shared/types/auction'

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
    timings_ms?: Record<string, number>
    ambiguous_top_pair?: boolean
    zero_priority_applied?: boolean
  }
}

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

  const lookupPlateAndFipe = async (payload: { plate: string }) =>
    $fetch<PlateLookupResponse>('/api/v1/plate-fipe/lookup', {
      method: 'POST',
      body: payload,
    })

  const getPlateFipeQuotas = async () =>
    $fetch<{
      quota: PlateFipeQuotaInfo
    }>('/api/v1/plate-fipe/quotas', {
      method: 'GET',
    })

  const extractPlateFromImage = async (payload: {
    imageBase64: string
    filename?: string
    requestId?: string
  }) => {
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
    }>('/api/v1/plate/recognize', {
      method: 'POST',
      body: payload,
    })
  }

  return {
    listRemoteCars,
    saveRemoteCar,
    deleteRemoteCar,
    lookupPlateAndFipe,
    getPlateFipeQuotas,
    extractPlateFromImage,
  }
}
