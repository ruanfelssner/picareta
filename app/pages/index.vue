<template>
  <div class="min-h-screen bg-linear-to-br from-slate-50 to-slate-100 pb-8">
    <!-- Step Indicator -->
    <div class="sticky top-0 z-10 bg-white/80 px-4 py-4 backdrop-blur-sm">
      <div class="mx-auto flex max-w-xs items-center">
        <template v-for="stepNum in [1, 2, 3]" :key="stepNum">
          <div
            class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-sm font-bold transition-all"
            :class="{
              'bg-slate-900 text-white': currentStep === stepNum,
              'bg-emerald-500 text-white': currentStep > stepNum,
              'bg-slate-200 text-slate-500': currentStep < stepNum,
            }"
          >
            <span v-if="currentStep > stepNum">✓</span>
            <span v-else>{{ stepNum }}</span>
          </div>
          <div v-if="stepNum < 3" class="mx-2 h-0.5 flex-1 bg-slate-200 transition-colors" :class="{ 'bg-emerald-500': currentStep > stepNum }" />
        </template>
      </div>
    </div>

    <!-- Fila de rascunhos -->
    <div v-if="draftQueue.length > 0" class="bg-slate-900 px-4 py-2">
      <div class="mx-auto max-w-3xl">
        <p class="mb-1.5 text-center text-xs text-slate-400">Fila ({{ draftQueue.length }}) &mdash; toque no pronto para preencher</p>
        <div class="flex gap-2 overflow-x-auto pb-1">
          <div
            v-for="(item, idx) in draftQueue"
            :key="item.draft.id"
            class="relative shrink-0 rounded-xl border-2 p-1.5 text-left transition-colors"
            :class="{
              'border-white bg-slate-700 cursor-pointer': item.draft.id === activeQueueId,
              'border-slate-600 bg-slate-800 hover:border-slate-400 cursor-pointer': item.status === 'ready' && item.draft.id !== activeQueueId,
              'border-slate-700 bg-slate-800 cursor-default opacity-70': item.status !== 'ready',
            }"
            @click="item.status === 'ready' && loadFromQueue(idx)"
          >
            <div class="relative">
              <img
                v-if="item.draft.photoDataUrl"
                :src="item.draft.photoDataUrl"
                class="h-32 w-32 rounded-lg object-cover"
                alt=""
              >
              <div v-else class="flex h-32 w-32 items-center justify-center rounded-lg bg-slate-700">
                <svg class="h-6 w-6 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
              </div>
              <!-- Status overlay for processing -->
              <div v-if="item.status === 'processing'" class="absolute inset-0 flex items-center justify-center rounded-lg bg-slate-900/60">
                <div class="flex flex-col items-center gap-1">
                  <div class="h-5 w-5 animate-spin rounded-full border-2 border-white border-t-transparent" />
                  <p class="text-[10px] font-semibold text-white">
                    {{ queueItemStageLabel(item) }} {{ formatElapsedMs(getQueueItemElapsedMs(item)) }}
                  </p>
                </div>
              </div>
              <!-- Selected checkmark -->
              <div v-if="item.draft.id === activeQueueId" class="absolute inset-0 flex items-center justify-center rounded-lg bg-slate-900/40">
                <svg class="h-6 w-6 text-white drop-shadow" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7" /></svg>
              </div>
              <button
                class="absolute bottom-1 right-1 cursor-pointer rounded-md bg-slate-900/80 px-2 py-1 text-[10px] font-semibold text-white hover:bg-slate-900"
                type="button"
                @click.stop="openQueuePreview(idx)"
              >
                Ver
              </button>
            </div>
            <p
              class="mt-1 max-w-[128px] truncate text-center text-xs font-semibold"
              :class="item.draft.id === activeQueueId ? 'text-white' : 'text-slate-300'"
            >
              {{ item.status === 'processing' ? '...' : (item.draft.plate || '???') }}
            </p>
            <p
              v-if="queueItemDurationLabel(item)"
              class="mt-0.5 max-w-[128px] truncate text-center text-[10px] font-semibold"
              :class="item.status === 'processing' ? 'text-slate-300' : 'text-slate-400'"
            >
              {{ queueItemDurationLabel(item) }}
            </p>
            <p
              v-if="item.errorMessage"
              class="mt-0.5 max-w-[128px] truncate text-center text-[10px] leading-tight"
              :class="item.status === 'error' ? 'text-rose-400' : 'text-amber-400'"
              :title="item.errorMessage"
            >
              {{ item.errorMessage }}
            </p>
            <!-- Status dot -->
            <div
              class="absolute right-0.5 top-0.5 h-2.5 w-2.5 rounded-full border border-slate-900"
              :class="{
                'bg-slate-400 animate-pulse': item.status === 'processing',
                'bg-emerald-400': item.status === 'ready' && item.ocrSuccess,
                'bg-amber-400': item.status === 'ready' && !item.ocrSuccess,
                'bg-rose-400': item.status === 'error',
              }"
            />
            <button
              class="absolute -right-1.5 -top-1.5 flex h-5 w-5 items-center justify-center rounded-full bg-rose-600 text-white hover:bg-rose-500"
              type="button"
              @click.stop="removeFromQueue(idx)"
            >
              <svg class="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M6 18L18 6M6 6l12 12" /></svg>
            </button>
          </div>
        </div>
      </div>
    </div>

    <div v-if="queuePreviewItem" class="fixed inset-0 z-50 bg-slate-950/85 backdrop-blur-sm" @click.self="closeQueuePreview">
      <div class="absolute inset-0 flex items-center justify-center p-3">
        <div class="relative max-h-[96dvh] w-fit max-w-[96vw] overflow-hidden rounded-2xl border border-white/20">
          <img
            v-if="queuePreviewItem.draft.photoDataUrl"
            :src="queuePreviewItem.draft.photoDataUrl"
            class="block h-auto max-h-[96dvh] w-auto max-w-[96vw]"
            alt="Preview da foto"
          >

          <button
            class="absolute right-3 top-3 z-30 cursor-pointer rounded-lg bg-black/65 px-3 py-1.5 text-xs font-semibold text-white hover:bg-black/80"
            type="button"
            @click="closeQueuePreview"
          >
            Fechar
          </button>

          <div class="pointer-events-none absolute inset-x-0 top-0 h-24 bg-linear-to-b from-black/65 to-transparent" />
          <div class="absolute left-3 top-3 z-20 rounded-md bg-black/55 px-2 py-1 text-xs font-semibold text-white">
            {{ queuePreviewItem.draft.plate || 'Sem placa confirmada' }}
          </div>

          <div class="pointer-events-none absolute inset-x-0 bottom-0 h-40 bg-linear-to-t from-black/85 to-transparent" />
          <div class="absolute inset-x-3 bottom-3 z-20">
            <p class="text-xs font-semibold text-white/90">
              Toque na placa correta para confirmar direto pela foto
            </p>

            <div v-if="queuePreviewItem.status === 'processing'" class="mt-2 inline-flex rounded-md bg-white/90 px-2 py-1 text-xs font-semibold text-slate-700">
              Processando {{ queueItemStageLabel(queuePreviewItem) }}: {{ formatElapsedMs(getQueueItemElapsedMs(queuePreviewItem)) }}
            </div>

            <div v-else-if="queuePreviewCandidates.length > 0" class="mt-2 flex flex-wrap gap-2">
            <button
              v-for="candidate in queuePreviewCandidates"
              :key="candidate"
              class="cursor-pointer rounded-md border px-3 py-1.5 text-xs font-bold transition-colors disabled:cursor-not-allowed disabled:opacity-60"
              :class="
                candidate === normalizePlate(queuePreviewItem.draft.plate || '')
                  ? 'border-white bg-white text-slate-900'
                  : 'border-amber-300 bg-amber-50/95 text-amber-900 hover:bg-amber-100'
              "
              type="button"
              :disabled="loadingLookup"
              @click="confirmQueueCandidate(candidate)"
            >
              {{ loadingLookup && selectingPlateCandidate === candidate ? 'Consultando...' : candidate }}
            </button>
          </div>

            <div v-else class="mt-2 inline-flex rounded-md bg-white/90 px-2 py-1 text-xs font-semibold text-slate-700">
              {{ queuePreviewItem.errorMessage || 'Sem sugestao OCR para esta foto.' }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- STEP 1: Foto e OCR -->
    <section v-if="currentStep === 1" class="mx-4 mt-4 space-y-4">
      <div class="surface-card rounded-2xl p-5">
        <h2 class="text-xl font-bold text-slate-900">Foto do veículo</h2>
        <p class="mt-1 text-sm text-slate-600">Envie quantas fotos quiser — cada uma vai para a fila e processa em segundo plano</p>

        <div
          v-if="statusMessage && statusTone !== 'ok'"
          class="mt-3 rounded-xl px-3 py-2 text-sm font-semibold"
          :class="{
            'border border-amber-300 bg-amber-50 text-amber-900': statusTone === 'warn',
            'border border-rose-300 bg-rose-50 text-rose-900': statusTone === 'error',
          }"
        >
          {{ statusMessage }}
        </div>

        <div class="mt-4">
          <input
            ref="photoInputRef"
            class="hidden"
            type="file"
            accept="image/*"
            @change="onPhotoSelected"
          >
          <input
            ref="photoCameraInputRef"
            class="hidden"
            type="file"
            accept="image/*"
            capture="environment"
            @change="onPhotoSelected"
          >

          <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <button
              class="flex w-full flex-col items-center justify-center rounded-2xl border-2 border-dashed border-slate-300 bg-white py-10 text-slate-600 hover:border-slate-400 hover:bg-slate-50"
              type="button"
              @click="triggerCameraCapture"
            >
              <svg class="h-10 w-10" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
              <p class="mt-2 text-sm font-semibold">Tirar foto</p>
            </button>

            <button
              class="flex w-full flex-col items-center justify-center rounded-2xl border-2 border-dashed border-slate-300 bg-white py-10 text-slate-600 hover:border-slate-400 hover:bg-slate-50"
              type="button"
              @click="triggerGalleryUpload"
            >
              <svg class="h-10 w-10" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7a2 2 0 012-2h3l1 1h10a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V7z" />
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 14l2-2 2 2 3-3 3 3" />
              </svg>
              <p class="mt-2 text-sm font-semibold">Escolher da galeria</p>
            </button>
          </div>
          <p v-if="draftQueue.length > 0" class="mt-2 text-center text-xs text-slate-400">
            {{ draftQueue.filter(i => i.status === 'ready').length }} prontos na fila
          </p>
        </div>
      </div>
    </section>

    <!-- STEP 2: Custos e Margem -->
    <section v-if="currentStep === 2" class="mx-4 mt-4 space-y-4">
      <div class="surface-card rounded-2xl p-5">
        <h2 class="text-xl font-bold text-slate-900">Dados do veículo</h2>
        
        <div class="mt-4 space-y-3">
          <div class="rounded-xl bg-slate-50 p-4">
            <div class="grid grid-cols-2 gap-4">
              <div
                class="col-span-2 rounded-xl border bg-white p-3"
                :class="editingPlate ? 'border-amber-300' : 'border-slate-200'"
              >
                <p class="text-xs font-semibold uppercase tracking-wider text-slate-500">Placa + candidatos OCR</p>

                <div class="mt-2 flex items-center gap-2 overflow-x-auto pb-1 whitespace-nowrap">
                  <input
                    :value="draft.plate"
                    class="field-input h-9 min-w-[140px] max-w-[180px] shrink-0 uppercase"
                    maxlength="8"
                    placeholder="AAA0A00"
                    @input="onPlateInput"
                  >
                  <button
                    class="shrink-0 rounded-lg border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
                    type="button"
                    :disabled="loadingLookup || !draft.plate"
                    @click="lookupCurrentPlate"
                  >
                    {{ loadingLookup ? 'Consultando...' : 'Consultar novamente' }}
                  </button>
                  <template v-if="suggestedPlateCandidates.length > 0">
                    <span class="text-xs font-semibold uppercase tracking-wider text-amber-700">OCR:</span>
                    <button
                      v-for="candidate in suggestedPlateCandidates"
                      :key="candidate"
                      class="shrink-0 cursor-pointer rounded-lg border px-3 py-1.5 text-xs font-bold transition-colors disabled:cursor-not-allowed disabled:opacity-60"
                      :class="
                        candidate === draft.plate
                          ? 'border-slate-900 bg-slate-900 text-white'
                          : 'border-amber-300 bg-amber-50 text-amber-900 hover:bg-amber-100'
                      "
                      type="button"
                      :disabled="loadingLookup"
                      @click="applyPlateCandidate(candidate)"
                    >
                      {{ loadingLookup && selectingPlateCandidate === candidate ? 'Consultando...' : candidate }}
                    </button>
                  </template>
                </div>

                <p v-if="hasAmbiguousPlateCandidates" class="mt-1 text-xs font-semibold text-amber-700">
                  Existem candidatos muito parecidos. Confirme antes da primeira consulta FIPE.
                </p>
                <p v-if="activeQueueTimingHint" class="mt-1 text-xs font-semibold text-slate-500">
                  {{ activeQueueTimingHint }}
                </p>
                <p v-if="ocrLearningHint" class="mt-1 text-xs font-semibold text-slate-500">
                  {{ ocrLearningHint }}
                </p>
              </div>

              <div class="col-span-2 rounded-xl border border-slate-200 bg-white p-3">
                <div class="grid grid-cols-[1fr_auto] gap-3">
                  <div>
                    <div class="flex items-center justify-between gap-2">
                      <p class="text-xs font-semibold uppercase tracking-wider text-slate-500">Marca/Modelo</p>
                      <button
                        class="rounded-lg border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-100"
                        type="button"
                        @click="toggleBrandModelEdit"
                      >
                        {{ editingBrandModel ? 'Confirmar' : 'Editar' }}
                      </button>
                    </div>
                    <p class="mt-1 text-lg font-bold text-slate-900">{{ draft.brand }} {{ draft.model }}</p>
                    <div v-if="editingBrandModel" class="mt-2 grid grid-cols-2 gap-2">
                      <input
                        v-model="draft.brand"
                        class="field-input"
                        placeholder="Marca"
                      >
                      <input
                        v-model="draft.model"
                        class="field-input"
                        placeholder="Modelo"
                      >
                    </div>
                  </div>
                  <div class="min-w-[84px] text-right">
                    <p class="text-xs font-semibold uppercase tracking-wider text-slate-500">Ano</p>
                    <p class="mt-1 text-lg font-bold text-slate-900">{{ draft.year || '-' }}</p>
                  </div>
                </div>
              </div>
              <div class="col-span-2">
                <div class="flex items-center justify-between">
                  <div>
                    <p class="text-xs font-semibold uppercase tracking-wider text-slate-500">Valor FIPE</p>
                    <p class="mt-1 text-2xl font-bold text-slate-900">{{ formatMoney(draft.fipeValue) }}</p>
                  </div>
                  <button
                    class="rounded-lg border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-100"
                    type="button"
                    @click="toggleFipeEdit"
                  >
                    {{ editingFipe ? 'Confirmar' : 'Editar' }}
                  </button>
                </div>
                <div v-if="editingFipe" class="mt-2">
                  <input
                    v-model.number="draft.fipeValue"
                    class="field-input"
                    type="number"
                    min="0"
                    step="100"
                  >
                </div>
              </div>
            </div>
          </div>

          <div class="rounded-xl border border-slate-200 bg-white p-4">
            <div class="flex items-center justify-between">
              <div>
                <p class="text-xs font-semibold uppercase tracking-wider text-slate-500">Margem alvo</p>
                <p class="mt-1 text-xl font-bold text-slate-900">{{ formatMoney(targetMarginValue) }}</p>
              </div>
              <button
                class="rounded-lg border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-100"
                type="button"
                @click="toggleMarginEdit"
              >
                {{ editingMargin ? 'Confirmar' : 'Editar' }}
              </button>
            </div>
            <div v-if="editingMargin" class="mt-3">
              <input
                v-model.number="targetMarginValue"
                class="field-input"
                type="number"
                min="0"
                step="500"
              >
              <button
                class="mt-2 w-full rounded-lg border border-emerald-300 bg-emerald-50 py-2 text-xs font-semibold text-emerald-700 hover:bg-emerald-100"
                type="button"
                @click="applySuggestedMargin"
              >
                Usar margem sugerida: {{ formatMoney(suggestedMarginValue) }}
              </button>
            </div>
          </div>

          <div class="rounded-xl border border-slate-200 bg-white p-4">
            <p class="text-xs font-semibold uppercase tracking-wider text-slate-500">Tipo de Monta</p>
            <div class="mt-3 flex gap-3">
              <button
                class="flex-1 rounded-lg border-2 px-4 py-3 text-sm font-bold transition-colors"
                :class="draft.mountClass === 'pequena' ? 'border-slate-900 bg-slate-900 text-white' : 'border-slate-300 bg-white text-slate-700 hover:bg-slate-50'"
                type="button"
                @click="draft.mountClass = 'pequena'"
              >
                Pequena Monta
                <span class="block text-xs font-normal opacity-80">Venda 5% abaixo FIPE</span>
              </button>
              <button
                class="flex-1 rounded-lg border-2 px-4 py-3 text-sm font-bold transition-colors"
                :class="draft.mountClass === 'media' ? 'border-slate-900 bg-slate-900 text-white' : 'border-slate-300 bg-white text-slate-700 hover:bg-slate-50'"
                type="button"
                @click="draft.mountClass = 'media'"
              >
                Média Monta
                <span class="block text-xs font-normal opacity-80">Venda 20% abaixo FIPE</span>
              </button>
            </div>
          </div>

          <div class="rounded-xl border border-slate-200 bg-white p-4">
            <div class="mb-3 flex items-center justify-between">
              <h3 class="text-sm font-bold text-slate-900">Custos</h3>
              <button
                class="rounded-lg border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-100"
                type="button"
                @click="toggleCostAdd"
              >
                {{ addingCost ? 'Cancelar' : '+ Adicionar' }}
              </button>
            </div>

            <div v-if="addingCost" class="mb-4 space-y-2 rounded-lg bg-slate-50 p-3">
              <select v-model="newCostType" class="field-input" @change="onCostTypeChange">
                <option v-for="option in costTypeOptions" :key="option.value" :value="option.value">
                  {{ option.label }}
                </option>
              </select>
              <input v-model.number="newCostAmount" class="field-input" type="number" min="0" step="50" placeholder="Valor">
              <input
                v-if="newCostType === 'outros'"
                v-model="newCostOtherLabel"
                class="field-input"
                placeholder="Descrição"
              >
              <button
                class="w-full rounded-lg bg-slate-900 py-2 text-sm font-semibold text-white hover:bg-slate-800"
                type="button"
                @click="addCostItem"
              >
                Confirmar
              </button>
            </div>

            <div class="space-y-2">
              <div
                v-for="cost in draft.costs"
                :key="cost.id"
                class="rounded-lg bg-slate-50 p-3"
              >
                <div class="flex items-center justify-between">
                  <div class="flex-1">
                    <p class="text-sm font-semibold text-slate-700">{{ cost.label }}</p>
                    <p v-if="editingCostId !== cost.id" class="text-xs text-slate-500">{{ formatMoney(cost.amount) }}</p>
                  </div>
                  <div class="flex gap-2">
                    <template v-if="editingCostId !== cost.id">
                      <button
                        class="rounded-lg border border-slate-300 px-2 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-100"
                        type="button"
                        @click="startEditCost(cost)"
                      >
                        Editar
                      </button>
                      <button
                        class="rounded-lg border border-rose-300 px-2 py-1 text-xs font-semibold text-rose-700 hover:bg-rose-50"
                        type="button"
                        @click="removeCostItem(cost.id)"
                      >
                        Remover
                      </button>
                    </template>
                    <template v-else>
                      <button
                        class="rounded-lg border border-emerald-300 px-2 py-1 text-xs font-semibold text-emerald-700 hover:bg-emerald-50"
                        type="button"
                        @click="confirmEditCost(cost.id)"
                      >
                        Confirmar
                      </button>
                      <button
                        class="rounded-lg border border-rose-300 px-2 py-1 text-xs font-semibold text-rose-700 hover:bg-rose-50"
                        type="button"
                        @click="cancelEditCost"
                      >
                        Cancelar
                      </button>
                    </template>
                  </div>
                </div>
                <div v-if="editingCostId === cost.id" class="mt-2">
                  <input
                    v-model.number="editingCostAmount"
                    class="field-input"
                    type="number"
                    min="0"
                    step="50"
                    placeholder="Valor"
                  >
                </div>
              </div>
            </div>

            <div class="mt-3 rounded-lg bg-slate-900 p-3 text-white">
              <p class="text-xs font-semibold uppercase tracking-wider opacity-80">Total de custos</p>
              <p class="mt-1 text-xl font-bold">{{ formatMoney(totalCosts) }}</p>
            </div>
          </div>

          <div class="rounded-xl border-2 border-emerald-400 bg-emerald-50 p-4">
            <p class="text-xs font-semibold uppercase tracking-wider text-emerald-700">Valor máximo no leilão</p>
            <p class="mt-1 text-3xl font-bold text-emerald-800">{{ formatMoney(maxAuctionBid) }}</p>
            <p class="mt-2 text-xs text-emerald-700">FIPE - Margem - Custos</p>
          </div>
        </div>

        <div class="mt-6 flex gap-3">
          <button
            class="flex-1 rounded-xl border border-slate-300 py-3 text-base font-bold text-slate-700 hover:bg-slate-100"
            type="button"
            @click="goToStep(1)"
          >
            Voltar
          </button>
          <button
            class="flex-1 rounded-xl bg-slate-900 py-3 text-base font-bold text-white hover:bg-slate-800"
            type="button"
            @click="toggleDetailsBeforeSave"
          >
            {{ showingDetails ? 'Salvar' : 'Detalhes' }}
          </button>
        </div>

        <div v-if="showingDetails" class="mt-4 space-y-3 rounded-xl border border-slate-200 bg-white p-4">
          <div>
            <label class="field-label">Quanto pretende pagar no leilão (opcional)</label>
            <input v-model.number="draft.purchaseValue" class="field-input" type="number" min="0" step="100">
          </div>

          <div class="rounded-lg bg-slate-50 p-3">
            <p class="text-xs font-semibold uppercase tracking-wider text-slate-500">Resultado projetado</p>
            <p class="mt-2 text-sm">Lucro estimado: <span class="font-bold">{{ formatMoney(projectedProfit) }}</span></p>
            <p class="text-sm">
              Distância da meta:
              <span class="font-bold" :class="marginGapValue >= 0 ? 'text-emerald-700' : 'text-rose-700'">
                {{ formatMoney(marginGapValue) }}
              </span>
            </p>
            <p class="text-sm">Margem %: <span class="font-bold">{{ formatPercent(projectedMarginPercent) }}</span></p>
          </div>

          <div>
            <label class="field-label">Observações</label>
            <textarea
              v-model="draft.notes"
              class="field-input min-h-24"
              placeholder="Detalhes do carro..."
            />
          </div>

          <button
            class="w-full rounded-xl bg-emerald-600 py-3 text-base font-bold text-white hover:bg-emerald-700 disabled:opacity-50"
            type="button"
            :disabled="!canSave"
            @click="saveAndGoToStep3"
          >
            Confirmar e salvar
          </button>
        </div>
      </div>
    </section>

    <!-- STEP 3: Sucesso -->
    <section v-if="currentStep === 3" class="mx-4 mt-4 space-y-4">
      <div v-if="justSaved" class="surface-card rounded-2xl p-5 text-center">
        <div class="mx-auto flex h-20 w-20 items-center justify-center rounded-full bg-emerald-100">
          <svg class="h-10 w-10 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <h2 class="mt-4 text-2xl font-bold text-slate-900">Salvo com sucesso!</h2>
        <p class="mt-2 text-sm text-slate-600">O carro foi registrado no dispositivo</p>

        <div class="mt-6 space-y-3">
          <button
            class="w-full rounded-xl border-2 border-slate-900 bg-slate-900 py-3 text-base font-bold text-white hover:bg-slate-800"
            type="button"
            @click="startNewCar"
          >
            Cadastrar novo carro
          </button>
          <button
            class="w-full rounded-xl border-2 border-slate-300 py-3 text-base font-bold text-slate-700 hover:bg-slate-100"
            type="button"
            @click="viewSavedCars"
          >
            Ver lista de carros salvos
          </button>
        </div>
      </div>

      <div v-if="showSavedCarsList" class="surface-card rounded-2xl p-5">
        <div class="mb-4 flex items-center justify-between">
          <h2 class="text-xl font-bold text-slate-900">Carros salvos</h2>
          <span class="text-xs font-semibold uppercase tracking-wider text-slate-500">
            {{ localCars.length }} registros
          </span>
        </div>

        <div v-if="!indexedDb.isSupported" class="rounded-xl border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900">
          IndexedDB não está disponível neste navegador.
        </div>

        <div v-else-if="localCars.length === 0" class="rounded-xl border border-slate-200 bg-white/70 px-3 py-5 text-center text-sm text-slate-600">
          Nenhum carro salvo ainda.
        </div>

        <div v-else class="space-y-3">
          <article
            v-for="item in localCars"
            :key="item.id"
            class="rounded-xl border-2 bg-white p-4 transition-colors"
            :class="item.id === bestMarginCarId ? 'border-emerald-400' : 'border-slate-200'"
          >
            <div class="flex items-start justify-between gap-3">
              <div v-if="item.photoDataUrl" class="shrink-0">
                <img
                  :src="item.photoDataUrl"
                  alt="Foto"
                  class="h-16 w-16 rounded-xl object-cover"
                >
              </div>
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2">
                  <p class="text-base font-bold text-slate-900">{{ item.plate || 'SEM PLACA' }}</p>
                  <span
                    v-if="item.id === bestMarginCarId"
                    class="rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-bold text-emerald-700"
                  >Melhor margem</span>
                </div>
                <p class="text-sm text-slate-600">{{ item.brand }} {{ item.model }}</p>
                <p class="mt-1 text-xs text-slate-500">{{ formatDate(item.updatedAt) }}</p>
                <div class="mt-2 flex flex-wrap gap-3 text-xs">
                  <span class="text-slate-600">Compra: <span class="font-semibold">{{ formatMoney(item.purchaseValue) }}</span></span>
                  <span class="text-slate-600">FIPE: <span class="font-semibold">{{ formatMoney(item.fipeValue) }}</span></span>
                  <span v-if="item.mountClass" class="rounded-full px-2 py-0.5 text-xs font-semibold" :class="item.mountClass === 'pequena' ? 'bg-blue-100 text-blue-700' : 'bg-purple-100 text-purple-700'">
                    {{ item.mountClass === 'pequena' ? 'Pequena Monta (-5%)' : 'Média Monta (-20%)' }}
                  </span>
                </div>
                <div class="mt-2">
                  <p class="text-xs font-semibold uppercase tracking-wider text-slate-500">Lucro projetado</p>
                  <p
                    class="text-2xl font-bold"
                    :class="(item.summary?.expectedProfit ?? 0) >= 0 ? 'text-emerald-700' : 'text-rose-600'"
                  >{{ formatMoney(item.summary?.expectedProfit ?? 0) }}</p>
                  <p class="text-xs text-slate-500">{{ formatPercent(item.summary?.marginPercent ?? 0) }} da FIPE</p>
                </div>
              </div>

              <div class="flex shrink-0 gap-2">
                <button
                  class="rounded-lg border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-100"
                  type="button"
                  @click="editSavedCar(item)"
                >
                  Editar
                </button>
                <button
                  class="rounded-lg border border-rose-300 px-3 py-2 text-xs font-semibold text-rose-700 hover:bg-rose-50"
                  type="button"
                  @click="removeLocal(item.id)"
                >
                  Excluir
                </button>
              </div>
            </div>
          </article>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useAuctionCarsApi } from '~/composables/useAuctionCarsApi'
import { useIndexedAuctionCars } from '~/composables/useIndexedAuctionCars'
import { calculateAuctionSummary, calculateSaleValue, calculateTotalCosts, normalizePlate } from '@core/shared/valuation'
import type { AuctionCarRecord, CostItem, PlateFipeQuotaInfo } from '@core/shared/types/auction'

type QueueProcessingStage = 'ocr' | 'fipe' | 'done' | 'error'

type OcrCandidateDetail = {
  plate: string
  confidence: number
  bbox: [number, number, number, number] | null
}

type DraftQueueItem = {
  draft: DraftState
  ocrProcessed: boolean
  ocrSuccess: boolean
  plateCandidates: string[]
  rawPlateCandidates: string[]
  plateCandidateDetails: OcrCandidateDetail[]
  needsPlateConfirmation: boolean
  targetMarginValue: number
  status: 'processing' | 'ready' | 'error'
  processingStage: QueueProcessingStage
  processingStartedAt: number | null
  processingFinishedAt: number | null
  processingDurationMs: number | null
  ocrDurationMs: number | null
  fipeDurationMs: number | null
  ocrRequestId: string
  ocrTimingsMs: Record<string, number>
  errorMessage?: string
}

type DraftState = {
  id: string
  plate: string
  photoDataUrl?: string
  brand: string
  model: string
  year: number | null
  fipeValue: number
  purchaseValue: number
  costs: CostItem[]
  targetMarginPercent: number
  mountClass: 'pequena' | 'media'
  notes: string
  createdAt: string | null
}

type CostOption = {
  value: string
  label: string
  defaultAmount?: number
}

type OcrFeedbackProfile = {
  updatedAt: string
  totalConfirmations: number
  correctedConfirmations: number
  pairWins: Record<string, number>
  positionCorrections: Record<string, number>
}

const OCR_FEEDBACK_PROMOTE_THRESHOLD = 2

const createId = () => {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return Math.random().toString(36).slice(2, 12)
}

const createEmptyOcrFeedbackProfile = (): OcrFeedbackProfile => ({
  updatedAt: new Date(0).toISOString(),
  totalConfirmations: 0,
  correctedConfirmations: 0,
  pairWins: {},
  positionCorrections: {},
})

const costTypeOptions: CostOption[] = [
  { value: 'leilao', label: 'Leilao', defaultAmount: 800 },
  { value: 'documentacao', label: 'Documentacao' },
  { value: 'pintura', label: 'Pintura' },
  { value: 'mecanica', label: 'Mecanica' },
  { value: 'suspensao', label: 'Suspensao' },
  { value: 'vidros', label: 'Vidros' },
  { value: 'portas', label: 'Portas' },
  { value: 'eletrica', label: 'Eletrica' },
  { value: 'outros', label: 'Outros' },
]

const suggestMarginByFipe = (fipeValue: number) => {
  if (!Number.isFinite(fipeValue) || fipeValue <= 0) return 10000
  if (fipeValue <= 30000) return 5000
  if (fipeValue <= 80000) return 10000
  if (fipeValue <= 120000) return 30000
  if (fipeValue <= 160000) return 40000

  const extraBlocks = Math.ceil((fipeValue - 160000) / 40000)
  return 40000 + extraBlocks * 10000
}

const getDefaultCosts = (): CostItem[] => [{ id: createId(), label: 'Leilao', amount: 800 }]

const createEmptyDraft = (): DraftState => ({
  id: createId(),
  plate: '',
  photoDataUrl: '',
  brand: '',
  model: '',
  year: null,
  fipeValue: 0,
  purchaseValue: 0,
  costs: getDefaultCosts(),
  targetMarginPercent: 0,
  mountClass: 'pequena',
  notes: '',
  createdAt: null,
})

const moneyFormatter = new Intl.NumberFormat('pt-BR', {
  style: 'currency',
  currency: 'BRL',
  maximumFractionDigits: 2,
})

const percentFormatter = new Intl.NumberFormat('pt-BR', {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
})

const dateFormatter = new Intl.DateTimeFormat('pt-BR', {
  day: '2-digit',
  month: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
})

const draft = reactive<DraftState>(createEmptyDraft())
const draftQueue = ref<DraftQueueItem[]>([])
const localCars = ref<AuctionCarRecord[]>([])
const loadingLookup = ref(false)
const statusMessage = ref('')
const statusTone = ref<'ok' | 'warn' | 'error'>('ok')
const plateCandidates = ref<string[]>([])
const rawPlateCandidates = ref<string[]>([])
const plateCandidateDetails = ref<OcrCandidateDetail[]>([])
const ocrBestScore = ref(0)
const ocrSecondScore = ref(0)
const plateFipeQuota = useState<PlateFipeQuotaInfo | null>('plateFipeQuota', () => null)
const plateFipeQuotaLoading = useState<boolean>('plateFipeQuotaLoading', () => false)
const plateFipeQuotaError = useState<string>('plateFipeQuotaError', () => '')
const selectingPlateCandidate = ref<string | null>(null)
const processingClockMs = ref(Date.now())
let processingClockInterval: ReturnType<typeof setInterval> | null = null
const ocrFeedbackProfile = ref<OcrFeedbackProfile>(createEmptyOcrFeedbackProfile())

const targetMarginValue = ref(10000)
const marginWasEdited = ref(false)

const newCostType = ref<string>('documentacao')
const newCostAmount = ref<number>(0)
const newCostOtherLabel = ref('')

// Step state
const currentStep = ref(1)
const ocrProcessed = ref(false)
const ocrSuccess = ref(false)
const editingPlate = ref(false)
const editingMargin = ref(false)
const editingFipe = ref(false)
const editingBrandModel = ref(false)
const addingCost = ref(false)
const editingCostId = ref<string | null>(null)
const editingCostAmount = ref<number>(0)
const showingDetails = ref(false)
const showSavedCarsList = ref(false)
const justSaved = ref(false)
const activeQueueId = ref<string | null>(null)
const queuePreviewIndex = ref<number | null>(null)
const photoInputRef = ref<HTMLInputElement | null>(null)
const photoCameraInputRef = ref<HTMLInputElement | null>(null)

const indexedDb = useIndexedAuctionCars()
const api = useAuctionCarsApi()

const savedCarsCount = useState<number>('savedCarsCount', () => 0)
const triggerSavedCars = useState<number>('triggerSavedCars', () => 0)
const triggerStep1 = useState<number>('triggerStep1', () => 0)

watch(triggerSavedCars, () => {
  justSaved.value = false
  currentStep.value = 3
  showSavedCarsList.value = true
  window.scrollTo({ top: 0, behavior: 'smooth' })
})

watch(triggerStep1, () => {
  goToStep(1)
})


const totalCosts = computed(() => calculateTotalCosts(draft.costs))
const suggestedMarginValue = computed(() => suggestMarginByFipe(draft.fipeValue))

const maxAuctionBid = computed(() => {
  const value = Number(draft.fipeValue) - Number(targetMarginValue.value) - Number(totalCosts.value)
  return Math.max(0, Number.isFinite(value) ? value : 0)
})

const chosenBidValue = computed(() => {
  const value = Number(draft.purchaseValue)
  return Number.isFinite(value) && value > 0 ? value : 0
})

const bidUsedInProjection = computed(() => (chosenBidValue.value > 0 ? chosenBidValue.value : maxAuctionBid.value))

const projectedProfit = computed(() => {
  const saleValue = calculateSaleValue(Number(draft.fipeValue), draft.mountClass)
  return saleValue - (bidUsedInProjection.value + Number(totalCosts.value))
})

const projectedMarginPercent = computed(() => {
  const saleValue = calculateSaleValue(Number(draft.fipeValue), draft.mountClass)
  return saleValue > 0 ? (projectedProfit.value / saleValue) * 100 : 0
})

const marginGapValue = computed(() => projectedProfit.value - Number(targetMarginValue.value || 0))

const canProceedToStep2 = computed(() => {
  return Boolean(draft.photoDataUrl && ocrProcessed.value && (ocrSuccess.value || (draft.plate && draft.brand && draft.fipeValue > 0)))
})

const canSave = computed(() => {
  return draft.fipeValue > 0 && draft.costs.length > 0 && Boolean(draft.plate || draft.brand || draft.model)
})

const bestMarginCarId = computed(() => {
  if (localCars.value.length === 0) return null
  return localCars.value.reduce((best, car) => {
    const bestProfit = best?.summary?.expectedProfit ?? -Infinity
    const carProfit = car?.summary?.expectedProfit ?? -Infinity
    return carProfit > bestProfit ? car : best
  }, localCars.value[0]).id
})

const isLikelyPlateAmbiguous = (candidates: string[]) => {
  const normalized = Array.from(new Set(candidates.map((item) => normalizePlate(item)).filter(Boolean)))
  if (normalized.length < 2) return false

  const byPrefix = new Map<string, number>()
  for (const candidate of normalized) {
    if (candidate.length !== 7) continue
    const prefix = candidate.slice(0, 6)
    byPrefix.set(prefix, (byPrefix.get(prefix) || 0) + 1)
  }

  for (const count of byPrefix.values()) {
    if (count > 1) return true
  }

  return false
}

const suggestedPlateCandidates = computed(() => plateCandidates.value.slice(0, 5))
const hasAmbiguousPlateCandidates = computed(() => isLikelyPlateAmbiguous(plateCandidates.value))
const queuePreviewItem = computed(() => {
  if (queuePreviewIndex.value === null) return null
  return draftQueue.value[queuePreviewIndex.value] || null
})
const queuePreviewCandidates = computed(() => {
  const item = queuePreviewItem.value
  if (!item) return []
  const source = item.plateCandidates.length > 0 ? item.plateCandidates : [item.draft.plate]
  return Array.from(new Set(source.map((value) => normalizePlate(value || '')).filter(Boolean))).slice(0, 5)
})

const pairKey = (fromPlate: string, toPlate: string) => `${fromPlate}>${toPlate}`

const readPairDelta = (fromPlate: string, toPlate: string) => {
  const wins = ocrFeedbackProfile.value.pairWins[pairKey(fromPlate, toPlate)] || 0
  const losses = ocrFeedbackProfile.value.pairWins[pairKey(toPlate, fromPlate)] || 0
  return wins - losses
}

const readPositionCorrectionScore = (fromPlate: string, toPlate: string) => {
  if (!fromPlate || !toPlate || fromPlate.length !== toPlate.length) return 0

  let score = 0
  for (let index = 0; index < fromPlate.length; index += 1) {
    const fromChar = fromPlate[index]
    const toChar = toPlate[index]
    if (fromChar === toChar) continue

    const positiveKey = `${index}:${fromChar}>${toChar}`
    const negativeKey = `${index}:${toChar}>${fromChar}`
    score += Number(ocrFeedbackProfile.value.positionCorrections[positiveKey] || 0)
    score -= Number(ocrFeedbackProfile.value.positionCorrections[negativeKey] || 0)
  }

  return score
}

const prioritizeCandidatesByFeedback = (candidates: string[]) => {
  const normalized = Array.from(new Set(candidates.map((item) => normalizePlate(item || '')).filter(Boolean)))
  if (normalized.length <= 1) return normalized

  const baseline = normalized[0]
  const scored = normalized.map((plate, index) => {
    if (index === 0) {
      return {
        plate,
        index,
        score: 0,
      }
    }

    const pairScore = readPairDelta(baseline, plate) * 3
    const positionScore = readPositionCorrectionScore(baseline, plate)

    return {
      plate,
      index,
      score: pairScore + positionScore,
    }
  })

  const sorted = [...scored].sort((left, right) => {
    if (right.score !== left.score) return right.score - left.score
    return left.index - right.index
  })

  const top = sorted[0]
  if (!top || top.plate === baseline) return normalized
  if (top.score < OCR_FEEDBACK_PROMOTE_THRESHOLD) return normalized

  return sorted.map((entry) => entry.plate)
}

const countPositionCorrections = computed(() => {
  return Object.values(ocrFeedbackProfile.value.positionCorrections).reduce(
    (total, value) => total + Number(value || 0),
    0,
  )
})

const ocrLearningHint = computed(() => {
  const total = Number(ocrFeedbackProfile.value.totalConfirmations || 0)
  if (total <= 0) return ''
  return `Aprendizado compartilhado ativo: ${total} confirmacoes (${countPositionCorrections.value} correcoes).`
})

const activeQueueItem = computed(() => {
  if (!activeQueueId.value) return null
  return draftQueue.value.find((item) => item.draft.id === activeQueueId.value) || null
})

const markQueueProcessingStarted = (item: DraftQueueItem) => {
  const startedAt = Date.now()
  item.status = 'processing'
  item.processingStage = 'ocr'
  item.processingStartedAt = startedAt
  item.processingFinishedAt = null
  item.processingDurationMs = null
  item.ocrDurationMs = null
  item.fipeDurationMs = null
  item.ocrTimingsMs = {}
  item.rawPlateCandidates = []
  item.plateCandidates = []
  item.plateCandidateDetails = []
  item.errorMessage = undefined
}

const markQueueProcessingFinished = (item: DraftQueueItem, status: 'ready' | 'error') => {
  const finishedAt = Date.now()
  item.processingFinishedAt = finishedAt
  item.processingDurationMs = item.processingStartedAt ? Math.max(0, finishedAt - item.processingStartedAt) : null
  item.processingStage = status === 'ready' ? 'done' : 'error'
  item.status = status
}

const getQueueItemElapsedMs = (item: DraftQueueItem) => {
  if (item.status === 'processing' && item.processingStartedAt) {
    return Math.max(0, processingClockMs.value - item.processingStartedAt)
  }
  return Math.max(0, Number(item.processingDurationMs || 0))
}

const formatElapsedMs = (milliseconds: number | null | undefined) => {
  const value = Number(milliseconds || 0)
  if (!Number.isFinite(value) || value <= 0) return '0.0s'
  const seconds = value / 1000
  return `${seconds >= 10 ? seconds.toFixed(1) : seconds.toFixed(2)}s`
}

const queueItemStageLabel = (item: DraftQueueItem) => {
  if (item.processingStage === 'fipe') return 'FIPE'
  if (item.processingStage === 'error') return 'Erro'
  if (item.processingStage === 'done') return 'Concluido'
  return 'OCR'
}

const queueItemDurationLabel = (item: DraftQueueItem) => {
  if (item.status === 'processing') {
    return `${queueItemStageLabel(item)} ${formatElapsedMs(getQueueItemElapsedMs(item))}`
  }
  if (item.processingDurationMs) {
    const parts = [`Total ${formatElapsedMs(item.processingDurationMs)}`]
    if (item.ocrDurationMs) parts.push(`OCR ${formatElapsedMs(item.ocrDurationMs)}`)
    if (item.fipeDurationMs) parts.push(`FIPE ${formatElapsedMs(item.fipeDurationMs)}`)
    return parts.join(' | ')
  }
  return ''
}

const activeQueueTimingHint = computed(() => {
  const item = activeQueueItem.value
  if (!item) return ''
  return queueItemDurationLabel(item)
})

const refreshOcrFeedbackProfile = async () => {
  try {
    const response = await api.getPlateFeedbackProfile()
    ocrFeedbackProfile.value = response.profile || createEmptyOcrFeedbackProfile()
  } catch {
    // fallback para perfil em memoria (vazio)
  }
}

const normalizeBbox = (bbox: unknown): [number, number, number, number] | null => {
  if (!Array.isArray(bbox) || bbox.length !== 4) return null
  const parsed = bbox.map((value) => Math.round(Number(value)))
  if (parsed.some((value) => !Number.isFinite(value))) return null
  const [x1, y1, x2, y2] = parsed
  if (x2 <= x1 || y2 <= y1) return null
  return [x1, y1, x2, y2]
}

const buildCandidateDetails = (candidates: Array<{ plate?: string; confidence?: number; bbox?: unknown }>) => {
  const map = new Map<string, OcrCandidateDetail>()
  const order: string[] = []

  for (const candidate of candidates) {
    const plate = normalizePlate(candidate?.plate || '')
    if (!plate) continue
    const confidence = Number(candidate?.confidence ?? 0)
    const bbox = normalizeBbox(candidate?.bbox)
    if (!map.has(plate)) {
      order.push(plate)
      map.set(plate, {
        plate,
        confidence,
        bbox,
      })
      continue
    }

    const existing = map.get(plate)
    if (!existing) continue
    if (confidence > existing.confidence) {
      map.set(plate, {
        plate,
        confidence,
        bbox: bbox || existing.bbox,
      })
    }
  }

  return order
    .map((plate) => map.get(plate))
    .filter((item): item is OcrCandidateDetail => Boolean(item))
}

const reorderCandidateDetails = (orderedPlates: string[], details: OcrCandidateDetail[]) => {
  const byPlate = new Map(details.map((item) => [item.plate, item] as const))
  const prioritized: OcrCandidateDetail[] = []

  for (const plate of orderedPlates) {
    const detail = byPlate.get(plate)
    if (!detail) continue
    prioritized.push(detail)
    byPlate.delete(plate)
  }

  for (const detail of byPlate.values()) {
    prioritized.push(detail)
  }

  return prioritized
}

const applyFeedbackProfileDelta = (recognizedPlate: string, confirmedPlate: string) => {
  const next: OcrFeedbackProfile = {
    ...ocrFeedbackProfile.value,
    pairWins: { ...ocrFeedbackProfile.value.pairWins },
    positionCorrections: { ...ocrFeedbackProfile.value.positionCorrections },
  }

  next.totalConfirmations = Number(next.totalConfirmations || 0) + 1
  next.updatedAt = new Date().toISOString()

  if (recognizedPlate && recognizedPlate !== confirmedPlate) {
    next.correctedConfirmations = Number(next.correctedConfirmations || 0) + 1
    const pairWinKey = pairKey(recognizedPlate, confirmedPlate)
    next.pairWins[pairWinKey] = Number(next.pairWins[pairWinKey] || 0) + 1

    if (recognizedPlate.length === confirmedPlate.length) {
      for (let index = 0; index < recognizedPlate.length; index += 1) {
        const fromChar = recognizedPlate[index]
        const toChar = confirmedPlate[index]
        if (fromChar === toChar) continue
        const correctionKey = `${index}:${fromChar}>${toChar}`
        next.positionCorrections[correctionKey] = Number(next.positionCorrections[correctionKey] || 0) + 1
      }
    }
  }

  ocrFeedbackProfile.value = next
}

const resolveCandidateDetailForPlate = (plate: string) => {
  const normalized = normalizePlate(plate || '')
  if (!normalized) return null
  return plateCandidateDetails.value.find((item) => item.plate === normalized) || null
}

const buildPlateCropPayload = async (bbox: [number, number, number, number] | null) => {
  if (!bbox || !draft.photoDataUrl) {
    return {
      plateCropBase64: undefined,
      imageSize: undefined,
    }
  }

  try {
    const image = await loadImageElement(draft.photoDataUrl)
    const width = image.naturalWidth || image.width
    const height = image.naturalHeight || image.height
    if (!width || !height) {
      return {
        plateCropBase64: undefined,
        imageSize: undefined,
      }
    }

    const [bx1, by1, bx2, by2] = bbox
    const rawW = Math.max(1, bx2 - bx1)
    const rawH = Math.max(1, by2 - by1)
    const pad = Math.max(8, Math.round(Math.max(rawW, rawH) * 0.16))

    const x1 = Math.max(0, bx1 - pad)
    const y1 = Math.max(0, by1 - pad)
    const x2 = Math.min(width, bx2 + pad)
    const y2 = Math.min(height, by2 + pad)
    const cropW = Math.max(1, x2 - x1)
    const cropH = Math.max(1, y2 - y1)

    const maxSide = 640
    const scale = Math.min(1, maxSide / Math.max(cropW, cropH))
    const targetW = Math.max(1, Math.round(cropW * scale))
    const targetH = Math.max(1, Math.round(cropH * scale))

    const canvas = document.createElement('canvas')
    canvas.width = targetW
    canvas.height = targetH

    const context = canvas.getContext('2d')
    if (!context) {
      return {
        plateCropBase64: undefined,
        imageSize: { width, height },
      }
    }

    context.drawImage(image, x1, y1, cropW, cropH, 0, 0, targetW, targetH)

    return {
      plateCropBase64: canvas.toDataURL('image/jpeg', 0.9),
      imageSize: { width, height },
    }
  } catch {
    return {
      plateCropBase64: undefined,
      imageSize: undefined,
    }
  }
}

const registerOcrConfirmation = async (payload: {
  recognizedPlate?: string
  confirmedPlate: string
  candidates?: string[]
  source: 'step2' | 'queue-preview'
  requestId?: string
  timingsMs?: Record<string, number>
}) => {
  const confirmedPlate = normalizePlate(payload.confirmedPlate || '')
  if (!confirmedPlate) return

  const recognizedPlate = normalizePlate(payload.recognizedPlate || '')
  const candidates = Array.from(
    new Set((payload.candidates || []).map((item) => normalizePlate(item || '')).filter(Boolean)),
  )

  const detail =
    resolveCandidateDetailForPlate(confirmedPlate) ||
    resolveCandidateDetailForPlate(recognizedPlate) ||
    null
  const cropPayload = await buildPlateCropPayload(detail?.bbox || null)

  const response = await api.submitPlateFeedback({
    recognizedPlate,
    confirmedPlate,
    candidates,
    source: payload.source,
    requestId: payload.requestId,
    timingsMs: payload.timingsMs,
    plateCropBase64: cropPayload.plateCropBase64,
    bbox: detail?.bbox || null,
    imageSize: cropPayload.imageSize,
  })

  if (response?.skipped) return

  applyFeedbackProfileDelta(recognizedPlate, confirmedPlate)
  await refreshOcrFeedbackProfile()
}

const resolvePrimaryPlateCandidate = (candidates: string[], fallback = '') => {
  const firstCandidate = normalizePlate(candidates[0] || '')
  if (firstCandidate) return firstCandidate
  return normalizePlate(fallback || '')
}

watch(
  () => draft.fipeValue,
  () => {
    if (!marginWasEdited.value || targetMarginValue.value <= 0) {
      targetMarginValue.value = suggestedMarginValue.value
    }
  },
)

const setStatus = (message: string, tone: 'ok' | 'warn' | 'error' = 'ok') => {
  statusMessage.value = message
  statusTone.value = tone
}

const syncActiveQueueDraft = () => {
  if (!activeQueueId.value) return
  const index = draftQueue.value.findIndex((item) => item.draft.id === activeQueueId.value)
  if (index === -1) return

  const current = draftQueue.value[index]
  current.draft = {
    ...draft,
    costs: draft.costs.map((cost) => ({ ...cost })),
  }
  current.targetMarginValue = targetMarginValue.value
  current.plateCandidates = [...plateCandidates.value]
  current.rawPlateCandidates = [...rawPlateCandidates.value]
  current.plateCandidateDetails = plateCandidateDetails.value.map((item) => ({ ...item }))
  current.ocrProcessed = ocrProcessed.value
  current.ocrSuccess = ocrSuccess.value
}

const applyQuotaInfo = (quota?: PlateFipeQuotaInfo) => {
  if (!quota) return
  plateFipeQuota.value = quota
  plateFipeQuotaError.value = ''
}

const formatMoney = (value: number) => moneyFormatter.format(Number(value) || 0)
const formatPercent = (value: number) => `${percentFormatter.format(Number(value) || 0)}%`
const formatDate = (value: string) => dateFormatter.format(new Date(value))

// Step navigation
const goToStep = (step: number) => {
  currentStep.value = step
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

const triggerGalleryUpload = () => {
  photoInputRef.value?.click()
}

const triggerCameraCapture = () => {
  photoCameraInputRef.value?.click()
}

const clearPhoto = () => {
  draft.photoDataUrl = ''
  ocrProcessed.value = false
  ocrSuccess.value = false
  plateCandidates.value = []
  rawPlateCandidates.value = []
  plateCandidateDetails.value = []
  ocrBestScore.value = 0
  ocrSecondScore.value = 0
}

const addToQueue = () => {
  // kept for backward compat but no longer used by template
  if (!draft.photoDataUrl) return
  draftQueue.value.push({
    draft: { ...draft, costs: draft.costs.map(c => ({ ...c })) },
    ocrProcessed: ocrProcessed.value,
    ocrSuccess: ocrSuccess.value,
    plateCandidates: [...plateCandidates.value],
    rawPlateCandidates: [...rawPlateCandidates.value],
    plateCandidateDetails: plateCandidateDetails.value.map((item) => ({ ...item })),
    needsPlateConfirmation: false,
    targetMarginValue: targetMarginValue.value,
    status: 'ready',
    processingStage: 'done',
    processingStartedAt: null,
    processingFinishedAt: null,
    processingDurationMs: null,
    ocrDurationMs: null,
    fipeDurationMs: null,
    ocrRequestId: '',
    ocrTimingsMs: {},
  })
  // reset just the photo/OCR fields, keep on step 1
  applyDraft(createEmptyDraft())
  ocrProcessed.value = false
  ocrSuccess.value = false
  plateCandidates.value = []
  rawPlateCandidates.value = []
  plateCandidateDetails.value = []
  ocrBestScore.value = 0
  ocrSecondScore.value = 0
  marginWasEdited.value = false
  targetMarginValue.value = 10000
  setStatus('Adicionado à fila! Envie a próxima foto.', 'ok')
}

const loadFromQueue = (index: number) => {
  // Persist any pending edits from the currently active queue item
  // before replacing the draft with another item.
  syncActiveQueueDraft()

  const item = draftQueue.value[index]
  if (!item || item.status !== 'ready') return
  closeQueuePreview()

  // Mark as active (stays in queue)
  activeQueueId.value = item.draft.id

  applyDraft(item.draft)
  ocrProcessed.value = item.ocrProcessed
  ocrSuccess.value = item.ocrSuccess
  plateCandidates.value = Array.isArray(item.plateCandidates) ? [...item.plateCandidates] : []
  rawPlateCandidates.value =
    Array.isArray(item.rawPlateCandidates) && item.rawPlateCandidates.length > 0
      ? [...item.rawPlateCandidates]
      : [...plateCandidates.value]
  plateCandidateDetails.value = Array.isArray(item.plateCandidateDetails)
    ? item.plateCandidateDetails.map((detail) => ({ ...detail }))
    : []
  if (item.plateCandidates.length > 0) {
    const normalizedCurrent = normalizePlate(item.draft.plate || '')
    if (item.needsPlateConfirmation || !normalizedCurrent || !item.plateCandidates.includes(normalizedCurrent)) {
      draft.plate = item.plateCandidates[0]
    }
  }
  targetMarginValue.value = item.targetMarginValue || suggestMarginByFipe(item.draft.fipeValue)
  marginWasEdited.value = item.draft.fipeValue > 0
  const hasAmbiguity = item.needsPlateConfirmation || isLikelyPlateAmbiguous(item.plateCandidates)
  editingPlate.value = hasAmbiguity
  editingMargin.value = false
  editingFipe.value = false
  editingBrandModel.value = false
  addingCost.value = false
  editingCostId.value = null
  showingDetails.value = false

  if (hasAmbiguity) {
    setStatus(
      `OCR encontrou placas parecidas (${item.plateCandidates.slice(0, 3).join(', ')}). Confirme antes de salvar.`,
      'warn',
    )
  }

  currentStep.value = 2
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

const openQueuePreview = (index: number) => {
  queuePreviewIndex.value = index
}

const closeQueuePreview = () => {
  queuePreviewIndex.value = null
}

const confirmQueueCandidate = async (candidate: string) => {
  if (loadingLookup.value) return
  if (queuePreviewIndex.value === null) return
  const index = queuePreviewIndex.value
  const item = draftQueue.value[index]
  if (!item || item.status !== 'ready') return

  const normalized = normalizePlate(candidate)
  if (!normalized) return

  selectingPlateCandidate.value = normalized
  item.draft.plate = normalized
  item.plateCandidates = [normalized, ...item.plateCandidates.filter((plate) => plate !== normalized)]
  item.plateCandidateDetails = reorderCandidateDetails(
    item.plateCandidates,
    Array.isArray(item.plateCandidateDetails) ? item.plateCandidateDetails : [],
  )
  item.needsPlateConfirmation = false
  item.ocrSuccess = true
  if (item.errorMessage?.startsWith('Confirme placa OCR:')) {
    item.errorMessage = undefined
  }

  closeQueuePreview()
  loadFromQueue(index)
  try {
    await applyPlateCandidate(normalized, 'queue-preview')
  } finally {
    selectingPlateCandidate.value = null
  }
}

const removeFromQueue = (index: number) => {
  if (queuePreviewIndex.value === index) {
    closeQueuePreview()
  } else if (queuePreviewIndex.value !== null && queuePreviewIndex.value > index) {
    queuePreviewIndex.value -= 1
  }
  draftQueue.value.splice(index, 1)
}

const toggleMarginEdit = () => {
  editingMargin.value = !editingMargin.value
  if (!editingMargin.value) {
    marginWasEdited.value = true
  }
}

const toggleFipeEdit = () => {
  editingFipe.value = !editingFipe.value
}

const toggleBrandModelEdit = () => {
  editingBrandModel.value = !editingBrandModel.value
}

const startEditCost = (cost: CostItem) => {
  editingCostId.value = cost.id
  editingCostAmount.value = cost.amount
}

const confirmEditCost = (id: string) => {
  const amount = Math.max(0, Number(editingCostAmount.value) || 0)

  if (amount <= 0) {
    setStatus('Informe um valor maior que zero para confirmar.', 'warn')
    return
  }

  const index = draft.costs.findIndex((item) => item.id === id)
  if (index !== -1) {
    draft.costs[index] = { ...draft.costs[index], amount }
    setStatus('Custo atualizado.', 'ok')
    syncActiveQueueDraft()
  }

  editingCostId.value = null
  editingCostAmount.value = 0
}

const cancelEditCost = () => {
  editingCostId.value = null
  editingCostAmount.value = 0
}

const toggleCostAdd = () => {
  addingCost.value = !addingCost.value
  if (!addingCost.value) {
    newCostAmount.value = 0
    newCostOtherLabel.value = ''
  }
}

const toggleDetailsBeforeSave = () => {
  if (showingDetails.value) {
    saveAndGoToStep3()
  } else {
    showingDetails.value = true
  }
}

const startNewCar = () => {
  clearDraft()
  showSavedCarsList.value = false
  currentStep.value = 1
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

const goToSavedCars = () => {
  justSaved.value = false
  currentStep.value = 3
  showSavedCarsList.value = true
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

const viewSavedCars = () => {
  showSavedCarsList.value = true
}

const editSavedCar = (record: AuctionCarRecord) => {
  loadFromLocal(record)
  currentStep.value = 2
  showSavedCarsList.value = false
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

const applySuggestedMargin = () => {
  targetMarginValue.value = suggestedMarginValue.value
  marginWasEdited.value = false
  editingMargin.value = false
}

const applyDraft = (value: DraftState) => {
  draft.id = value.id
  draft.plate = value.plate
  draft.photoDataUrl = value.photoDataUrl || ''
  draft.brand = value.brand
  draft.model = value.model
  draft.year = value.year
  draft.fipeValue = value.fipeValue
  draft.purchaseValue = value.purchaseValue
  draft.targetMarginPercent = value.targetMarginPercent
  draft.notes = value.notes
  draft.createdAt = value.createdAt
  draft.costs.splice(0, draft.costs.length, ...value.costs.map((item) => ({ ...item })))
}

const clearDraft = () => {
  applyDraft(createEmptyDraft())
  plateCandidates.value = []
  rawPlateCandidates.value = []
  plateCandidateDetails.value = []
  ocrBestScore.value = 0
  ocrSecondScore.value = 0
  ocrProcessed.value = false
  ocrSuccess.value = false
  targetMarginValue.value = 10000
  marginWasEdited.value = false
  editingPlate.value = false
  editingMargin.value = false
  editingFipe.value = false
  editingBrandModel.value = false
  addingCost.value = false
  editingCostId.value = null
  editingCostAmount.value = 0
  showingDetails.value = false
  justSaved.value = false
  activeQueueId.value = null
  newCostType.value = 'documentacao'
  newCostAmount.value = 0
  newCostOtherLabel.value = ''
  setStatus('Novo cadastro iniciado.', 'ok')
}


const onPlateInput = (event: Event) => {
  const input = event.target as HTMLInputElement
  draft.plate = normalizePlate(input.value)
  syncActiveQueueDraft()
}

const readErrorMessage = (error: unknown) => {
  const timeoutText = 'A leitura da imagem demorou demais (timeout). Tente foto menor/mais nítida e tente novamente.'

  if (error && typeof error === 'object') {
    const maybeData = (
      error as {
        data?: {
          statusMessage?: string
          message?: string
          cause?: string
          targetBaseUrl?: string
        }
        message?: string
      }
    ).data
    const cause = String(maybeData?.cause || '')
    const targetBaseUrl = String(maybeData?.targetBaseUrl || '')

    if (cause.toLowerCase().includes('econnrefused')) {
      return targetBaseUrl
        ? `OCR indisponivel: conexao recusada em ${targetBaseUrl}. O processo Flask provavelmente nao iniciou no deploy.`
        : 'OCR indisponivel: conexao recusada. O processo Flask provavelmente nao iniciou no deploy.'
    }

    if (maybeData?.statusMessage) return maybeData.statusMessage
    if (maybeData?.message) return maybeData.message

    const maybeMessage = String((error as { message?: string }).message || '')
    if (maybeMessage.toLowerCase().includes('timeout')) return timeoutText
  }

  if (error instanceof Error && error.message) {
    if (error.message.toLowerCase().includes('timeout')) return timeoutText
    return error.message
  }

  return 'Falha na operacao.'
}

const OCR_IMAGE_MAX_SIDE = 1600
const OCR_IMAGE_QUALITY = 0.82

const loadImageElement = (dataUrl: string) =>
  new Promise<HTMLImageElement>((resolve, reject) => {
    const image = new Image()
    image.onload = () => resolve(image)
    image.onerror = (event) => reject(event)
    image.src = dataUrl
  })

const optimizeImageForOcr = async (dataUrl: string) => {
  const image = await loadImageElement(dataUrl)
  const sourceWidth = image.naturalWidth || image.width
  const sourceHeight = image.naturalHeight || image.height

  if (!sourceWidth || !sourceHeight) return dataUrl

  const longestSide = Math.max(sourceWidth, sourceHeight)
  const scale = longestSide > OCR_IMAGE_MAX_SIDE ? OCR_IMAGE_MAX_SIDE / longestSide : 1
  const targetWidth = Math.max(1, Math.round(sourceWidth * scale))
  const targetHeight = Math.max(1, Math.round(sourceHeight * scale))

  const canvas = document.createElement('canvas')
  canvas.width = targetWidth
  canvas.height = targetHeight

  const context = canvas.getContext('2d')
  if (!context) return dataUrl

  context.drawImage(image, 0, 0, targetWidth, targetHeight)
  const optimized = canvas.toDataURL('image/jpeg', OCR_IMAGE_QUALITY)

  return optimized.length < dataUrl.length ? optimized : dataUrl
}

const refreshPlateFipeQuota = async () => {
  plateFipeQuotaLoading.value = true
  plateFipeQuotaError.value = ''

  try {
    const response = await api.getPlateFipeQuotas()
    applyQuotaInfo(response.quota)
  } catch (error) {
    plateFipeQuotaError.value = readErrorMessage(error)
  } finally {
    plateFipeQuotaLoading.value = false
  }
}

const resolveFeedbackCandidates = () => {
  const source = rawPlateCandidates.value.length > 0 ? rawPlateCandidates.value : plateCandidates.value
  return Array.from(new Set(source.map((item) => normalizePlate(item || '')).filter(Boolean))).slice(0, 10)
}

const applyPlateCandidate = async (candidate: string, source: 'step2' | 'queue-preview' = 'step2') => {
  if (loadingLookup.value) return
  const normalized = normalizePlate(candidate)
  if (!normalized) return

  const feedbackCandidates = resolveFeedbackCandidates()
  const recognizedPlate = normalizePlate(feedbackCandidates[0] || '')
  const isUsefulFeedback =
    Boolean(!recognizedPlate) ||
    recognizedPlate !== normalized ||
    feedbackCandidates.length > 1

  if (isUsefulFeedback) {
    void registerOcrConfirmation({
      recognizedPlate,
      confirmedPlate: normalized,
      candidates: feedbackCandidates,
      source,
      requestId: activeQueueItem.value?.ocrRequestId,
      timingsMs: activeQueueItem.value?.ocrTimingsMs,
    }).catch(() => {
      // feedback nao pode bloquear a consulta FIPE
    })
  }

  selectingPlateCandidate.value = normalized
  draft.plate = normalized
  setStatus(`Placa aplicada: ${normalized}. Consultando FIPE...`, 'ok')
  try {
    await lookupVehicleByPlate(normalized)
  } finally {
    selectingPlateCandidate.value = null
  }
}

const lookupVehicleByPlate = async (plate: string) => {
  const normalizedPlate = normalizePlate(plate)
  if (!normalizedPlate) {
    setStatus('Informe uma placa válida para consulta.', 'warn')
    return
  }

  draft.plate = normalizedPlate
  loadingLookup.value = true
  let lookupCompleted = false

  try {
    const lookup = await api.lookupPlateAndFipe({ plate: normalizedPlate })
    const { result, warning, detail, quota, cache } = lookup
    applyQuotaInfo(quota)

    draft.brand = String(result.brand || '').trim()
    draft.model = String(result.model || '').trim()
    draft.year = typeof result.year === 'number' ? result.year : null
    draft.fipeValue = Number(result.fipeValue) || 0

    const cacheHint = cache.hit ? ' (cache, sem custo adicional).' : ''
    const providerWarning = [warning, detail].filter(Boolean).join(' ')

    if (providerWarning) {
      setStatus(`Placa ${normalizedPlate} identificada. ${providerWarning}${cacheHint}`, 'warn')
    } else if (draft.fipeValue <= 0) {
      setStatus(`Placa ${normalizedPlate} identificada, mas sem valor FIPE no retorno.${cacheHint}`, 'warn')
    } else {
      setStatus(`Placa ${normalizedPlate} consultada com sucesso${cacheHint}`, 'ok')
    }
    lookupCompleted = true
  } catch (error) {
    setStatus(`Placa ${normalizedPlate} identificada, mas falhou consulta FIPE: ${readErrorMessage(error)}`, 'warn')
  } finally {
    if (lookupCompleted && activeQueueId.value) {
      const queueIndex = draftQueue.value.findIndex((item) => item.draft.id === activeQueueId.value)
      if (queueIndex >= 0) {
        const queueItem = draftQueue.value[queueIndex]
        queueItem.needsPlateConfirmation = false
        if (queueItem.errorMessage?.startsWith('Confirme placa OCR:')) {
          queueItem.errorMessage = undefined
        }
        queueItem.ocrSuccess = true
      }
    }
    syncActiveQueueDraft()
    loadingLookup.value = false
    void refreshPlateFipeQuota()
  }
}

const lookupCurrentPlate = async () => {
  await lookupVehicleByPlate(draft.plate)
}

const onPhotoSelected = async (event: Event) => {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  // Reset input immediately so user can pick another photo right away
  input.value = ''

  if (file.size > 4_000_000) {
    setStatus('Imagem grande demais. Use foto ate 4MB.', 'warn')
    return
  }

  const fileData = await new Promise<string>((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result || ''))
    reader.onerror = () => reject(reader.error)
    reader.readAsDataURL(file)
  })

  let processedPhotoData = fileData
  try {
    processedPhotoData = await optimizeImageForOcr(fileData)
  } catch {
    processedPhotoData = fileData
  }

  // Add to queue immediately with status 'processing'
  const newItem: DraftQueueItem = {
    draft: { ...createEmptyDraft(), photoDataUrl: processedPhotoData },
    ocrProcessed: false,
    ocrSuccess: false,
    plateCandidates: [],
    rawPlateCandidates: [],
    plateCandidateDetails: [],
    needsPlateConfirmation: false,
    targetMarginValue: 10000,
    status: 'processing',
    processingStage: 'ocr',
    processingStartedAt: Date.now(),
    processingFinishedAt: null,
    processingDurationMs: null,
    ocrDurationMs: null,
    fipeDurationMs: null,
    ocrRequestId: '',
    ocrTimingsMs: {},
  }
  draftQueue.value.push(newItem)
  const queueIndex = draftQueue.value.length - 1

  setStatus('Foto adicionada! Pode enviar mais enquanto processa.', 'ok')

  // Process OCR in background
  processQueueItemAsync(queueIndex)
}

const processQueueItemAsync = async (index: number) => {
  const item = draftQueue.value[index]
  if (!item || !item.draft.photoDataUrl) {
    if (item) {
      item.ocrProcessed = true
      item.ocrSuccess = false
      item.errorMessage = 'Imagem invalida para OCR.'
      markQueueProcessingFinished(item, 'error')
    }
    return
  }

  markQueueProcessingStarted(item)
  const ocrStartedAt = Date.now()

  try {
    const response = await api.extractPlateFromImage({
      imageBase64: item.draft.photoDataUrl,
      filename: 'camera-upload',
      requestId: createId(),
    })

    const ocrElapsedMs = Math.max(0, Date.now() - ocrStartedAt)
    const { result } = response
    const candidates = Array.isArray(result.candidates) ? result.candidates : []
    const candidateDetails = buildCandidateDetails(candidates)
    const rawCandidates = Array.from(
      new Set(candidates.map((c: { plate?: string }) => normalizePlate(c?.plate || '')).filter(Boolean)),
    )
    const dedupedCandidates = prioritizeCandidatesByFeedback(rawCandidates)
    const sortedDetails = reorderCandidateDetails(dedupedCandidates, candidateDetails)
    const bestScore = Number(candidates[0]?.confidence ?? result.confidence ?? 0)
    const secondScore = Number(candidates[1]?.confidence ?? 0)
    const nearTie = dedupedCandidates.length > 1 && Math.abs(bestScore - secondScore) <= 0.06
    const engineAmbiguous = Boolean(result.engine?.ambiguous_top_pair)
    const timeoutReached = Number(result.engine?.timings_ms?.timeout_reached ?? 0) > 0

    item.ocrRequestId = String(response.requestId || '')
    item.ocrTimingsMs = result.engine?.timings_ms || {}
    item.ocrDurationMs = Number(result.engine?.timings_ms?.total_ms || 0) || ocrElapsedMs
    item.rawPlateCandidates = rawCandidates
    item.plateCandidates = dedupedCandidates
    item.plateCandidateDetails = sortedDetails
    item.needsPlateConfirmation = false
    item.ocrProcessed = true
    const primaryCandidate = resolvePrimaryPlateCandidate(dedupedCandidates, result.plate || '')
    if (primaryCandidate) {
      item.draft.plate = primaryCandidate
    }
    const hasAmbiguity = isLikelyPlateAmbiguous(dedupedCandidates) || nearTie || engineAmbiguous

    if (result.plate) {
      item.ocrSuccess = true

      if (hasAmbiguity) {
        const hint = dedupedCandidates.length > 0
          ? dedupedCandidates.slice(0, 3).join(', ')
          : normalizePlate(result.plate || '')
        item.needsPlateConfirmation = true
        item.ocrSuccess = false
        item.errorMessage = hint ? `Confirme placa OCR: ${hint}` : 'Confirme placa OCR antes da primeira consulta FIPE.'
        markQueueProcessingFinished(item, 'ready')
        return
      }

      // Fetch FIPE in background
      item.processingStage = 'fipe'
      const fipeStartedAt = Date.now()
      try {
        const lookup = await api.lookupPlateAndFipe({ plate: item.draft.plate })
        const { result: fipeResult, warning, detail, quota } = lookup
        applyQuotaInfo(quota)
        item.draft.brand = String(fipeResult.brand || '').trim()
        item.draft.model = String(fipeResult.model || '').trim()
        item.draft.year = typeof fipeResult.year === 'number' ? fipeResult.year : null
        item.draft.fipeValue = Number(fipeResult.fipeValue) || 0
        item.targetMarginValue = suggestMarginByFipe(item.draft.fipeValue)
        item.draft.costs = getDefaultCosts()
        const providerWarning = [warning, detail].filter(Boolean).join(' ')
        if (providerWarning) {
          item.errorMessage = providerWarning
        } else if (!item.draft.brand && !item.draft.model && item.draft.fipeValue <= 0) {
          item.errorMessage = 'Consulta retornou sem marca/modelo/FIPE.'
        } else {
          item.errorMessage = undefined
        }
      } catch (err: unknown) {
        // FIPE failed but plate was found — still mark ready, warn via errorMessage
        item.errorMessage = `FIPE: ${readErrorMessage(err)}`
      } finally {
        item.fipeDurationMs = Math.max(0, Date.now() - fipeStartedAt)
      }
    } else {
      item.ocrSuccess = false
      item.needsPlateConfirmation = dedupedCandidates.length > 0
      item.errorMessage = dedupedCandidates.length > 0
        ? `OCR sem placa final. Candidatos: ${dedupedCandidates.slice(0, 3).join(', ')}`
        : (
            timeoutReached
              ? 'OCR atingiu limite de tempo. Tente foto mais aproximada da placa.'
              : 'OCR nao identificou placa na imagem.'
          )
    }

    markQueueProcessingFinished(item, 'ready')
  } catch (err: unknown) {
    item.ocrProcessed = true
    item.ocrSuccess = false
    item.errorMessage = readErrorMessage(err)
    markQueueProcessingFinished(item, 'error')
  }
}

const extractPlateFromPhoto = async () => {
  if (!draft.photoDataUrl) {
    setStatus('Envie a foto para extrair a placa.', 'warn')
    return
  }

  loadingLookup.value = true

  try {
    const ocrStartedAt = Date.now()
    const response = await api.extractPlateFromImage({
      imageBase64: draft.photoDataUrl,
      filename: 'camera-upload',
      requestId: createId(),
    })

    const { result } = response
    const measuredOcrMs = Math.max(0, Date.now() - ocrStartedAt)

    const candidates = Array.isArray(result.candidates) ? result.candidates : []
    const candidateDetails = buildCandidateDetails(candidates)
    const rawCandidates = Array.from(
      new Set(candidates.map((item: { plate?: string }) => normalizePlate(item?.plate || '')).filter(Boolean)),
    )
    const dedupedCandidates = prioritizeCandidatesByFeedback(rawCandidates)
    const sortedDetails = reorderCandidateDetails(dedupedCandidates, candidateDetails)
    const bestScore = Number(candidates[0]?.confidence ?? result.confidence ?? 0)
    const secondScore = Number(candidates[1]?.confidence ?? 0)
    const nearTie = dedupedCandidates.length > 1 && Math.abs(bestScore - secondScore) <= 0.06
    const engineAmbiguous = Boolean(result.engine?.ambiguous_top_pair)
    const timeoutReached = Number(result.engine?.timings_ms?.timeout_reached ?? 0) > 0
    const ocrDurationMs = Number(result.engine?.timings_ms?.total_ms || 0) || measuredOcrMs
    rawPlateCandidates.value = rawCandidates
    plateCandidates.value = dedupedCandidates
    plateCandidateDetails.value = sortedDetails
    const primaryCandidate = resolvePrimaryPlateCandidate(dedupedCandidates, result.plate || '')
    if (primaryCandidate) {
      draft.plate = primaryCandidate
    }
    ocrBestScore.value = bestScore
    ocrSecondScore.value = secondScore
    ocrProcessed.value = true

    if (result.plate) {
      ocrSuccess.value = true

      const hasAmbiguity = isLikelyPlateAmbiguous(dedupedCandidates) || nearTie || engineAmbiguous
      if (hasAmbiguity) {
        const hint = dedupedCandidates.length > 0
          ? dedupedCandidates.slice(0, 3).join(', ')
          : normalizePlate(result.plate || '')
        editingPlate.value = true
        setStatus(
          hint
            ? `OCR encontrou candidatos parecidos (${hint}). Confirme a placa antes da consulta.`
            : 'OCR com baixa confianca para placa final. Confirme a placa antes da consulta.',
          'warn',
        )
        return
      }

      setStatus(`Placa identificada: ${draft.plate}. Consultando FIPE... OCR ${formatElapsedMs(ocrDurationMs)}.`, 'ok')
      if (draft.plate) {
        await lookupVehicleByPlate(draft.plate)
      }
      return
    }

    ocrSuccess.value = false
    const topCandidates = dedupedCandidates.slice(0, 3)
    const candidatesHint = topCandidates.length > 0 ? ` Candidatos: ${topCandidates.join(', ')}.` : ''
    const timeoutHint = timeoutReached ? ' OCR atingiu limite de tempo.' : ''
    setStatus(`OCR com baixa confiança em ${formatElapsedMs(ocrDurationMs)}.${timeoutHint}` + candidatesHint, 'warn')
  } catch (error) {
    ocrProcessed.value = true
    ocrSuccess.value = false
    plateCandidates.value = []
    rawPlateCandidates.value = []
    plateCandidateDetails.value = []
    setStatus(readErrorMessage(error), 'error')
  } finally {
    loadingLookup.value = false
  }
}

const onCostTypeChange = () => {
  const option = costTypeOptions.find((item) => item.value === newCostType.value)
  if (option?.defaultAmount && newCostAmount.value <= 0) {
    newCostAmount.value = option.defaultAmount
  }
}

const resolveCostLabel = () => {
  if (newCostType.value === 'outros') {
    return newCostOtherLabel.value.trim()
  }

  const option = costTypeOptions.find((item) => item.value === newCostType.value)
  return option?.label || ''
}

const addCostItem = () => {
  const label = resolveCostLabel()
  const amount = Math.max(0, Number(newCostAmount.value) || 0)

  if (!label) {
    setStatus('Informe o nome do custo para adicionar.', 'warn')
    return
  }

  if (amount <= 0) {
    setStatus('Informe um valor maior que zero para o custo.', 'warn')
    return
  }

  const existingLeilao = newCostType.value === 'leilao'
    ? draft.costs.find((item) => item.label.toLowerCase() === 'leilao')
    : null

  if (existingLeilao) {
    existingLeilao.amount = amount
    setStatus('Custo de leilao atualizado.', 'ok')
    syncActiveQueueDraft()
    newCostAmount.value = 0
    addingCost.value = false
    return
  }

  draft.costs.push({
    id: createId(),
    label,
    amount,
  })

  newCostAmount.value = 0
  if (newCostType.value === 'outros') {
    newCostOtherLabel.value = ''
  }
  addingCost.value = false

  setStatus('Custo adicionado.', 'ok')
  syncActiveQueueDraft()
}

const removeCostItem = (id: string) => {
  const nextItems = draft.costs.filter((item) => item.id !== id)

  if (nextItems.length === draft.costs.length) return

  draft.costs.splice(0, draft.costs.length, ...nextItems)

  if (draft.costs.length === 0) {
    draft.costs.push({ id: createId(), label: 'Leilao', amount: 800 })
  }

  setStatus('Custo removido.', 'warn')
  syncActiveQueueDraft()
}

const resolveMarginPercent = () => {
  if (draft.fipeValue <= 0) return 0
  return (Number(targetMarginValue.value || 0) / draft.fipeValue) * 100
}

const resolvePurchaseValue = () => {
  return chosenBidValue.value > 0 ? chosenBidValue.value : maxAuctionBid.value
}

const buildRecord = (): AuctionCarRecord => {
  const now = new Date().toISOString()
  const createdAt = draft.createdAt || now

  const costs = draft.costs.map((item) => ({
    id: item.id,
    label: item.label.trim() || 'Custo sem nome',
    amount: Math.max(0, Number(item.amount) || 0),
  }))

  const purchaseValue = resolvePurchaseValue()
  const targetMarginPercent = resolveMarginPercent()

  return {
    id: draft.id,
    plate: normalizePlate(draft.plate),
    photoDataUrl: draft.photoDataUrl || '',
    brand: draft.brand.trim(),
    model: draft.model.trim(),
    year: draft.year,
    fipeValue: Math.max(0, Number(draft.fipeValue) || 0),
    purchaseValue,
    costs,
    targetMarginPercent,
    mountClass: draft.mountClass,
    notes: draft.notes.trim(),
    createdAt,
    updatedAt: now,
    summary: calculateAuctionSummary({
      fipeValue: draft.fipeValue,
      purchaseValue,
      costs,
      targetMarginPercent,
      mountClass: draft.mountClass,
    }),
  }
}

const reloadLocal = async () => {
  localCars.value = await indexedDb.listCars()
  savedCarsCount.value = localCars.value.length
}

const saveAndGoToStep3 = async () => {
  if (!indexedDb.isSupported) {
    setStatus('IndexedDB nao disponivel neste navegador.', 'error')
    return
  }

  if (!canSave.value) {
    setStatus('Preencha foto/dados/custos antes de salvar.', 'warn')
    return
  }

  const purchaseValue = resolvePurchaseValue()
  draft.purchaseValue = purchaseValue

  const record = buildRecord()
  await indexedDb.saveCar(record)
  draft.createdAt = record.createdAt
  await reloadLocal()

  // Remove the saved item from queue
  if (activeQueueId.value) {
    const qi = draftQueue.value.findIndex(i => i.draft.id === activeQueueId.value)
    if (qi !== -1) draftQueue.value.splice(qi, 1)
    activeQueueId.value = null
  }

  setStatus(`Carro salvo com sucesso!`, 'ok')
  justSaved.value = true
  currentStep.value = 3
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

const loadFromLocal = (record: AuctionCarRecord) => {
  applyDraft({
    id: record.id,
    plate: record.plate,
    photoDataUrl: record.photoDataUrl,
    brand: record.brand,
    model: record.model,
    year: record.year,
    fipeValue: record.fipeValue,
    purchaseValue: record.purchaseValue,
    costs: record.costs,
    targetMarginPercent: record.targetMarginPercent,
    mountClass: record.mountClass || 'pequena',
    notes: record.notes,
    createdAt: record.createdAt,
  })

  plateCandidates.value = []
  rawPlateCandidates.value = []
  plateCandidateDetails.value = []
  ocrBestScore.value = 0
  ocrSecondScore.value = 0
  ocrProcessed.value = true
  ocrSuccess.value = true

  const restoredTarget = record.fipeValue > 0 ? (record.targetMarginPercent / 100) * record.fipeValue : 0
  targetMarginValue.value = restoredTarget > 0 ? restoredTarget : suggestMarginByFipe(record.fipeValue)
  marginWasEdited.value = true
  editingPlate.value = false

  setStatus('Registro carregado para edicao.', 'ok')
}

const removeLocal = async (id: string) => {
  await indexedDb.deleteCar(id)
  await reloadLocal()

  if (draft.id === id) {
    clearDraft()
  }

  setStatus('Registro local removido.', 'warn')
}

onMounted(async () => {
  if (import.meta.client && processingClockInterval === null) {
    processingClockMs.value = Date.now()
    processingClockInterval = window.setInterval(() => {
      processingClockMs.value = Date.now()
    }, 250)
  }

  await refreshOcrFeedbackProfile()
  await refreshPlateFipeQuota()

  if (!indexedDb.isSupported) {
    setStatus('Este navegador nao suporta IndexedDB.', 'warn')
    return
  }

  await reloadLocal()
})

onBeforeUnmount(() => {
  if (processingClockInterval !== null) {
    clearInterval(processingClockInterval)
    processingClockInterval = null
  }
})
</script>
