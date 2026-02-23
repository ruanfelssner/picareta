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
    placaFipeBaseUrl: process.env.NUXT_PLACA_FIPE_BASE_URL || 'https://api.placafipe.com.br',
    placaFipeToken: process.env.NUXT_PLACA_FIPE_TOKEN || '',
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
        { name: 'theme-color', content: '#0f766e' },
        { name: 'mobile-web-app-capable', content: 'yes' },
        { name: 'apple-mobile-web-app-capable', content: 'yes' },
        { name: 'apple-mobile-web-app-title', content: 'Picareta' },
        { name: 'apple-mobile-web-app-status-bar-style', content: 'default' },
      ],
      link: [
        { rel: 'manifest', href: '/manifest.webmanifest' },
        { rel: 'icon', type: 'image/png', sizes: '32x32', href: '/icons/favicon-32.png' },
        { rel: 'icon', type: 'image/png', sizes: '16x16', href: '/icons/favicon-16.png' },
        { rel: 'apple-touch-icon', sizes: '180x180', href: '/icons/apple-touch-icon-180.png' },
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
