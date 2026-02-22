const STATIC_CACHE = 'picareta-static-v2'
const STATIC_ASSETS = [
  '/',
  '/manifest.webmanifest',
  '/icons/pwa-192.png',
  '/icons/pwa-512.png',
  '/icons/apple-touch-icon-180.png',
  '/icons/favicon-32.png',
  '/icons/favicon-16.png',
]

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then((cache) => cache.addAll(STATIC_ASSETS)),
  )
  self.skipWaiting()
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((key) => key !== STATIC_CACHE).map((key) => caches.delete(key))),
    ),
  )
  self.clients.claim()
})

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return

  const requestUrl = new URL(event.request.url)
  if (requestUrl.origin !== self.location.origin) return

  const isStaticAsset = STATIC_ASSETS.includes(requestUrl.pathname)
  const isDocument = event.request.mode === 'navigate'

  if (isStaticAsset) {
    event.respondWith(
      caches.match(event.request).then((cached) => {
        if (cached) return cached
        return fetch(event.request).then((response) => {
          if (!response || response.status !== 200) return response
          const clone = response.clone()
          caches.open(STATIC_CACHE).then((cache) => cache.put(event.request, clone))
          return response
        })
      }),
    )
    return
  }

  if (isDocument) {
    event.respondWith(
      fetch(event.request).catch(() => caches.match('/') || Response.error()),
    )
    return
  }

  event.respondWith(fetch(event.request))
})
