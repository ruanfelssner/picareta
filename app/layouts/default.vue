<template>
  <div class="min-h-screen pb-8">
    <header class="border-b border-white/60 bg-white/50 backdrop-blur-md">
      <div class="mx-auto flex w-full max-w-5xl items-center justify-between px-4 py-4 sm:px-6">
        <div>
          <h1 class="text-2xl font-bold text-slate-900 sm:text-3xl">Picareta</h1>
        </div>
      </div>
    </header>

    <main class="mx-auto w-full max-w-5xl px-4 pt-6 sm:px-6">
      <slot />
    </main>
  </div>
</template>
