import { useRuntimeConfig } from '#imports'
import { createError } from 'h3'
import { MongoClient } from 'mongodb'

type MongoState = {
  client: MongoClient
  connecting?: Promise<MongoClient>
  connected?: boolean
}

declare global {
  var __mongoState: MongoState | undefined
}

const getConfig = () => useRuntimeConfig()

export function isMongoConfigured() {
  const config = getConfig()
  return Boolean(config.mongoUri && config.mongoDbName)
}

function getMongoState() {
  if (!globalThis.__mongoState) {
    const config = getConfig()

    if (!config.mongoUri) {
      throw createError({
        statusCode: 503,
        statusMessage: 'Mongo nao configurado (NUXT_MONGO_URI).',
      })
    }

    globalThis.__mongoState = {
      client: new MongoClient(config.mongoUri),
    }
  }

  return globalThis.__mongoState
}

export async function getMongoDb() {
  const config = getConfig()

  if (!config.mongoDbName) {
    throw createError({
      statusCode: 503,
      statusMessage: 'Mongo nao configurado (NUXT_MONGO_DB_NAME).',
    })
  }

  const state = getMongoState()

  if (!state.connected) {
    state.connecting ||= state.client.connect()
    await state.connecting
    state.connected = true
  }

  return state.client.db(config.mongoDbName)
}
