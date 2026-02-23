import { randomUUID } from 'node:crypto'
import { getMongoDb } from '@core/server/utils/mongo'

export const OCR_FEEDBACK_EVENTS_COLLECTION = 'ocr_feedback_events'
export const OCR_FEEDBACK_STATS_COLLECTION = 'ocr_feedback_stats'

type OcrFeedbackEventDocument = {
  _id: string
  createdAt: string
  source: string
  requestId?: string
  usefulReason: 'corrected' | 'ambiguous' | 'missing_recognition'
  recognizedPlate: string | null
  confirmedPlate: string
  candidates: string[]
  corrected: boolean
  diffPositions: Array<{ index: number; from: string; to: string }>
  timingsMs: Record<string, number>
  plateCropBase64?: string
  bbox?: [number, number, number, number] | null
  imageSize?: {
    width: number
    height: number
  }
}

type OcrFeedbackStatsDocument = {
  _id: string
  kind: 'global' | 'pair' | 'position'
  key?: string
  wins?: number
  totalConfirmations?: number
  correctedConfirmations?: number
  index?: number
  fromChar?: string
  toChar?: string
  createdAt: string
  updatedAt: string
}

export type OcrFeedbackEventInput = Omit<OcrFeedbackEventDocument, '_id' | 'createdAt'>

export type OcrFeedbackProfile = {
  totalConfirmations: number
  correctedConfirmations: number
  pairWins: Record<string, number>
  positionCorrections: Record<string, number>
  updatedAt: string
}

let indexesReady = false

async function getEventsCollection() {
  const db = await getMongoDb()
  return db.collection<OcrFeedbackEventDocument>(OCR_FEEDBACK_EVENTS_COLLECTION)
}

async function getStatsCollection() {
  const db = await getMongoDb()
  return db.collection<OcrFeedbackStatsDocument>(OCR_FEEDBACK_STATS_COLLECTION)
}

async function ensureIndexes() {
  if (indexesReady) return
  const events = await getEventsCollection()
  const stats = await getStatsCollection()

  await Promise.all([
    events.createIndex({ createdAt: -1 }),
    events.createIndex({ corrected: 1, createdAt: -1 }),
    events.createIndex({ usefulReason: 1, createdAt: -1 }),
    events.createIndex({ confirmedPlate: 1, createdAt: -1 }),
    events.createIndex({ requestId: 1 }, { unique: true, sparse: true }),
    stats.createIndex({ kind: 1, wins: -1 }),
    stats.createIndex({ updatedAt: -1 }),
  ])

  indexesReady = true
}

const pairKey = (from: string, to: string) => `${from}>${to}`
const pairDocId = (from: string, to: string) => `pair:${pairKey(from, to)}`
const positionKey = (index: number, from: string, to: string) => `${index}:${from}>${to}`
const positionDocId = (index: number, from: string, to: string) => `position:${positionKey(index, from, to)}`

export async function recordOcrFeedbackEvent(input: OcrFeedbackEventInput) {
  await ensureIndexes()

  const now = new Date().toISOString()
  const { requestId, ...rest } = input
  const event: OcrFeedbackEventDocument = {
    _id: randomUUID(),
    createdAt: now,
    ...rest,
    ...(requestId ? { requestId } : {}),
  }

  const events = await getEventsCollection()
  const stats = await getStatsCollection()

  try {
    await events.insertOne(event)
  } catch (error) {
    const maybeMongo = error as { code?: number }
    if (maybeMongo.code === 11000 && requestId) {
      const existing = await events.findOne({ requestId })
      if (existing) {
        return existing
      }
    }
    throw error
  }

  const operations: Parameters<typeof stats.bulkWrite>[0] = [
    {
      updateOne: {
        filter: { _id: 'global' },
        update: {
          $set: {
            kind: 'global',
            updatedAt: now,
          },
          $setOnInsert: {
            createdAt: now,
          },
          $inc: {
            totalConfirmations: 1,
            correctedConfirmations: input.corrected ? 1 : 0,
          },
        },
        upsert: true,
      },
    },
  ]

  if (input.corrected && input.recognizedPlate) {
    operations.push({
      updateOne: {
        filter: { _id: pairDocId(input.recognizedPlate, input.confirmedPlate) },
        update: {
          $set: {
            kind: 'pair',
            key: pairKey(input.recognizedPlate, input.confirmedPlate),
            updatedAt: now,
          },
          $setOnInsert: {
            createdAt: now,
          },
          $inc: {
            wins: 1,
          },
        },
        upsert: true,
      },
    })

    for (const diff of input.diffPositions) {
      operations.push({
        updateOne: {
          filter: { _id: positionDocId(diff.index, diff.from, diff.to) },
          update: {
            $set: {
              kind: 'position',
              key: positionKey(diff.index, diff.from, diff.to),
              index: diff.index,
              fromChar: diff.from,
              toChar: diff.to,
              updatedAt: now,
            },
            $setOnInsert: {
              createdAt: now,
            },
            $inc: {
              wins: 1,
            },
          },
          upsert: true,
        },
      })
    }
  }

  if (operations.length > 0) {
    await stats.bulkWrite(operations, { ordered: false })
  }

  return event
}

export async function getOcrFeedbackProfile(): Promise<OcrFeedbackProfile> {
  await ensureIndexes()

  const stats = await getStatsCollection()

  const [globalDoc, pairDocs, positionDocs] = await Promise.all([
    stats.findOne({ _id: 'global' }),
    stats.find({ kind: 'pair' }).sort({ wins: -1 }).limit(1500).toArray(),
    stats.find({ kind: 'position' }).sort({ wins: -1 }).limit(3000).toArray(),
  ])

  const pairWins: Record<string, number> = {}
  for (const doc of pairDocs) {
    if (!doc.key) continue
    pairWins[doc.key] = Number(doc.wins || 0)
  }

  const positionCorrections: Record<string, number> = {}
  for (const doc of positionDocs) {
    if (!doc.key) continue
    positionCorrections[doc.key] = Number(doc.wins || 0)
  }

  return {
    totalConfirmations: Number(globalDoc?.totalConfirmations || 0),
    correctedConfirmations: Number(globalDoc?.correctedConfirmations || 0),
    pairWins,
    positionCorrections,
    updatedAt: String(globalDoc?.updatedAt || new Date(0).toISOString()),
  }
}
