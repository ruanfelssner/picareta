import tailwindcss from '@tailwindcss/vite'
import { fileURLToPath } from 'node:url'

// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: '2025-07-15',
  devtools: { enabled: process.env.NODE_ENV === 'development' },
  ssr: true,
  modules: ['@nuxt/eslint'],
  css: ['~/assets/css/main.css'],
  alias: {
    '@core': fileURLToPath(new URL('./', import.meta.url)),
  },
  runtimeConfig: {
    flaskBaseUrl:
      process.env.NUXT_FLASK_BASE_URL ||
      process.env.NUXT_PUBLIC_FLASK_BASE_URL ||
      'http://127.0.0.1:5000',
    flaskTimeoutMs: Number(
      process.env.NUXT_FLASK_TIMEOUT_MS || process.env.NUXT_PUBLIC_FLASK_TIMEOUT_MS || 120000,
    ),
    mongoUri: '',
    mongoDbName: 'picareta',
    placaFipeBaseUrl: '',
    placaFipeToken: '',
    placaFipeLookupPath: process.env.NUXT_PLACA_FIPE_LOOKUP_PATH || '/lookup',
    placaFipeLookupMethod: process.env.NUXT_PLACA_FIPE_LOOKUP_METHOD || 'POST',
    placaFipeRequestPlateField: process.env.NUXT_PLACA_FIPE_REQUEST_PLATE_FIELD || 'placa',
    placaFipeDeviceToken: process.env.NUXT_PLACA_FIPE_DEVICE_TOKEN || '',
    placaFipeUserAgent:
      process.env.NUXT_PLACA_FIPE_USER_AGENT || 'Thunder Client (https://www.thunderclient.com)',
    placaFipeTimeoutMs: Number(process.env.NUXT_PLACA_FIPE_TIMEOUT_MS || 8000),
    placaFipeLookupStrategy: process.env.NUXT_PLACA_FIPE_LOOKUP_STRATEGY || 'scrape-first',
    placaFipeCfClearance: process.env.NUXT_PLACA_FIPE_CF_CLEARANCE || '',
    public: {
      siteUrl: 'http://localhost:3000',
      siteName: 'Picareta',
      defaultTitle: 'Picareta',
      defaultDescription: 'Cadastro e análise de carros de leilão com cálculo de margem.',
    },
  },
  app: {
    head: {
      title: 'Picareta',
      titleTemplate: '%s · Picareta',
      htmlAttrs: {
        lang: 'pt-BR',
      },
      meta: [
        { charset: 'utf-8' },
        { name: 'viewport', content: 'width=device-width, initial-scale=1, viewport-fit=cover' },
        {
          name: 'description',
          content: 'Cadastro de carros de leilão, custos e margem com suporte mobile/offline.',
        },
        { name: 'application-name', content: 'Picareta' },
      ],
      link: [
        { rel: 'preconnect', href: 'https://fonts.googleapis.com' },
        { rel: 'preconnect', href: 'https://fonts.gstatic.com', crossorigin: '' },
        {
          rel: 'stylesheet',
          href: 'https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,700&family=Space+Grotesk:wght@400;500;600;700&display=swap',
        },
      ],
    },
  },
  nitro: {
    alias: {
      '@core': fileURLToPath(new URL('./', import.meta.url)),
    },
  },
  vite: {
    plugins: [tailwindcss()],
  },
})
