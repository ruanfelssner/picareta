import type { AuctionCarRecord } from '@core/shared/types/auction'

const DB_NAME = 'picareta-db'
const DB_VERSION = 1
const STORE_NAME = 'auctionCars'

let dbPromise: Promise<IDBDatabase> | null = null

function ensureClient() {
  if (!import.meta.client) {
    throw new Error('IndexedDB disponivel apenas no cliente.')
  }
}

function waitForRequest<T>(request: IDBRequest<T>) {
  return new Promise<T>((resolve, reject) => {
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error)
  })
}

function waitForTransaction(tx: IDBTransaction) {
  return new Promise<void>((resolve, reject) => {
    tx.oncomplete = () => resolve()
    tx.onerror = () => reject(tx.error)
    tx.onabort = () => reject(tx.error)
  })
}

async function openDb() {
  ensureClient()

  if (!dbPromise) {
    dbPromise = new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, DB_VERSION)

      request.onupgradeneeded = () => {
        const db = request.result
        if (!db.objectStoreNames.contains(STORE_NAME)) {
          const store = db.createObjectStore(STORE_NAME, { keyPath: 'id' })
          store.createIndex('updatedAt', 'updatedAt', { unique: false })
        }
      }

      request.onsuccess = () => resolve(request.result)
      request.onerror = () => reject(request.error)
    })
  }

  return dbPromise
}

export function useIndexedAuctionCars() {
  const isSupported =
    import.meta.client && typeof window !== 'undefined' && typeof window.indexedDB !== 'undefined'

  const listCars = async (): Promise<AuctionCarRecord[]> => {
    if (!isSupported) return []
    const db = await openDb()
    const tx = db.transaction(STORE_NAME, 'readonly')
    const store = tx.objectStore(STORE_NAME)
    const records = await waitForRequest(store.getAll())
    await waitForTransaction(tx)

    return [...records].sort((a, b) => b.updatedAt.localeCompare(a.updatedAt))
  }

  const getCar = async (id: string): Promise<AuctionCarRecord | null> => {
    if (!isSupported) return null
    const db = await openDb()
    const tx = db.transaction(STORE_NAME, 'readonly')
    const store = tx.objectStore(STORE_NAME)
    const record = await waitForRequest(store.get(id))
    await waitForTransaction(tx)
    return record || null
  }

  const saveCar = async (car: AuctionCarRecord) => {
    if (!isSupported) return
    const db = await openDb()
    const tx = db.transaction(STORE_NAME, 'readwrite')
    tx.objectStore(STORE_NAME).put(car)
    await waitForTransaction(tx)
  }

  const deleteCar = async (id: string) => {
    if (!isSupported) return
    const db = await openDb()
    const tx = db.transaction(STORE_NAME, 'readwrite')
    tx.objectStore(STORE_NAME).delete(id)
    await waitForTransaction(tx)
  }

  return {
    isSupported,
    listCars,
    getCar,
    saveCar,
    deleteCar,
  }
}
