import type { PlateLookupResult } from '@core/shared/types/auction'
import { getMongoDb } from '@core/server/utils/mongo'

export const PLATE_LOOKUP_CACHE_COLLECTION = 'plate_lookup_cache'

type PlateLookupCacheDocument = {
  _id: string
  result: PlateLookupResult
  createdAt: string
  updatedAt: string
}

export type PlateLookupCacheRecord = {
  plate: string
  result: PlateLookupResult
  createdAt: string
  updatedAt: string
}

const toRecord = (doc: PlateLookupCacheDocument): PlateLookupCacheRecord => ({
  plate: doc._id,
  result: doc.result,
  createdAt: doc.createdAt,
  updatedAt: doc.updatedAt,
})

async function getCollection() {
  const db = await getMongoDb()
  return db.collection<PlateLookupCacheDocument>(PLATE_LOOKUP_CACHE_COLLECTION)
}

export async function findPlateLookupCache(plate: string) {
  const collection = await getCollection()
  const doc = await collection.findOne({ _id: plate })
  return doc ? toRecord(doc) : null
}

export async function upsertPlateLookupCache(plate: string, result: PlateLookupResult) {
  const collection = await getCollection()
  const now = new Date().toISOString()

  const persistedResult: PlateLookupResult = {
    ...result,
    source: result.source === 'cache' ? 'placafipe-api' : result.source,
  }

  await collection.updateOne(
    { _id: plate },
    {
      $set: {
        result: persistedResult,
        updatedAt: now,
      },
      $setOnInsert: {
        createdAt: now,
      },
    },
    { upsert: true },
  )

  const saved = await collection.findOne({ _id: plate })
  if (!saved) {
    return {
      plate,
      result: persistedResult,
      createdAt: now,
      updatedAt: now,
    } satisfies PlateLookupCacheRecord
  }

  return toRecord(saved)
}
