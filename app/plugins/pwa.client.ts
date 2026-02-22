export default defineNuxtPlugin(() => {
  if (!import.meta.client) return

  const pwaInstall = usePwaInstall()
  pwaInstall.init()

  if (!('serviceWorker' in window.navigator)) return

  window.addEventListener(
    'load',
    () => {
      window.navigator.serviceWorker.register('/sw.js').catch((error) => {
        console.warn('Falha ao registrar service worker:', error)
      })
    },
    { once: true },
  )
})
