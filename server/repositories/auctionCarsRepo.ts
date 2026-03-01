import type { AuctionCarRecord } from '@core/shared/types/auction'
import { getMongoDb } from '@core/server/utils/mongo'

export const AUCTION_CARS_COLLECTION = 'auction_cars'

type AuctionCarDocument = AuctionCarRecord & {
  _id: string
}

const toRecord = (doc: AuctionCarDocument): AuctionCarRecord => ({
  id: doc._id,
  plate: doc.plate,
  photoDataUrl: doc.photoDataUrl,
  brand: doc.brand,
  model: doc.model,
  year: doc.year,
  fipeValue: doc.fipeValue,
  purchaseValue: doc.purchaseValue,
  costs: doc.costs,
  targetMarginPercent: doc.targetMarginPercent,
  mountClass: doc.mountClass,
  interested: doc.interested,
  interestedPreset: doc.interestedPreset,
  notes: doc.notes,
  status: doc.status,
  createdAt: doc.createdAt,
  updatedAt: doc.updatedAt,
  summary: doc.summary,
})

async function getCollection() {
  const db = await getMongoDb()
  return db.collection<AuctionCarDocument>(AUCTION_CARS_COLLECTION)
}

export async function listAuctionCars(limit = 50) {
  const collection = await getCollection()
  const docs = await collection.find().sort({ updatedAt: -1 }).limit(limit).toArray()
  return docs.map(toRecord)
}

export async function upsertAuctionCar(record: AuctionCarRecord) {
  const collection = await getCollection()

  const doc: AuctionCarDocument = {
    ...record,
    _id: record.id,
  }

  await collection.updateOne({ _id: doc._id }, { $set: doc }, { upsert: true })
  return toRecord(doc)
}

export async function removeAuctionCar(id: string) {
  const collection = await getCollection()
  await collection.deleteOne({ _id: id })
}
