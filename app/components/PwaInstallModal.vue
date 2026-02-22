<script setup lang="ts">
const {
  isModalOpen,
  isIosSafari,
  canNativeInstall,
  installNow,
  dismissForDays,
  neverAskAgain,
} = usePwaInstall()

const closeForNow = () => dismissForDays()
</script>

<template>
  <teleport to="body">
    <transition
      enter-active-class="transition duration-200 ease-out"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="transition duration-150 ease-in"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div
        v-if="isModalOpen"
        class="fixed inset-0 z-[70] flex items-end bg-slate-900/60 px-4 pb-6 pt-10 sm:items-center sm:justify-center"
      >
        <div class="surface-card w-full max-w-md rounded-2xl p-5 sm:p-6">
          <div class="mb-3 inline-flex items-center rounded-full bg-teal-100 px-3 py-1 text-xs font-semibold text-teal-800">
            Instalar no celular
          </div>

          <h2 class="mb-2 text-xl font-bold text-slate-900">Usar como app</h2>

          <p class="text-sm text-slate-700">
            Instale o Picareta na tela inicial para abrir mais rapido e usar como aplicativo.
          </p>

          <ol
            v-if="isIosSafari && !canNativeInstall"
            class="mt-4 list-decimal space-y-1 pl-5 text-sm text-slate-700"
          >
            <li>Toque no botao Compartilhar do Safari.</li>
            <li>Selecione Adicionar a Tela de Inicio.</li>
            <li>Confirme em Adicionar.</li>
          </ol>

          <p
            v-else-if="canNativeInstall"
            class="mt-4 rounded-xl border border-teal-200 bg-teal-50 px-3 py-2 text-sm text-teal-900"
          >
            Seu navegador suporta instalacao direta. Toque em Instalar agora.
          </p>

          <div class="mt-5 flex flex-wrap gap-2">
            <button
              v-if="canNativeInstall"
              type="button"
              class="rounded-xl bg-teal-700 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-800"
              @click="installNow"
            >
              Instalar agora
            </button>

            <button
              type="button"
              class="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
              @click="closeForNow"
            >
              Agora nao
            </button>

            <button
              type="button"
              class="rounded-xl border border-transparent px-2 py-2 text-sm text-slate-600 hover:text-slate-900"
              @click="neverAskAgain"
            >
              Nao mostrar novamente
            </button>
          </div>
        </div>
      </div>
    </transition>
  </teleport>
</template>
