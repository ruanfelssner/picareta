type InstallChoiceOutcome = 'accepted' | 'dismissed'

type BeforeInstallPromptEvent = Event & {
  prompt: () => Promise<void>
  userChoice: Promise<{ outcome: InstallChoiceOutcome; platform: string }>
}

const DISMISS_UNTIL_KEY = 'picareta:pwa-install-dismiss-until'
const NEVER_ASK_KEY = 'picareta:pwa-install-never-ask'
const DEFAULT_COOLDOWN_DAYS = 7

let initialized = false
let deferredInstallPrompt: BeforeInstallPromptEvent | null = null

const now = () => Date.now()

const readDismissUntil = () => {
  const raw = localStorage.getItem(DISMISS_UNTIL_KEY)
  if (!raw) return 0
  const parsed = Number(raw)
  return Number.isFinite(parsed) ? parsed : 0
}

const detectStandaloneMode = () => {
  const mediaStandalone = window.matchMedia('(display-mode: standalone)').matches
  const navigatorStandalone = Boolean((window.navigator as Navigator & { standalone?: boolean }).standalone)
  return mediaStandalone || navigatorStandalone
}

const detectIosSafari = () => {
  const ua = window.navigator.userAgent.toLowerCase()
  const ios =
    /iphone|ipad|ipod/.test(ua) ||
    (window.navigator.platform === 'MacIntel' && window.navigator.maxTouchPoints > 1)
  const safari = /safari/.test(ua) && !/crios|fxios|edgios|opr\//.test(ua)
  return ios && safari
}

const detectMobileBrowser = () => {
  const ua = window.navigator.userAgent.toLowerCase()
  return /android|iphone|ipad|ipod|mobile/.test(ua)
}

export const usePwaInstall = () => {
  const isModalOpen = useState<boolean>('pwa-install-modal-open', () => false)
  const isIosSafari = useState<boolean>('pwa-install-is-ios-safari', () => false)
  const isMobileBrowser = useState<boolean>('pwa-install-is-mobile', () => false)
  const isStandalone = useState<boolean>('pwa-install-is-standalone', () => false)
  const canNativeInstall = useState<boolean>('pwa-install-can-native', () => false)
  const isPwaInstallSupported = useState<boolean>('pwa-install-supported', () => false)

  const refreshCapabilities = () => {
    if (!import.meta.client) return

    isIosSafari.value = detectIosSafari()
    isMobileBrowser.value = detectMobileBrowser()
    isStandalone.value = detectStandaloneMode()
    canNativeInstall.value = Boolean(deferredInstallPrompt)
    isPwaInstallSupported.value = isIosSafari.value || canNativeInstall.value || isMobileBrowser.value
  }

  const shouldAutoOpenModal = () => {
    if (!import.meta.client) return false
    if (isStandalone.value) return false
    if (localStorage.getItem(NEVER_ASK_KEY) === '1') return false
    return now() >= readDismissUntil()
  }

  const openModal = () => {
    refreshCapabilities()
    if (shouldAutoOpenModal()) {
      isModalOpen.value = true
    }
  }

  const closeModal = () => {
    isModalOpen.value = false
  }

  const dismissForDays = (days = DEFAULT_COOLDOWN_DAYS) => {
    const until = now() + days * 24 * 60 * 60 * 1000
    localStorage.setItem(DISMISS_UNTIL_KEY, String(until))
    closeModal()
  }

  const neverAskAgain = () => {
    localStorage.setItem(NEVER_ASK_KEY, '1')
    closeModal()
  }

  const installNow = async () => {
    refreshCapabilities()
    if (!deferredInstallPrompt) {
      closeModal()
      return
    }

    await deferredInstallPrompt.prompt()
    const choice = await deferredInstallPrompt.userChoice
    deferredInstallPrompt = null
    refreshCapabilities()

    if (choice?.outcome === 'accepted') {
      neverAskAgain()
      return
    }

    dismissForDays(3)
  }

  const init = () => {
    if (!import.meta.client || initialized) return
    initialized = true

    const onBeforeInstallPrompt = (event: Event) => {
      event.preventDefault()
      deferredInstallPrompt = event as BeforeInstallPromptEvent
      refreshCapabilities()
      openModal()
    }

    const onAppInstalled = () => {
      deferredInstallPrompt = null
      refreshCapabilities()
      neverAskAgain()
    }

    const onVisibilityChange = () => {
      if (document.visibilityState !== 'visible') return
      refreshCapabilities()
      if (!isModalOpen.value) openModal()
    }

    window.addEventListener('beforeinstallprompt', onBeforeInstallPrompt)
    window.addEventListener('appinstalled', onAppInstalled)
    document.addEventListener('visibilitychange', onVisibilityChange)

    refreshCapabilities()
    openModal()
  }

  return {
    isModalOpen,
    isIosSafari,
    isMobileBrowser,
    isStandalone,
    canNativeInstall,
    isPwaInstallSupported,
    init,
    openModal,
    closeModal,
    installNow,
    dismissForDays,
    neverAskAgain,
  }
}
