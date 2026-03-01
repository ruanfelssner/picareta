<template>
  <div class="min-h-screen pb-8">
    <header class="border-b border-white/60 bg-white/50 backdrop-blur-md">
      <div class="mx-auto flex w-full max-w-5xl items-center justify-between px-4 py-4 sm:px-6">
        <div>
          <button
            class="text-2xl font-bold text-slate-900 sm:text-3xl hover:opacity-70 transition-opacity"
            type="button"
            @click="goToStep1"
          >
            Picareta
          </button>
        </div>
        <div class="flex items-center gap-2">
          <div class="rounded-lg border border-slate-200 bg-slate-50 px-2 py-1.5">
            <div class="flex items-center gap-2">
              <p class="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Buscas</p>
              <p class="text-sm font-bold text-slate-900">
                {{ plateFipeQuota?.remainingToday ?? '-' }}
                <span class="text-[10px] font-semibold text-slate-500">/ {{ plateFipeQuota?.dailyLimit ?? '-' }}</span>
              </p>
              <button
                class="cursor-pointer rounded border border-slate-300 px-1.5 py-0.5 text-[10px] font-semibold text-slate-700 hover:bg-slate-100 disabled:opacity-60"
                type="button"
                :disabled="plateFipeQuotaLoading"
                @click="refreshPlateFipeQuota"
              >
                {{ plateFipeQuotaLoading ? '...' : '↻' }}
              </button>
            </div>
            <p v-if="plateFipeQuotaError" class="max-w-32 truncate text-[10px] text-rose-600">{{ plateFipeQuotaError }}</p>
          </div>
        </div>
      </div>
    </header>

    <main class="mx-auto w-full max-w-5xl px-2">
      <slot />
    </main>

    <ClientOnly><PwaInstallModal /></ClientOnly>
  </div>
</template>

<script setup lang="ts">
import { useAuctionCarsApi } from '~/composables/useAuctionCarsApi'
import type { PlateFipeQuotaInfo } from '@core/shared/types/auction'

const triggerStep1 = useState<number>('triggerStep1', () => 0)
const plateFipeQuota = useState<PlateFipeQuotaInfo | null>('plateFipeQuota', () => null)
const plateFipeQuotaLoading = useState<boolean>('plateFipeQuotaLoading', () => false)
const plateFipeQuotaError = useState<string>('plateFipeQuotaError', () => '')
const api = useAuctionCarsApi()

const readErrorMessage = (error: unknown) => {
  if (error && typeof error === 'object') {
    const maybeData = (error as { data?: { statusMessage?: string; message?: string } }).data
    if (maybeData?.statusMessage) return maybeData.statusMessage
    if (maybeData?.message) return maybeData.message
  }
  if (error instanceof Error && error.message) return error.message
  return 'Falha ao atualizar quota.'
}

const refreshPlateFipeQuota = async () => {
  plateFipeQuotaLoading.value = true
  plateFipeQuotaError.value = ''

  try {
    const response = await api.getPlateFipeQuotas()
    plateFipeQuota.value = response.quota
  } catch (error) {
    plateFipeQuotaError.value = readErrorMessage(error)
  } finally {
    plateFipeQuotaLoading.value = false
  }
}

const goToStep1 = () => {
  triggerStep1.value++
}
</script>
