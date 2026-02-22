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
        <button
          class="rounded-lg border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100"
          type="button"
          @click="goToSavedCars"
        >
          Carros salvos
          <span v-if="savedCarsCount > 0" class="ml-1.5 rounded-full bg-slate-900 px-2 py-0.5 text-xs text-white">{{ savedCarsCount }}</span>
        </button>
      </div>
    </header>

    <main class="mx-auto w-full max-w-5xl px-4 pt-6 sm:px-6">
      <slot />
    </main>

    <PwaInstallModal />
  </div>
</template>

<script setup lang="ts">
const savedCarsCount = useState<number>('savedCarsCount', () => 0)
const triggerSavedCars = useState<number>('triggerSavedCars', () => 0)
const triggerStep1 = useState<number>('triggerStep1', () => 0)

const goToSavedCars = () => {
  triggerSavedCars.value++
}

const goToStep1 = () => {
  triggerStep1.value++
}
</script>
