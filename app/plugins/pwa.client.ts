export default defineNuxtPlugin(() => {
  if (!import.meta.client) return

  const pwaInstall = usePwaInstall()
  pwaInstall.init()

  if (!('serviceWorker' in window.navigator)) return

  const registerServiceWorker = () => {
    window.navigator.serviceWorker.register('/sw.js').catch((error) => {
      console.warn('Falha ao registrar service worker:', error)
    })
  }

  if (document.readyState === 'complete') {
    registerServiceWorker()
    return
  }

  window.addEventListener('load', registerServiceWorker, { once: true })
})
