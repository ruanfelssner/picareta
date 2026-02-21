<template>
  <div class="min-h-screen pb-8">
    <header class="border-b border-white/60 bg-white/50 backdrop-blur-md">
      <div class="mx-auto flex w-full max-w-5xl items-center justify-between px-4 py-4 sm:px-6">
        <div>
          <p class="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Leilao + FIPE</p>
          <h1 class="text-2xl font-bold text-slate-900 sm:text-3xl">Picareta</h1>
        </div>
        <span class="rounded-full border border-teal-700/25 bg-teal-600/10 px-3 py-1 text-xs font-semibold text-teal-800">
          mobile first
        </span>
      </div>
    </header>

    <main class="mx-auto w-full max-w-5xl px-4 pt-6 sm:px-6">
      <slot />
    </main>
  </div>
</template>
