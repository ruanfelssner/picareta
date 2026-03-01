<template>
  <div class="min-h-screen space-y-5 py-5">
    <section class="surface-card rounded-2xl overflow-hidden">
        <div
          class="relative"
          @touchstart="onPhotoTouchStart"
          @touchmove="onPhotoTouchMove"
          @touchend="onPhotoTouchEnd"
        >
          <img
            v-if="displayPhotoSrc"
            :src="displayPhotoSrc"
            :style="photoTransformStyle"
            class="h-[44vh] max-h-[54vh] min-h-64 w-full bg-slate-900 object-contain cursor-pointer select-none block"
            :alt="isPlateFocusedPreview ? 'Crop da placa em foco' : 'Foto principal do veículo'"
            draggable="false"
            @click="openOriginalPhotoModal"
          >

          <div v-if="processingOcr" class="absolute inset-0 flex items-center justify-center bg-slate-900/55">
            <div class="flex flex-col items-center gap-1.5 rounded-xl bg-white/95 px-5 py-3 shadow-lg min-w-36">
              <div class="flex items-center gap-2">
                <svg class="h-4 w-4 shrink-0 animate-spin text-slate-700" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" />
                  <path class="opacity-80" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
                </svg>
                <span class="text-xs font-bold tabular-nums text-slate-700">{{ ocrProgress }}%</span>
              </div>
              <div class="h-1 w-full rounded-full bg-slate-200 overflow-hidden">
                <div
                  class="h-full rounded-full bg-slate-700 transition-all duration-300"
                  :style="{ width: ocrProgress + '%' }"
                />
              </div>
              <span class="text-[10px] font-medium text-slate-500 text-center leading-tight">{{ ocrStageLabel }}</span>
            </div>
          </div>

          <div
            v-if="isPlateFocusedPreview"
            class="absolute left-2 bottom-2 rounded-lg bg-slate-950/80 px-2 py-1 text-[10px] font-semibold uppercase tracking-wider text-white"
          >
            Foco na placa
          </div>

          <div v-if="displayPhotoSrc" class="absolute left-2 top-2 flex items-center gap-1">
            <button
              class="inline-flex items-center justify-center rounded-lg bg-slate-950/80 p-1.5 text-white hover:bg-rose-700/90"
              type="button"
              title="Limpar e recomeçar"
              @click="clearDraft(); resetPhotoZoom()"
            >
              <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
            <button
              class="inline-flex items-center justify-center rounded-lg bg-slate-950/80 p-1.5 text-white hover:bg-slate-700/90 disabled:opacity-50"
              type="button"
              title="Retentar OCR com a mesma foto"
              :disabled="processingOcr"
              @click="extractPlateFromPhoto(draft.photoDataUrl)"
            >
              <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </button>
          </div>

          <button
            v-if="displayPhotoSrc"
            class="absolute right-2 top-2 inline-flex items-center gap-1 rounded-lg bg-slate-950/80 px-2.5 py-1.5 text-[11px] font-semibold text-white hover:bg-slate-950"
            type="button"
            @click="triggerCameraCapture"
          >
            <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            Enviar novamente
          </button>
        </div>
        <div class="p-4 space-y-3">
            <div v-if="ocrNotFound" class="flex items-start gap-2 rounded-xl border border-rose-200 bg-rose-50 px-3 py-2.5">
              <svg class="mt-0.5 h-4 w-4 shrink-0 text-rose-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
              </svg>
              <div>
                <p class="text-xs font-bold text-rose-700">Nenhuma placa identificada</p>
                <p class="text-[11px] text-rose-600 mt-0.5">O OCR não encontrou a placa na imagem. Tente uma foto mais próxima e bem iluminada, ou digite a placa manualmente abaixo.</p>
              </div>
            </div>
            <p v-if="displayPhotoSrc" class="text-[10px] font-bold uppercase tracking-wider text-slate-600">
              Placa
            </p>
            <div v-if="displayPhotoSrc" class="flex items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 p-2">
              <input
                :value="draft.plate"
                class="h-12 min-w-0 flex-1 rounded-lg border border-slate-200 bg-white px-3 text-lg font-bold tracking-widest uppercase text-slate-900 outline-none focus:border-slate-400 focus:ring-2 focus:ring-slate-200"
                maxlength="8"
                placeholder="AAA0A00"
                @input="onPlateInput"
              >
              <button
                class="ml-auto inline-flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-slate-900 text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
                type="button"
                :disabled="loadingLookup || !draft.plate"
                aria-label="Confirmar placa e consultar"
                @click="lookupCurrentPlate"
              >
                <div v-if="loadingLookup" class="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                <svg v-else class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7" />
                </svg>
              </button>
            </div>
            <div v-if="plateCandidates.length > 0" class="flex flex-wrap items-center gap-x-3 gap-y-1.5 pl-1 pt-1 border-t border-slate-100">
              <span class="text-xs font-semibold text-slate-500">Sugestões:</span>
              <button
                v-for="candidate in plateCandidates"
                :key="candidate"
                class="text-sm font-semibold underline decoration-1 underline-offset-4 transition-colors disabled:opacity-60"
                :class="candidate === draft.plate ? 'text-slate-900 decoration-slate-900' : 'text-slate-500 decoration-slate-400 hover:text-slate-700'"
                type="button"
                :disabled="loadingLookup"
                @click="applyPlateCandidate(candidate)"
              >
                {{ candidate }}
              </button>
            </div>
          <input
            ref="primaryCameraInputRef"
            class="hidden"
            type="file"
            accept="image/*"
            @change="onPrimaryPhotoSelected"
          >

          <button
            v-if="!displayPhotoSrc"
            class="flex w-full items-center justify-center gap-2 rounded-2xl border-2 border-dashed border-slate-300 bg-white py-4 text-base font-semibold text-slate-700 hover:border-slate-500 hover:bg-slate-50"
            type="button"
            @click="triggerCameraCapture"
          >
            <svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            Tirar foto
          </button>
        </div>
    </section>

    <section v-if="loadingLookup || canShowVehicleData" class="space-y-5">

      <div v-if="loadingLookup" class="surface-card rounded-2xl p-3">
        <div class="flex items-center gap-3">
          <div class="h-5 w-5 animate-spin rounded-full border-2 border-slate-400 border-t-transparent" />
          <p class="text-sm font-semibold text-slate-700">Consultando placa e FIPE...</p>
        </div>
      </div>

      <div v-if="canShowVehicleData" class="surface-card rounded-2xl p-3">
        <h2 class="text-xl font-bold text-slate-900">Dados do veículo</h2>

        <div class="mt-4 space-y-4">
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="field-label">Marca</label>
              <input v-model="draft.brand" class="field-input mt-1" placeholder="Marca">
            </div>
            <div>
              <label class="field-label">Modelo</label>
              <input v-model="draft.model" class="field-input mt-1" placeholder="Modelo">
            </div>
            <div>
              <label class="field-label">Ano</label>
              <input v-model.number="draft.year" class="field-input mt-1" type="number" min="1900" max="2100" placeholder="Ano">
            </div>
            <div>
              <label class="field-label">KM</label>
              <input v-model.number="draft.km" class="field-input mt-1" type="number" min="0" step="100" placeholder="Quilometragem">
            </div>
            <div>
              <label class="field-label">Valor FIPE</label>
              <input v-model.number="draft.fipeValue" class="field-input mt-1" type="number" min="0" step="100" placeholder="0">
            </div>
            <div>
              <label class="field-label">Margem alvo</label>
              <div class="mt-1 grid grid-cols-[1fr_auto] gap-2">
                <input v-model.number="targetMarginValue" class="field-input" type="number" min="0" step="500" @input="onMarginInput">
                <button
                  class="rounded-lg border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-100"
                  type="button"
                  @click="applySuggestedMargin"
                >
                  Sugerir
                </button>
              </div>
            </div>
          </div>

          <div>
            <p class="field-label">Tipo de monta</p>
            <div class="mt-2 grid grid-cols-3 gap-2 sm:grid-cols-4">
              <button
                class="rounded-lg border-2 px-2 py-2 text-xs font-bold transition-colors"
                :class="draft.mountClass === 'sem_monta' ? 'border-emerald-600 bg-emerald-50 text-emerald-800' : 'border-slate-300 bg-white text-slate-700 hover:bg-slate-50'"
                type="button"
                @click="draft.mountClass = 'sem_monta'"
              >
                Sem monta
              </button>
              <button
                class="rounded-lg border-2 px-2 py-2 text-xs font-bold transition-colors"
                :class="draft.mountClass === 'pequena' ? 'border-blue-600 bg-blue-50 text-blue-800' : 'border-slate-300 bg-white text-slate-700 hover:bg-slate-50'"
                type="button"
                @click="draft.mountClass = 'pequena'"
              >
                Pequena
              </button>
              <button
                class="rounded-lg border-2 px-2 py-2 text-xs font-bold transition-colors"
                :class="draft.mountClass === 'media' ? 'border-indigo-600 bg-indigo-50 text-indigo-800' : 'border-slate-300 bg-white text-slate-700 hover:bg-slate-50'"
                type="button"
                @click="draft.mountClass = 'media'"
              >
                Média
              </button>
            </div>
          </div>

          <div>
            <div class="flex items-center justify-between gap-2">
              <p class="field-label">Galeria do veículo</p>
              <button
                class="rounded-lg border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-100"
                type="button"
                @click="triggerAdditionalGalleryUpload"
              >
                + Foto
              </button>
            </div>
            <input
              ref="additionalGalleryInputRef"
              class="hidden"
              type="file"
              accept="image/*"
              multiple
              @change="onAdditionalPhotosSelected"
            >

            <div v-if="draft.galleryPhotos.length > 0" class="mt-2 flex gap-2 overflow-x-auto pb-1">
              <div v-for="(photo, idx) in draft.galleryPhotos" :key="photo + idx" class="relative shrink-0">
                <img
                  :src="photo"
                  class="h-20 w-20 cursor-pointer rounded-xl border border-slate-200 object-cover"
                  alt="Foto adicional"
                  @click="openGalleryModal(idx)"
                >
                <button
                  class="absolute -right-1 -top-1 flex h-5 w-5 items-center justify-center rounded-full bg-rose-600 text-white"
                  type="button"
                  @click.stop="removeAdditionalPhoto(idx)"
                >
                  <svg class="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>
            <p v-else class="mt-2 text-xs text-slate-500">Sem fotos adicionais.</p>
          </div>
        </div>
      </div>

      <div v-if="canShowVehicleData" class="surface-card rounded-2xl p-3">
        <div class="mb-3 flex items-center justify-between">
          <h3 class="text-base font-bold text-slate-900">Custos</h3>
          <button
            class="rounded-lg border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-100"
            type="button"
            @click="toggleCostAdd"
          >
            {{ addingCost ? 'Cancelar' : '+ Adicionar' }}
          </button>
        </div>

        <div v-if="addingCost" class="mb-3 rounded-xl border border-slate-200 bg-slate-50 p-2">
          <div class="flex items-center gap-1.5">
            <select v-model="newCostType" class="field-input h-10 min-w-0 flex-1 text-sm" @change="onCostTypeChange">
              <option v-for="option in costTypeOptions" :key="option.value" :value="option.value">
                {{ option.label }}
              </option>
            </select>
            <input
              :value="formatMoneyInput(newCostAmount)"
              class="field-input h-10 w-28! shrink-0 text-sm"
              type="text"
              inputmode="decimal"
              list="cost-value-presets"
              placeholder="R$ 0,00"
              @input="onNewCostAmountInput"
            >
            <button
              class="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-slate-900 text-white hover:bg-slate-800"
              type="button"
              aria-label="Adicionar custo"
              @click="addCostItem"
            >
              <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M12 5v14m-7-7h14" />
              </svg>
            </button>
          </div>
          <datalist id="cost-value-presets">
            <option v-for="preset in costValuePresets" :key="preset" :value="formatMoneyInput(preset)" />
          </datalist>
          <input
            v-if="newCostType === 'outros'"
            v-model="newCostOtherLabel"
            class="field-input mt-2"
            placeholder="Descricao"
          >
        </div>

        <div v-if="draft.costs.length === 0" class="rounded-xl border border-dashed border-slate-300 px-3 py-4 text-center text-sm text-slate-500">
          Sem custos cadastrados.
        </div>

        <div v-else class="space-y-2">
          <div v-for="cost in draft.costs" :key="cost.id" class="rounded-xl border border-slate-200 bg-white p-2.5">
            <div class="grid grid-cols-[minmax(0,1fr)_106px_auto] items-center gap-1.5">
              <input
                v-model="cost.label"
                class="field-input h-9 text-sm"
                :readonly="isAutoMountCost(cost)"
                :class="isAutoMountCost(cost) ? 'cursor-default bg-slate-100 text-slate-500' : ''"
                placeholder="Descricao"
                @blur="syncDraftState"
              >
              <input
                :value="formatMoneyInput(cost.amount)"
                class="field-input h-9 text-sm"
                :readonly="isAutoMountCost(cost)"
                :class="isAutoMountCost(cost) ? 'cursor-default bg-slate-100 text-slate-500' : ''"
                type="text"
                inputmode="decimal"
                list="cost-value-presets"
                @input="onCostAmountInput(cost, $event)"
              >
              <span
                v-if="isAutoMountCost(cost)"
                class="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-slate-300 text-center text-[10px] font-semibold text-slate-500"
              >
                Auto
              </span>
              <button
                v-else
                class="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-rose-300 text-rose-700 hover:bg-rose-50"
                type="button"
                aria-label="Remover custo"
                @click="removeCostItem(cost.id)"
              >
                <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>
        </div>

        <p class="mt-3 text-right text-xs font-semibold uppercase tracking-wider text-slate-500">
          Total de custos: <span class="text-sm text-slate-900">{{ formatMoney(totalCosts) }}</span>
        </p>
      </div>

      <div v-if="canShowVehicleData" class="grid grid-cols-2 gap-3">
        <div class="rounded-xl border-2 border-emerald-400 bg-emerald-50 p-4">
          <div class="flex items-center justify-between gap-2">
            <p class="text-xs font-semibold uppercase tracking-wider text-emerald-700">Valor compra</p>
            <label class="inline-flex items-center gap-1 text-[10px] font-semibold text-emerald-700">
              <input v-model="draft.purchaseOverrideEnabled" type="checkbox" class="h-3.5 w-3.5">
              Editar
            </label>
          </div>
          <p class="mt-1 text-2xl font-bold text-emerald-800">{{ formatMoney(effectivePurchaseValue) }}</p>
          <input
            v-if="draft.purchaseOverrideEnabled"
            v-model.number="draft.purchaseValue"
            class="field-input mt-2"
            type="number"
            min="0"
            step="100"
          >
          <p class="mt-2 text-xs text-emerald-700">FIPE - Margem - Custos</p>
        </div>

        <div class="rounded-xl border-2 border-blue-400 bg-blue-50 p-4">
          <p class="text-xs font-semibold uppercase tracking-wider text-blue-700">Média venda</p>
          <p class="mt-1 text-2xl font-bold text-blue-800">{{ formatMoney(estimatedSaleValue) }}</p>
          <p class="mt-2 text-xs text-blue-700">{{ saleDiscountLabel }}</p>
        </div>

        <div class="rounded-xl border-2 border-slate-300 bg-slate-50 p-4">
          <p class="text-xs font-semibold uppercase tracking-wider text-slate-600">Custos</p>
          <p class="mt-1 text-2xl font-bold text-slate-800">{{ formatMoney(totalCosts) }}</p>
        </div>

        <div class="rounded-xl border-2 p-4" :class="projectedProfit >= 0 ? 'border-emerald-400 bg-emerald-50' : 'border-rose-400 bg-rose-50'">
          <p class="text-xs font-semibold uppercase tracking-wider" :class="projectedProfit >= 0 ? 'text-emerald-700' : 'text-rose-700'">Lucro total</p>
          <p class="mt-1 text-2xl font-bold" :class="projectedProfit >= 0 ? 'text-emerald-800' : 'text-rose-800'">{{ formatMoney(projectedProfit) }}</p>
          <p class="mt-2 text-xs" :class="projectedProfit >= 0 ? 'text-emerald-700' : 'text-rose-700'">Margem: {{ formatPercent(projectedMarginPercent) }}</p>
        </div>
      </div>

      <div v-if="canShowVehicleData" class="surface-card rounded-2xl p-3">
        <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div>
            <label class="field-label">Status</label>
            <div class="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-4">
              <button
                class="flex-1 rounded-lg border-2 px-3 py-2 text-sm font-semibold"
                :class="draft.status === 'em_andamento' ? 'border-amber-500 bg-amber-50 text-amber-800' : 'border-slate-300 bg-white text-slate-700'"
                type="button"
                @click="draft.status = 'em_andamento'"
              >
                Em andamento
              </button>
              <button
                class="flex-1 rounded-lg border-2 px-3 py-2 text-sm font-semibold"
                :class="draft.status === 'adquirido' ? 'border-emerald-500 bg-emerald-50 text-emerald-800' : 'border-slate-300 bg-white text-slate-700'"
                type="button"
                @click="draft.status = 'adquirido'"
              >
                Adquirido
              </button>
              <button
                class="flex-1 rounded-lg border-2 px-3 py-2 text-sm font-semibold"
                :class="draft.status === 'anunciado' ? 'border-sky-500 bg-sky-50 text-sky-800' : 'border-slate-300 bg-white text-slate-700'"
                type="button"
                @click="draft.status = 'anunciado'"
              >
                Anunciado
              </button>
              <button
                class="flex-1 rounded-lg border-2 px-3 py-2 text-sm font-semibold"
                :class="draft.status === 'vendido' ? 'border-slate-500 bg-slate-200 text-slate-700' : 'border-slate-300 bg-white text-slate-700'"
                type="button"
                @click="draft.status = 'vendido'"
              >
                Vendido
              </button>
            </div>

            <label class="field-label mt-3 block">Interessado</label>
            <div class="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-4">
              <button
                class="flex-1 rounded-lg border-2 px-3 py-2 text-sm font-semibold"
                :class="draft.interestedPreset === 'ruan' ? 'border-indigo-500 bg-indigo-50 text-indigo-800' : 'border-slate-300 bg-white text-slate-700'"
                type="button"
                @click="draft.interestedPreset = 'ruan'; draft.interestedOther = ''"
              >
                Ruan
              </button>
              <button
                class="flex-1 rounded-lg border-2 px-3 py-2 text-sm font-semibold"
                :class="draft.interestedPreset === 'vinicius' ? 'border-indigo-500 bg-indigo-50 text-indigo-800' : 'border-slate-300 bg-white text-slate-700'"
                type="button"
                @click="draft.interestedPreset = 'vinicius'; draft.interestedOther = ''"
              >
                Vinicius
              </button>
              <button
                class="flex-1 rounded-lg border-2 px-3 py-2 text-sm font-semibold"
                :class="draft.interestedPreset === 'jhow' ? 'border-indigo-500 bg-indigo-50 text-indigo-800' : 'border-slate-300 bg-white text-slate-700'"
                type="button"
                @click="draft.interestedPreset = 'jhow'; draft.interestedOther = ''"
              >
                Jhow
              </button>
              <button
                class="flex-1 rounded-lg border-2 px-3 py-2 text-sm font-semibold"
                :class="draft.interestedPreset === 'outro' ? 'border-indigo-500 bg-indigo-50 text-indigo-800' : 'border-slate-300 bg-white text-slate-700'"
                type="button"
                @click="draft.interestedPreset = 'outro'"
              >
                Outro
              </button>
            </div>

            <input
              v-if="draft.interestedPreset === 'outro'"
              v-model="draft.interestedOther"
              class="field-input mt-2"
              placeholder="Nome do interessado"
            >
          </div>

          <div>
            <label class="field-label">Observações</label>
            <textarea
              v-model="draft.notes"
              class="field-input mt-2 min-h-24"
              placeholder="Observacoes do veiculo"
            />
          </div>
        </div>

        <div class="mt-4 grid gap-2" :class="isEditingCurrentCar ? 'grid-cols-2' : 'grid-cols-1'">
          <button
            class="w-full rounded-xl bg-emerald-600 py-3 text-base font-bold text-white hover:bg-emerald-700 disabled:opacity-60"
            type="button"
            :disabled="!canSave"
            @click="saveCurrentCar"
          >
            Salvar carro atual
          </button>
          <button
            v-if="isEditingCurrentCar"
            class="inline-flex w-full items-center justify-center gap-1 rounded-xl border border-slate-300 bg-white py-3 text-base font-semibold text-slate-700 hover:bg-slate-100"
            type="button"
            @click="closeCurrentEditor"
          >
            <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M6 18L18 6M6 6l12 12" />
            </svg>
            Fechar edição
          </button>
        </div>
      </div>
    </section>

    <section id="current-cars" class="surface-card rounded-2xl p-3">
      <div class="mb-4 flex items-center justify-between gap-2">
        <h2 class="text-xl font-bold text-slate-900">Carros atuais</h2>
        <span class="text-xs font-semibold uppercase tracking-wider text-slate-500">{{ filteredLocalCars.length }} registros</span>
      </div>

      <template v-if="!showCurrentCarsLoading">
        <div>
          <div class="mb-4">
            <label class="field-label">Filtrar por interessado</label>
            <select v-model="interestedFilter" class="field-input mt-1 h-11">
              <option value="todos">Todos</option>
              <option value="ruan">Ruan</option>
              <option value="vinicius">Vinicius</option>
              <option value="jhow">Jhow</option>
              <option value="outro">Outro</option>
            </select>
          </div>

          <div v-if="filteredLocalCars.length === 0" class="rounded-xl border border-slate-200 bg-white/70 px-3 py-5 text-center text-sm text-slate-600">
            {{ interestedFilter === 'todos' ? 'Nenhum carro atual salvo ainda.' : 'Nenhum carro encontrado para este interessado.' }}
          </div>

          <div v-else class="space-y-4">
            <article
              v-for="item in filteredLocalCars"
              :key="item.id"
              class="overflow-hidden rounded-2xl border shadow-sm transition-all"
              :class="getCarStatus(item) === 'vendido' ? 'border-slate-300 bg-slate-100 grayscale' : 'border-slate-200 bg-white'"
            >
          <div class="relative">
            <img
              v-if="getCarGalleryPhotos(item).length > 0"
              :src="getCarActivePhoto(item)"
              class="h-40 w-full cursor-pointer object-cover"
              alt="Foto do veículo"
              @click="openRecordGalleryModal(item)"
            >
            <div v-else class="flex h-40 w-full items-center justify-center bg-slate-100 text-xs font-semibold text-slate-500">
              Sem foto
            </div>

            <button
              v-if="getCarGalleryPhotos(item).length > 1"
              class="absolute left-2 top-1/2 inline-flex h-8 w-8 -translate-y-1/2 items-center justify-center rounded-full bg-black/45 text-white hover:bg-black/60"
              type="button"
              aria-label="Foto anterior"
              @click.stop="showPrevCarPhoto(item)"
            >
              <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M15 19l-7-7 7-7" />
              </svg>
            </button>
            <button
              v-if="getCarGalleryPhotos(item).length > 1"
              class="absolute right-2 top-1/2 inline-flex h-8 w-8 -translate-y-1/2 items-center justify-center rounded-full bg-black/45 text-white hover:bg-black/60"
              type="button"
              aria-label="Próxima foto"
              @click.stop="showNextCarPhoto(item)"
            >
              <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M9 5l7 7-7 7" />
              </svg>
            </button>

            <span
              class="absolute left-2 top-2 rounded-full px-2 py-1 text-[10px] font-bold uppercase shadow-sm"
              :class="getCarStatusBadgeClass(item)"
            >
              {{ getCarStatusLabel(item) }}
            </span>
            <span class="absolute right-2 top-2 rounded-full bg-slate-900/80 px-2 py-1 text-[10px] font-semibold text-white">
              {{ mountLabel(item.mountClass) }}
            </span>
            <span
              v-if="getCarGalleryPhotos(item).length > 1"
              class="absolute bottom-2 right-2 rounded-md bg-black/60 px-1.5 py-0.5 text-[10px] font-semibold text-white"
            >
              {{ getCarGalleryIndex(item) + 1 }}/{{ getCarGalleryPhotos(item).length }}
            </span>
          </div>

          <div class="space-y-3">
            <div>
              <p class="text-base font-bold text-slate-900">{{ item.plate || 'SEM PLACA' }}</p>
              <p class="truncate text-sm text-slate-600">{{ item.brand }} {{ item.model }} {{ item.year || '' }}</p>
              <p v-if="getInterestedDisplay(item)" class="truncate text-xs font-semibold text-indigo-700">Interessado: {{ getInterestedDisplay(item) }}</p>
            </div>

            <div class="grid grid-cols-2 gap-2 text-xs">
              <div class="rounded-lg bg-slate-50 px-2 py-2">
                <p class="text-[10px] uppercase tracking-wider text-slate-500">Compra</p>
                <p class="font-semibold text-slate-800">{{ formatMoney(item.purchaseValue) }}</p>
              </div>
              <div class="rounded-lg bg-slate-50 px-2 py-2">
                <p class="text-[10px] uppercase tracking-wider text-slate-500">Venda</p>
                <p class="font-semibold text-slate-800">{{ formatMoney(calculateSaleValue(item.fipeValue, item.mountClass)) }}</p>
              </div>
              <div class="rounded-lg bg-slate-50 px-2 py-2">
                <p class="text-[10px] uppercase tracking-wider text-slate-500">Custos</p>
                <p class="font-semibold text-slate-800">{{ formatMoney(item.summary?.totalCosts ?? 0) }}</p>
              </div>
              <div class="rounded-lg px-2 py-2" :class="(item.summary?.expectedProfit ?? 0) >= 0 ? 'bg-emerald-50' : 'bg-rose-50'">
                <p class="text-[10px] uppercase tracking-wider" :class="(item.summary?.expectedProfit ?? 0) >= 0 ? 'text-emerald-600' : 'text-rose-600'">Lucro</p>
                <p class="font-semibold" :class="(item.summary?.expectedProfit ?? 0) >= 0 ? 'text-emerald-700' : 'text-rose-700'">
                  {{ formatMoney(item.summary?.expectedProfit ?? 0) }}
                </p>
              </div>
            </div>

            <div class="grid grid-cols-3 gap-2">
              <button
                class="inline-flex items-center justify-center gap-1 rounded-lg border border-slate-300 px-2 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-100"
                type="button"
                @click="editCurrentCar(item)"
              >
                <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M15 12H9m12 0A9 9 0 11 3 12a9 9 0 0118 0z" />
                </svg>
                Abrir
              </button>
              <button
                v-if="getCarStatus(item) === 'em_andamento'"
                class="inline-flex items-center justify-center gap-1 rounded-lg border border-emerald-300 px-2 py-2 text-xs font-semibold text-emerald-700 hover:bg-emerald-50 disabled:opacity-60"
                type="button"
                :disabled="isUpdatingStatus(item.id)"
                @click="markAsAcquired(item)"
              >
                <div
                  v-if="isUpdatingStatus(item.id)"
                  class="h-3.5 w-3.5 animate-spin rounded-full border-2 border-emerald-700 border-t-transparent"
                />
                <svg v-else class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7" />
                </svg>
                Adquirir
              </button>
              <button
                v-else-if="getCarStatus(item) === 'adquirido'"
                class="inline-flex items-center justify-center gap-1 rounded-lg border border-sky-300 px-2 py-2 text-xs font-semibold text-sky-700 hover:bg-sky-50 disabled:opacity-60"
                type="button"
                :disabled="isUpdatingStatus(item.id)"
                @click="markAsAnnounced(item)"
              >
                <div
                  v-if="isUpdatingStatus(item.id)"
                  class="h-3.5 w-3.5 animate-spin rounded-full border-2 border-sky-700 border-t-transparent"
                />
                <svg v-else class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M4 12h16M12 4v16" />
                </svg>
                Anunciar
              </button>
              <button
                v-else-if="getCarStatus(item) === 'anunciado'"
                class="inline-flex items-center justify-center gap-1 rounded-lg border border-slate-400 px-2 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-100 disabled:opacity-60"
                type="button"
                :disabled="isUpdatingStatus(item.id)"
                @click="markAsSold(item)"
              >
                <div
                  v-if="isUpdatingStatus(item.id)"
                  class="h-3.5 w-3.5 animate-spin rounded-full border-2 border-slate-700 border-t-transparent"
                />
                <svg v-else class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M8 12h8M12 8v8" />
                </svg>
                Vender
              </button>
              <button
                v-else-if="getCarStatus(item) === 'vendido'"
                class="inline-flex items-center justify-center gap-1 rounded-lg border border-cyan-300 px-2 py-2 text-xs font-semibold text-cyan-700 hover:bg-cyan-50 disabled:opacity-60"
                type="button"
                :disabled="isUpdatingStatus(item.id)"
                @click="markAsReactivated(item)"
              >
                <div
                  v-if="isUpdatingStatus(item.id)"
                  class="h-3.5 w-3.5 animate-spin rounded-full border-2 border-cyan-700 border-t-transparent"
                />
                <svg v-else class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M4 4v6h6M20 20v-6h-6" />
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M20 9a8 8 0 00-14.84-4M4 15a8 8 0 0014.84 4" />
                </svg>
                Reativar
              </button>
              <button
                v-else
                class="inline-flex items-center justify-center gap-1 rounded-lg border border-slate-300 bg-slate-100 px-2 py-2 text-xs font-semibold text-slate-600"
                type="button"
                disabled
              >
                <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M12 5v14m-7-7h14" />
                </svg>
                Sem ação
              </button>
              <button
                class="inline-flex items-center justify-center gap-1 rounded-lg border border-rose-300 px-2 py-2 text-xs font-semibold text-rose-700 hover:bg-rose-50"
                type="button"
                @click="removeLocal(item.id)"
              >
                <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M6 18L18 6M6 6l12 12" />
                </svg>
                Excluir
              </button>
            </div>
          </div>
            </article>
          </div>
        </div>

      </template>
    </section>

    <div
      v-if="galleryModalOpen && galleryModalPhotos.length > 0"
      class="fixed inset-0 z-50 bg-slate-950/90 backdrop-blur-sm overflow-hidden"
      @click.self="closeGalleryModal"
    >
      <div class="flex h-full max-h-screen flex-col">
        <div class="flex items-center justify-between px-3 py-3 text-white">
          <p class="text-sm font-semibold">
            {{ galleryModalTitle }}
            <span class="text-xs font-normal text-slate-300">
              ({{ activeGalleryIndex + 1 }}/{{ galleryModalPhotos.length }})
            </span>
          </p>
          <button
            class="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-white/10 hover:bg-white/20"
            type="button"
            aria-label="Fechar galeria"
            @click="closeGalleryModal"
          >
            <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div class="relative min-h-0 flex-1 px-3 pb-3">
          <div class="flex h-full items-center justify-center overflow-hidden rounded-xl bg-slate-900">
            <img
              v-if="activeGalleryPhoto"
              :src="activeGalleryPhoto"
              class="max-h-full max-w-full object-contain"
              alt="Foto da galeria"
            >
          </div>

          <button
            class="absolute left-4 top-1/2 inline-flex h-10 w-10 -translate-y-1/2 items-center justify-center rounded-full bg-white/15 text-white hover:bg-white/25 disabled:opacity-40"
            type="button"
            :disabled="galleryModalPhotos.length <= 1"
            aria-label="Foto anterior"
            @click="showPrevGalleryPhoto"
          >
            <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M15 19l-7-7 7-7" />
            </svg>
          </button>

          <button
            class="absolute right-4 top-1/2 inline-flex h-10 w-10 -translate-y-1/2 items-center justify-center rounded-full bg-white/15 text-white hover:bg-white/25 disabled:opacity-40"
            type="button"
            :disabled="galleryModalPhotos.length <= 1"
            aria-label="Próxima foto"
            @click="showNextGalleryPhoto"
          >
            <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M9 5l7 7-7 7" />
            </svg>
          </button>
        </div>

        <div class="border-t border-white/10 px-2 pb-3 pt-2">
          <div class="flex gap-2 overflow-x-auto">
            <button
              v-for="(photo, idx) in galleryModalPhotos"
              :key="photo + '-thumb-' + idx"
              class="shrink-0 rounded-lg border-2 transition-colors"
              :class="idx === activeGalleryIndex ? 'border-white' : 'border-white/20'"
              type="button"
              @click="setActiveGalleryIndex(idx)"
            >
              <img :src="photo" class="h-14 w-14 rounded-md object-cover" alt="Thumb da galeria">
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useAuctionCarsApi } from '~/composables/useAuctionCarsApi'
import { useIndexedAuctionCars } from '~/composables/useIndexedAuctionCars'
import { calculateAuctionSummary, calculateSaleValue, calculateTotalCosts, normalizePlate } from '@core/shared/valuation'
import type { AuctionCarInterestedPreset, AuctionCarRecord, AuctionCarStatus, CostItem, MountClass, PlateFipeQuotaInfo } from '@core/shared/types/auction'


type CarStatus = 'em_andamento' | 'adquirido' | 'anunciado' | 'vendido'
type InterestedPreset = AuctionCarInterestedPreset | ''
type InterestedFilter = 'todos' | AuctionCarInterestedPreset

type DraftState = {
  id: string
  plate: string
  photoDataUrl: string
  plateCropDataUrl: string
  galleryPhotos: string[]
  brand: string
  model: string
  year: number | null
  km: number | null
  fipeValue: number
  purchaseValue: number
  purchaseOverrideEnabled: boolean
  costs: CostItem[]
  targetMarginPercent: number
  mountClass: MountClass
  interestedPreset: InterestedPreset
  interestedOther: string
  notes: string
  status: CarStatus
  createdAt: string | null
}

type CostOption = {
  value: string
  label: string
  defaultAmount?: number
}

type OcrCandidateDetail = {
  plate: string
  confidence: number
  bbox: [number, number, number, number] | null
}

const AUTO_MOUNT_COST_ID = 'auto-mount-cost'
const INTERESTED_PRESET_LABELS: Record<AuctionCarInterestedPreset, string> = {
  ruan: 'Ruan',
  vinicius: 'Vinicius',
  jhow: 'Jhow',
  outro: 'Outro',
}

const createId = () => {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return Math.random().toString(36).slice(2, 12)
}

const moneyFormatter = new Intl.NumberFormat('pt-BR', {
  style: 'currency',
  currency: 'BRL',
  maximumFractionDigits: 2,
})

const percentFormatter = new Intl.NumberFormat('pt-BR', {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
})

const moneyInputFormatter = new Intl.NumberFormat('pt-BR', {
  style: 'currency',
  currency: 'BRL',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})

const MAX_COST_AMOUNT = 10_000_000
const buildCostValuePresets = () => {
  const base = [200, 500, 700, 1000]
  const stepped = Array.from({ length: ((50_000 - 1_500) / 500) + 1 }, (_, index) => 1_500 + (index * 500))
  return [...base, ...stepped]
}

const costValuePresets = buildCostValuePresets()

const suggestMarginByFipe = (fipeValue: number) => {
  if (!Number.isFinite(fipeValue) || fipeValue <= 0) return 10000
  if (fipeValue <= 30000) return 5000
  if (fipeValue <= 80000) return 10000
  if (fipeValue <= 120000) return 30000
  if (fipeValue <= 160000) return 40000
  const extraBlocks = Math.ceil((fipeValue - 160000) / 40000)
  return 40000 + extraBlocks * 10000
}

const resolveMountCostLabel = (mountClass: MountClass) => {
  if (mountClass === 'sem_monta') return 'Tipo monta (Sem)'
  if (mountClass === 'pequena') return 'Tipo monta (Pequena)'
  return 'Tipo monta (Media)'
}

const resolveMountCostAmount = (mountClass: MountClass, fipeValue: number) => {
  if (mountClass === 'sem_monta') return 0

  const fipe = Number(fipeValue) || 0
  if (mountClass === 'pequena') {
    if (fipe <= 0) return 800
    return getCostValueByFipe(fipe, [
      [50000, 800],
      [120000, 1500],
      [200000, 2500],
    ])
  }

  if (fipe <= 0) return 2500
  return getCostValueByFipe(fipe, [
    [50000, 2500],
    [120000, 4500],
    [200000, 7000],
  ])
}

const getDefaultCosts = (mountClass: MountClass = 'pequena', fipeValue = 0): CostItem[] => {
  const costs: CostItem[] = []

  if (mountClass !== 'sem_monta') {
    costs.push({ id: createId(), label: 'Leilao', amount: 800 })
  }

  costs.push({
    id: AUTO_MOUNT_COST_ID,
    label: resolveMountCostLabel(mountClass),
    amount: resolveMountCostAmount(mountClass, fipeValue),
  })

  return costs
}

const createEmptyDraft = (): DraftState => ({
  id: createId(),
  plate: '',
  photoDataUrl: '',
  plateCropDataUrl: '',
  galleryPhotos: [],
  brand: '',
  model: '',
  year: null,
  km: null,
  fipeValue: 0,
  purchaseValue: 0,
  purchaseOverrideEnabled: false,
  costs: getDefaultCosts('pequena'),
  targetMarginPercent: 0,
  mountClass: 'pequena',
  interestedPreset: '',
  interestedOther: '',
  notes: '',
  status: 'em_andamento',
  createdAt: null,
})

const getCostValueByFipe = (fipe: number, ranges: [number, number][]) => {
  if (!Number.isFinite(fipe) || fipe <= 0 || ranges.length === 0) return 0
  for (const [limit, value] of ranges) {
    if (fipe <= limit) return value
  }
  const lastRange = ranges[ranges.length - 1]
  return lastRange ? lastRange[1] : 0
}

const costTypeOptions: CostOption[] = [
  { value: 'leilao', label: 'Leilão', defaultAmount: 800 },
  { value: 'documentacao', label: 'Documentação' },
  { value: 'frente-motor', label: 'Frente com motor', defaultAmount: 5000 },
  { value: 'frente-sem-motor', label: 'Frente sem motor', defaultAmount: 2000 },
  { value: 'traseira-pintura', label: 'Traseira pintura', defaultAmount: 1500 },
  { value: 'traseira-troca', label: 'Traseira troca', defaultAmount: 3500 },
  { value: 'lateral-portas', label: 'Lateral + portas', defaultAmount: 5000 },
  { value: 'guincho', label: 'Guincho', defaultAmount: 200 },
  { value: 'parabrisas', label: 'Parabrisa' },
  { value: 'frente-pecas', label: 'Frente peças' },
  { value: 'farol', label: 'Farol' },
  { value: 'kit-airbag', label: 'Kit airbag' },
  { value: 'portas-lateral', label: '2 Portas lateral' },
  { value: 'traseira-completa', label: 'Traseira completa' },
  { value: 'jogo-pneus', label: 'Jogo de pneus' },
  { value: 'pintura', label: 'Pintura' },
  { value: 'mecanica', label: 'Mecânica' },
  { value: 'suspensao', label: 'Suspensão' },
  { value: 'vidros', label: 'Vidros' },
  { value: 'eletrica', label: 'Elétrica' },
  { value: 'outros', label: 'Outros' },
]

const fipeDynamicCosts: Record<string, [number, number][]> = {
  parabrisas: [[50000, 800], [120000, 1200], [200000, 1700]],
  'frente-pecas': [[50000, 2500], [120000, 4500], [200000, 6000]],
  farol: [[50000, 800], [120000, 2000], [200000, 4500]],
  'kit-airbag': [[50000, 3500], [120000, 6000], [200000, 9000]],
  'portas-lateral': [[50000, 1200], [120000, 2800], [200000, 3800]],
  'traseira-completa': [[50000, 3000], [120000, 5000], [200000, 8000]],
  'jogo-pneus': [[50000, 2000], [120000, 3000], [200000, 4000]],
}

const draft = reactive<DraftState>(createEmptyDraft())
const localCars = ref<AuctionCarRecord[]>([])

const loadingLookup = ref(false)
const processingOcr = ref(false)
const ocrProgress = ref(0)
const ocrStage = ref('')
const ocrNotFound = ref(false)

const OCR_STAGE_LABELS: Record<string, string> = {
  decode: 'Decodificando imagem...',
  yolo_load: 'Carregando detector...',
  yolo_predict: 'Detectando placa...',
  yolo_ocr: 'Lendo caracteres (YOLO)...',
  yolo_skipped: 'Detector indisponível...',
  contour: 'Analisando contornos...',
  fallback: 'Buscando regiões alternativas...',
  rescue: 'Tentando recuperação...',
  rerank: 'Ranqueando candidatos...',
  done: 'Concluído!',
}

const ocrStageLabel = computed(() => OCR_STAGE_LABELS[ocrStage.value] ?? 'Processando...')

const addingCost = ref(false)
const plateCandidates = ref<string[]>([])
const plateCandidateDetails = ref<OcrCandidateDetail[]>([])

const statusMessage = ref('')
const statusTone = ref<'ok' | 'warn' | 'error'>('ok')
const marginWasEdited = ref(false)
const targetMarginValue = ref(10000)
const plateCheckAttempted = ref(false)

const newCostType = ref<string>('documentacao')
const newCostAmount = ref<number>(0)
const newCostOtherLabel = ref('')

const primaryCameraInputRef = ref<HTMLInputElement | null>(null)
const additionalGalleryInputRef = ref<HTMLInputElement | null>(null)

const indexedDb = useIndexedAuctionCars()
const api = useAuctionCarsApi()

const savedCarsCount = useState<number>('savedCarsCount', () => 0)
const triggerSavedCars = useState<number>('triggerSavedCars', () => 0)
const triggerStep1 = useState<number>('triggerStep1', () => 0)
const plateFipeQuota = useState<PlateFipeQuotaInfo | null>('plateFipeQuota', () => null)
const plateFipeQuotaLoading = useState<boolean>('plateFipeQuotaLoading', () => false)
const plateFipeQuotaError = useState<string>('plateFipeQuotaError', () => '')
const galleryModalOpen = ref(false)
const galleryModalTitle = ref('Galeria do veículo')
const galleryModalPhotos = ref<string[]>([])
const activeGalleryIndex = ref(0)
const carGalleryIndexes = ref<Record<string, number>>({})
const updatingStatusIds = ref<Record<string, boolean>>({})
const isEditingCurrentCar = ref(false)
const interestedFilter = ref<InterestedFilter>('todos')
const isClientMounted = ref(false)

const totalCosts = computed(() => calculateTotalCosts(draft.costs))
const showCurrentCarsLoading = computed(() => import.meta.server || !isClientMounted.value)
const displayPhotoSrc = computed(() => draft.plateCropDataUrl || draft.photoDataUrl || '')
const isPlateFocusedPreview = computed(() => Boolean(draft.plateCropDataUrl))
const canShowVehicleData = computed(() => plateCheckAttempted.value && !loadingLookup.value)
const activeGalleryPhoto = computed(() => {
  if (galleryModalPhotos.value.length === 0) return ''
  const index = Math.max(0, Math.min(activeGalleryIndex.value, galleryModalPhotos.value.length - 1))
  return galleryModalPhotos.value[index] || ''
})

const saleDiscountLabel = computed(() => {
  if (draft.mountClass === 'sem_monta') return 'FIPE - 0%'
  if (draft.mountClass === 'pequena') return 'FIPE - 5%'
  return 'FIPE - 20%'
})

const autoPurchaseValue = computed(() => {
  const value = Number(draft.fipeValue) - Number(targetMarginValue.value) - Number(totalCosts.value)
  return Math.max(0, Number.isFinite(value) ? value : 0)
})

const effectivePurchaseValue = computed(() => {
  if (!draft.purchaseOverrideEnabled) return autoPurchaseValue.value
  const manual = Number(draft.purchaseValue)
  return Math.max(0, Number.isFinite(manual) ? manual : 0)
})

const estimatedSaleValue = computed(() => calculateSaleValue(Number(draft.fipeValue), draft.mountClass))

const projectedProfit = computed(() => {
  return estimatedSaleValue.value - (effectivePurchaseValue.value + Number(totalCosts.value))
})

const projectedMarginPercent = computed(() => {
  if (estimatedSaleValue.value <= 0) return 0
  return (projectedProfit.value / estimatedSaleValue.value) * 100
})

const canSave = computed(() => {
  return Boolean(draft.plate || draft.brand || draft.model)
})

const filteredLocalCars = computed(() => {
  const selectedFilter = interestedFilter.value
  if (selectedFilter === 'todos') return localCars.value

  return localCars.value.filter((record) => {
    const preset = normalizeInterestedPreset(record.interestedPreset, record.interested)
    return preset === selectedFilter
  })
})

watch(triggerSavedCars, () => {
  scrollToCurrentCars()
})

watch(triggerStep1, () => {
  window.scrollTo({ top: 0, behavior: 'smooth' })
})

watch(
  () => draft.fipeValue,
  () => {
    if (!marginWasEdited.value || targetMarginValue.value <= 0) {
      targetMarginValue.value = suggestMarginByFipe(draft.fipeValue)
    }
    ensureMountDynamicCost(draft.mountClass, draft.fipeValue)
    onCostTypeChange()
  },
)

watch(
  () => draft.mountClass,
  (mountClass) => {
    ensureLeilaoCostByMount(mountClass)
    ensureMountDynamicCost(mountClass, draft.fipeValue)
  },
  { immediate: true },
)

const mountLabel = (mountClass: MountClass) => {
  if (mountClass === 'sem_monta') return 'Sem monta'
  if (mountClass === 'pequena') return 'Pequena monta'
  return 'Média monta'
}

const normalizeCarStatus = (value: unknown): CarStatus => {
  const normalized = String(value || '')
    .trim()
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')

  if (normalized === 'em_andamento' || normalized === 'em andamento' || normalized === 'em_avaliacao' || normalized === 'em avaliacao') {
    return 'em_andamento'
  }

  if (normalized === 'anunciado' || normalized === 'anunciar') {
    return 'anunciado'
  }

  if (normalized === 'vendido' || normalized === 'venda concluida') {
    return 'vendido'
  }

  if (normalized === 'reativado' || normalized === 'reativar') {
    return 'em_andamento'
  }

  if (normalized === 'adquirido' || normalized === 'comprado' || normalized === 'carro comprado') {
    return 'adquirido'
  }

  return 'em_andamento'
}

const normalizeInterestedPreset = (
  presetValue: unknown,
  interestedValue?: string,
): AuctionCarInterestedPreset | null => {
  const preset = String(presetValue || '').trim().toLowerCase()
  if (preset === 'ruan' || preset === 'vinicius' || preset === 'jhow' || preset === 'outro') {
    return preset
  }

  const normalizedInterested = String(interestedValue || '')
    .trim()
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')

  if (normalizedInterested === 'ruan') return 'ruan'
  if (normalizedInterested === 'vinicius') return 'vinicius'
  if (normalizedInterested === 'jhow') return 'jhow'
  if (normalizedInterested) return 'outro'

  return null
}

const resolveInterestedFromDraft = () => {
  if (draft.interestedPreset === 'ruan' || draft.interestedPreset === 'vinicius' || draft.interestedPreset === 'jhow') {
    return {
      preset: draft.interestedPreset,
      name: INTERESTED_PRESET_LABELS[draft.interestedPreset],
    }
  }

  if (draft.interestedPreset === 'outro') {
    const customName = draft.interestedOther.trim()
    return {
      preset: 'outro' as AuctionCarInterestedPreset,
      name: customName,
    }
  }

  return {
    preset: null,
    name: '',
  }
}

const getInterestedDisplay = (record: AuctionCarRecord) => {
  const customName = String(record.interested || '').trim()
  const preset = normalizeInterestedPreset(record.interestedPreset, customName)

  if (preset === 'ruan' || preset === 'vinicius' || preset === 'jhow') {
    return INTERESTED_PRESET_LABELS[preset]
  }

  if (preset === 'outro') {
    return customName || INTERESTED_PRESET_LABELS.outro
  }

  return ''
}

const getCarStatus = (record: AuctionCarRecord): CarStatus => normalizeCarStatus(record.status)
const getCarStatusLabel = (record: AuctionCarRecord) => {
  const status = getCarStatus(record)
  if (status === 'vendido') return 'Vendido'
  if (status === 'anunciado') return 'Anunciado'
  if (status === 'adquirido') return 'Adquirido'
  return 'Em andamento'
}

const getCarStatusBadgeClass = (record: AuctionCarRecord) => {
  const status = getCarStatus(record)
  if (status === 'vendido') return 'bg-slate-200 text-slate-700'
  if (status === 'anunciado') return 'bg-sky-100 text-sky-700'
  if (status === 'adquirido') return 'bg-emerald-100 text-emerald-700'
  return 'bg-amber-100 text-amber-700'
}
const isUpdatingStatus = (id: string) => Boolean(updatingStatusIds.value[id])

const setUpdatingStatus = (id: string, isUpdating: boolean) => {
  if (isUpdating) {
    updatingStatusIds.value = { ...updatingStatusIds.value, [id]: true }
  } else {
    updatingStatusIds.value = Object.fromEntries(
      Object.entries(updatingStatusIds.value).filter(([key]) => key !== id),
    )
  }
}

const isAutoMountCost = (cost: CostItem) => cost.id === AUTO_MOUNT_COST_ID

const setStatus = (message: string, tone: 'ok' | 'warn' | 'error' = 'ok') => {
  statusMessage.value = message
  statusTone.value = tone
}

const formatMoney = (value: number) => moneyFormatter.format(Number(value) || 0)
const formatPercent = (value: number) => `${percentFormatter.format(Number(value) || 0)}%`
const clampCostAmount = (value: number) => Math.min(MAX_COST_AMOUNT, Math.max(0, Number(value) || 0))
const formatMoneyInput = (value: number) => moneyInputFormatter.format(clampCostAmount(value))

const parseMoneyInput = (rawValue: string) => {
  const normalized = String(rawValue || '')
    .replace(/\s/g, '')
    .replace(/[R$r$]/g, '')
    .replace(/\./g, '')
    .replace(',', '.')
    .replace(/[^0-9.-]/g, '')
    .trim()

  const parsed = Number(normalized)
  if (!Number.isFinite(parsed)) return 0
  return clampCostAmount(parsed)
}

const normalizeBbox = (bbox: unknown): [number, number, number, number] | null => {
  if (!Array.isArray(bbox) || bbox.length !== 4) return null
  const parsed = bbox.map((value) => Math.round(Number(value)))
  if (parsed.some((value) => !Number.isFinite(value))) return null
  const [x1, y1, x2, y2] = parsed as [number, number, number, number]
  if (x2 <= x1 || y2 <= y1) return null
  return [x1, y1, x2, y2]
}

const readErrorMessage = (error: unknown) => {
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
        ? `OCR indisponível: conexão recusada em ${targetBaseUrl}.`
        : 'OCR indisponível: conexão recusada.'
    }

    if (maybeData?.statusMessage) return maybeData.statusMessage
    if (maybeData?.message) return maybeData.message
  }

  if (error instanceof Error && error.message) return error.message
  return 'Falha na operação.'
}

const loadImageElement = (dataUrl: string) =>
  new Promise<HTMLImageElement>((resolve, reject) => {
    const image = new Image()
    image.onload = () => resolve(image)
    image.onerror = (event) => reject(event)
    image.src = dataUrl
  })

const OCR_IMAGE_MAX_SIDE = 1600
const OCR_IMAGE_QUALITY = 0.82

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

const buildPlateCropPayload = async (photoDataUrl: string, bbox: [number, number, number, number] | null) => {
  if (!bbox || !photoDataUrl) return ''

  try {
    const image = await loadImageElement(photoDataUrl)
    const width = image.naturalWidth || image.width
    const height = image.naturalHeight || image.height
    if (!width || !height) return ''

    const [bx1, by1, bx2, by2] = bbox
    const rawW = Math.max(1, bx2 - bx1)
    const rawH = Math.max(1, by2 - by1)
    const padX = Math.max(10, Math.round(rawW * 0.28))
    const padYTop = Math.max(12, Math.round(rawH * 0.40))
    const padYBottom = Math.max(10, Math.round(rawH * 0.24))

    const x1 = Math.max(0, bx1 - padX)
    const y1 = Math.max(0, by1 - padYTop)
    const x2 = Math.min(width, bx2 + padX)
    const y2 = Math.min(height, by2 + padYBottom)
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
    if (!context) return ''

    context.drawImage(image, x1, y1, cropW, cropH, 0, 0, targetW, targetH)
    return canvas.toDataURL('image/jpeg', 0.9)
  } catch {
    return ''
  }
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

const resolveCandidateDetails = (candidates: Array<{ plate?: string; confidence?: number; bbox?: unknown }>) => {
  const result: OcrCandidateDetail[] = []
  const seen = new Set<string>()

  for (const candidate of candidates) {
    const plate = normalizePlate(candidate?.plate || '')
    if (!plate || seen.has(plate)) continue
    seen.add(plate)
    result.push({
      plate,
      confidence: Number(candidate?.confidence ?? 0),
      bbox: normalizeBbox(candidate?.bbox),
    })
  }

  return result
}

// --- OCR streaming via SSE ---
type OcrStreamResponse = {
  ok: boolean
  input: Record<string, unknown>
  result: {
    plate: string | null
    confidence: number
    bbox: number[] | null
    candidates: Array<{ plate: string; confidence: number; bbox: number[] | null; source: string }>
  }
  requestId?: string
}

const streamPlateOcr = async (payload: { imageBase64: string; filename?: string; requestId?: string }): Promise<OcrStreamResponse> => {
  const res = await fetch('/api/v1/plate/recognize-stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

  if (!res.ok || !res.body) {
    throw new Error(`OCR stream falhou: HTTP ${res.status}`)
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''
    for (const line of lines) {
      if (!line.startsWith('data: ')) continue
      const data = JSON.parse(line.slice(6)) as Record<string, unknown>
      if (data.error) throw new Error(String(data.error))
      if (typeof data.progress === 'number') ocrProgress.value = data.progress
      if (typeof data.stage === 'string') ocrStage.value = data.stage
      if (data.stage === 'done') return data as unknown as OcrStreamResponse
    }
  }

  throw new Error('SSE encerrado sem resultado')
}

const extractPlateFromPhoto = async (imageBase64: string) => {
  processingOcr.value = true

  try {
    const response = await streamPlateOcr({
      imageBase64,
      filename: 'camera-upload',
      requestId: createId(),
    })

    const candidates = Array.isArray(response.result.candidates) ? response.result.candidates : []
    const details = resolveCandidateDetails(candidates)
    const dedupedCandidates = Array.from(new Set(details.map((item) => item.plate))).slice(0, 3)

    plateCandidateDetails.value = details
    plateCandidates.value = dedupedCandidates

    const firstCandidate = dedupedCandidates[0] || normalizePlate(response.result.plate || '')
    ocrNotFound.value = !firstCandidate
    if (firstCandidate) {
      draft.plate = firstCandidate
    }

    const primaryDetail = details.find((item) => item.plate === firstCandidate) || details[0]
    const cropDataUrl = await buildPlateCropPayload(imageBase64, primaryDetail?.bbox || null)
    draft.plateCropDataUrl = cropDataUrl

    if (firstCandidate) {
      if (dedupedCandidates.length > 1) {
        setStatus(`OCR sugeriu ${dedupedCandidates.length} placas. Confirme e toque Check.`, 'warn')
      } else {
        setStatus(`Placa sugerida: ${firstCandidate}. Toque Check para consultar FIPE.`, 'ok')
      }
    } else {
      setStatus('OCR não identificou placa na imagem.', 'warn')
    }
  } catch (error) {
    plateCandidates.value = []
    plateCandidateDetails.value = []
    ocrNotFound.value = false
    setStatus(readErrorMessage(error), 'error')
  } finally {
    ocrProgress.value = 100
    ocrStage.value = 'done'
    await new Promise(resolve => setTimeout(resolve, 220))
    processingOcr.value = false
    ocrProgress.value = 0
    ocrStage.value = ''
  }
}

const lookupVehicleByPlate = async (plate: string) => {
  const normalizedPlate = normalizePlate(plate)
  if (!normalizedPlate) {
    setStatus('Informe uma placa válida para consulta.', 'warn')
    return
  }

  draft.plate = normalizedPlate
  plateCheckAttempted.value = true
  loadingLookup.value = true

  try {
    const lookup = await api.lookupPlateAndFipe({ plate: normalizedPlate })
    const { result, warning, detail, quota, cache } = lookup

    plateFipeQuota.value = quota || plateFipeQuota.value

    draft.brand = String(result.brand || '').trim()
    draft.model = String(result.model || '').trim()
    draft.year = typeof result.year === 'number' ? result.year : null
    draft.fipeValue = Number(result.fipeValue) || 0

    const cacheHint = cache.hit ? ' (cache).' : ''
    const providerWarning = [warning, detail].filter(Boolean).join(' ')

    if (providerWarning) {
      setStatus(`Placa ${normalizedPlate} consultada. ${providerWarning}${cacheHint}`, 'warn')
    } else if (draft.fipeValue <= 0) {
      setStatus(`Placa ${normalizedPlate} encontrada, sem FIPE no retorno.${cacheHint}`, 'warn')
    } else {
      setStatus(`Placa ${normalizedPlate} consultada com sucesso${cacheHint}`, 'ok')
    }
  } catch (error) {
    setStatus(`Falha na consulta FIPE: ${readErrorMessage(error)}`, 'error')
  } finally {
    loadingLookup.value = false
  }
}

const triggerCameraCapture = () => {
  primaryCameraInputRef.value?.click()
}

const triggerAdditionalGalleryUpload = () => {
  additionalGalleryInputRef.value?.click()
}

const readFileAsDataUrl = (file: File) =>
  new Promise<string>((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result || ''))
    reader.onerror = () => reject(reader.error)
    reader.readAsDataURL(file)
  })

const onPrimaryPhotoSelected = async (event: Event) => {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return

  if (file.size > 6_000_000) {
    setStatus('Imagem grande demais. Use foto até 6MB.', 'warn')
    return
  }

  try {
    const dataUrl = await readFileAsDataUrl(file)
    const optimized = await optimizeImageForOcr(dataUrl)

    plateCheckAttempted.value = false
    ocrNotFound.value = false
    draft.photoDataUrl = optimized
    if (!draft.galleryPhotos.includes(optimized)) {
      // Mantem apenas fotos extras na galeria, sem duplicar a principal.
      draft.galleryPhotos = draft.galleryPhotos.filter((item) => item !== optimized)
    }

    await extractPlateFromPhoto(optimized)
  } catch (error) {
    setStatus(`Falha ao carregar foto: ${readErrorMessage(error)}`, 'error')
  }
}

const onAdditionalPhotosSelected = async (event: Event) => {
  const input = event.target as HTMLInputElement
  const files = Array.from(input.files || [])
  input.value = ''
  if (files.length === 0) return

  for (const file of files) {
    try {
      const dataUrl = await readFileAsDataUrl(file)
      if (!draft.galleryPhotos.includes(dataUrl)) {
        draft.galleryPhotos.push(dataUrl)
      }
    } catch {
      // ignora arquivo inválido
    }
  }

  setStatus('Fotos adicionadas à galeria do veículo.', 'ok')
}

const removeAdditionalPhoto = (index: number) => {
  if (index < 0 || index >= draft.galleryPhotos.length) return
  draft.galleryPhotos.splice(index, 1)
  if (draft.galleryPhotos.length === 0) {
    closeGalleryModal()
  } else if (activeGalleryIndex.value >= draft.galleryPhotos.length) {
    activeGalleryIndex.value = draft.galleryPhotos.length - 1
  }
  setStatus('Foto removida da galeria.', 'warn')
}

const openGalleryModalWithPhotos = (photos: string[], index = 0, title = 'Galeria do veículo') => {
  const normalizedPhotos = Array.from(new Set((photos || []).filter(Boolean)))
  if (normalizedPhotos.length === 0) return
  galleryModalPhotos.value = normalizedPhotos
  galleryModalTitle.value = title
  activeGalleryIndex.value = Math.max(0, Math.min(index, normalizedPhotos.length - 1))
  galleryModalOpen.value = true
}

const openGalleryModal = (index: number) => {
  openGalleryModalWithPhotos(draft.galleryPhotos, index, 'Galeria do veículo')
}

// --- Photo pinch-zoom & pan ---
const photoScale = ref(1)
const photoTx = ref(0)
const photoTy = ref(0)
const photoAnimated = ref(false)

const photoTransformStyle = computed(() => ({
  transform: `translate(${photoTx.value}px, ${photoTy.value}px) scale(${photoScale.value})`,
  transformOrigin: 'center center',
  transition: photoAnimated.value ? 'transform 0.25s ease' : 'none',
  willChange: 'transform',
}))

let _pinchInitDist = 0
let _pinchInitScale = 1
let _isPinching = false
let _panStartX = 0
let _panStartY = 0
let _panInitTx = 0
let _panInitTy = 0
let _isPanning = false
let _lastTapMs = 0

const _pinchDist = (t1: Touch, t2: Touch) => {
  const dx = t1.clientX - t2.clientX
  const dy = t1.clientY - t2.clientY
  return Math.sqrt(dx * dx + dy * dy)
}

const _clampPhotoPan = () => {
  const limit = (photoScale.value - 1) * 220
  photoTx.value = Math.max(-limit, Math.min(limit, photoTx.value))
  photoTy.value = Math.max(-limit, Math.min(limit, photoTy.value))
}

const resetPhotoZoom = () => {
  photoAnimated.value = true
  photoScale.value = 1
  photoTx.value = 0
  photoTy.value = 0
  setTimeout(() => { photoAnimated.value = false }, 300)
}

const onPhotoTouchStart = (e: TouchEvent) => {
  photoAnimated.value = false
  if (e.touches.length === 2) {
    _isPinching = true
    _isPanning = false
    _pinchInitDist = _pinchDist(e.touches[0]!, e.touches[1]!)
    _pinchInitScale = photoScale.value
    e.preventDefault()
  } else if (e.touches.length === 1) {
    const now = Date.now()
    if (now - _lastTapMs < 280) {
      resetPhotoZoom()
      _lastTapMs = 0
      e.preventDefault()
      return
    }
    _lastTapMs = now
    if (photoScale.value > 1) {
      _isPanning = true
      _panStartX = e.touches[0]!.clientX
      _panStartY = e.touches[0]!.clientY
      _panInitTx = photoTx.value
      _panInitTy = photoTy.value
      e.preventDefault()
    }
  }
}

const onPhotoTouchMove = (e: TouchEvent) => {
  if (e.touches.length === 2 && _isPinching) {
    e.preventDefault()
    const dist = _pinchDist(e.touches[0]!, e.touches[1]!)
    photoScale.value = Math.max(1, Math.min(5, _pinchInitScale * (dist / _pinchInitDist)))
    if (photoScale.value <= 1) { photoTx.value = 0; photoTy.value = 0 }
  } else if (e.touches.length === 1 && _isPanning) {
    e.preventDefault()
    photoTx.value = _panInitTx + (e.touches[0]!.clientX - _panStartX)
    photoTy.value = _panInitTy + (e.touches[0]!.clientY - _panStartY)
    _clampPhotoPan()
  }
}

const onPhotoTouchEnd = (e: TouchEvent) => {
  if (_isPinching && e.touches.length < 2) {
    _isPinching = false
    if (photoScale.value < 1.15) resetPhotoZoom()
    else _clampPhotoPan()
  }
  if (e.touches.length === 0) _isPanning = false
}

const openOriginalPhotoModal = () => {
  if (photoScale.value > 1.05) return
  const original = draft.photoDataUrl
  if (!original) return
  const photos = draft.plateCropDataUrl ? [original, draft.plateCropDataUrl] : [original]
  openGalleryModalWithPhotos(photos, 0, 'Foto original')
}

watch(() => draft.photoDataUrl, () => resetPhotoZoom())

const closeGalleryModal = () => {
  galleryModalOpen.value = false
  galleryModalTitle.value = 'Galeria do veículo'
  galleryModalPhotos.value = []
  activeGalleryIndex.value = 0
}

const setActiveGalleryIndex = (index: number) => {
  if (galleryModalPhotos.value.length === 0) return
  activeGalleryIndex.value = Math.max(0, Math.min(index, galleryModalPhotos.value.length - 1))
}

const showPrevGalleryPhoto = () => {
  const total = galleryModalPhotos.value.length
  if (total <= 1) return
  activeGalleryIndex.value = (activeGalleryIndex.value - 1 + total) % total
}

const showNextGalleryPhoto = () => {
  const total = galleryModalPhotos.value.length
  if (total <= 1) return
  activeGalleryIndex.value = (activeGalleryIndex.value + 1) % total
}

const getCarGalleryPhotos = (record: AuctionCarRecord) => {
  const gallery = Array.isArray(record.galleryPhotos) ? record.galleryPhotos.filter(Boolean) : []
  if (gallery.length > 0) return gallery
  const fallback = record.plateCropDataUrl || record.photoDataUrl || ''
  return fallback ? [fallback] : []
}

const getCarGalleryIndex = (record: AuctionCarRecord) => {
  const photos = getCarGalleryPhotos(record)
  if (photos.length === 0) return 0

  const current = Number(carGalleryIndexes.value[record.id] || 0)
  if (!Number.isFinite(current) || current < 0 || current >= photos.length) {
    carGalleryIndexes.value = { ...carGalleryIndexes.value, [record.id]: 0 }
    return 0
  }
  return current
}

const setCarGalleryIndex = (recordId: string, nextIndex: number, total: number) => {
  if (total <= 0) return
  const normalized = ((nextIndex % total) + total) % total
  carGalleryIndexes.value = { ...carGalleryIndexes.value, [recordId]: normalized }
}

const getCarActivePhoto = (record: AuctionCarRecord) => {
  const photos = getCarGalleryPhotos(record)
  if (photos.length === 0) return ''
  return photos[getCarGalleryIndex(record)] || ''
}

const showPrevCarPhoto = (record: AuctionCarRecord) => {
  const photos = getCarGalleryPhotos(record)
  if (photos.length <= 1) return
  setCarGalleryIndex(record.id, getCarGalleryIndex(record) - 1, photos.length)
}

const showNextCarPhoto = (record: AuctionCarRecord) => {
  const photos = getCarGalleryPhotos(record)
  if (photos.length <= 1) return
  setCarGalleryIndex(record.id, getCarGalleryIndex(record) + 1, photos.length)
}

const openRecordGalleryModal = (record: AuctionCarRecord) => {
  const photos = getCarGalleryPhotos(record)
  if (photos.length === 0) return
  openGalleryModalWithPhotos(
    photos,
    getCarGalleryIndex(record),
    record.plate ? `Galeria - ${record.plate}` : 'Galeria do veículo',
  )
}

const lookupCurrentPlate = async () => {
  await lookupVehicleByPlate(draft.plate)
}

const applyPlateCandidate = async (candidate: string) => {
  draft.plate = normalizePlate(candidate)
  await lookupCurrentPlate()
}

const onPlateInput = (event: Event) => {
  const input = event.target as HTMLInputElement
  draft.plate = normalizePlate(input.value)
}

const onMarginInput = () => {
  marginWasEdited.value = true
}

const applySuggestedMargin = () => {
  targetMarginValue.value = suggestMarginByFipe(draft.fipeValue)
  marginWasEdited.value = false
}

function findLeilaoCostIndex() {
  return draft.costs.findIndex((item) => item.label.trim().toLowerCase() === 'leilao')
}

function ensureLeilaoCostByMount(mountClass: MountClass) {
  const leilaoIndex = findLeilaoCostIndex()

  if (mountClass === 'sem_monta') {
    if (leilaoIndex !== -1) draft.costs.splice(leilaoIndex, 1)
    return
  }

  if (leilaoIndex === -1) {
    draft.costs.unshift({ id: createId(), label: 'Leilao', amount: 800 })
  }
}

function ensureMountDynamicCost(mountClass: MountClass, fipeValue: number) {
  const amount = resolveMountCostAmount(mountClass, fipeValue)
  const label = resolveMountCostLabel(mountClass)

  const index = draft.costs.findIndex((item) => item.id === AUTO_MOUNT_COST_ID)
  if (index === -1) {
    draft.costs.push({
      id: AUTO_MOUNT_COST_ID,
      label,
      amount,
    })
    return
  }

  draft.costs[index] = {
    ...draft.costs[index],
    id: AUTO_MOUNT_COST_ID,
    label,
    amount,
  }
}

const toggleCostAdd = () => {
  addingCost.value = !addingCost.value
  if (!addingCost.value) {
    newCostType.value = 'documentacao'
    newCostAmount.value = 0
    newCostOtherLabel.value = ''
  }
}

const onCostTypeChange = () => {
  const option = costTypeOptions.find((item) => item.value === newCostType.value)
  const fipe = Number(draft.fipeValue) || 0

  const dynamic = fipeDynamicCosts[newCostType.value]
  if (dynamic) {
    newCostAmount.value = clampCostAmount(getCostValueByFipe(fipe, dynamic))
    return
  }

  if (option?.defaultAmount) {
    newCostAmount.value = clampCostAmount(option.defaultAmount)
    return
  }

  newCostAmount.value = 0
}

const resolveCostLabel = () => {
  if (newCostType.value === 'outros') return newCostOtherLabel.value.trim()
  return costTypeOptions.find((item) => item.value === newCostType.value)?.label || ''
}

const addCostItem = () => {
  if (draft.mountClass === 'sem_monta' && newCostType.value === 'leilao') {
    setStatus('Sem monta não adiciona custo de Leilão.', 'warn')
    return
  }

  const label = resolveCostLabel()
  const amount = clampCostAmount(newCostAmount.value)

  if (!label) {
    setStatus('Informe o nome do custo.', 'warn')
    return
  }

  if (amount <= 0) {
    setStatus('Informe um valor maior que zero.', 'warn')
    return
  }

  const normalizedLabel = label.trim().toLowerCase()
  const existingIndex = draft.costs.findIndex((item) => item.label.trim().toLowerCase() === normalizedLabel)

  if (existingIndex >= 0) {
    const existingCost = draft.costs[existingIndex]
    if (!existingCost) return
    draft.costs[existingIndex] = { ...existingCost, amount }
    setStatus('Custo atualizado.', 'ok')
  } else {
    draft.costs.push({ id: createId(), label, amount })
    setStatus('Custo adicionado.', 'ok')
  }

  addingCost.value = false
  newCostType.value = 'documentacao'
  newCostAmount.value = 0
  newCostOtherLabel.value = ''
}

const onNewCostAmountInput = (event: Event) => {
  const input = event.target as HTMLInputElement
  newCostAmount.value = parseMoneyInput(input.value)
  input.value = formatMoneyInput(newCostAmount.value)
}

const onCostAmountInput = (cost: CostItem, event: Event) => {
  const input = event.target as HTMLInputElement
  if (isAutoMountCost(cost)) {
    cost.amount = resolveMountCostAmount(draft.mountClass, draft.fipeValue)
    input.value = formatMoneyInput(cost.amount)
    return
  }
  cost.amount = parseMoneyInput(input.value)
  input.value = formatMoneyInput(cost.amount)
}

const removeCostItem = (id: string) => {
  if (id === AUTO_MOUNT_COST_ID) {
    setStatus('Custo de tipo de monta é automático.', 'warn')
    return
  }

  const nextItems = draft.costs.filter((item) => item.id !== id)
  draft.costs.splice(0, draft.costs.length, ...nextItems)
  ensureLeilaoCostByMount(draft.mountClass)
  ensureMountDynamicCost(draft.mountClass, draft.fipeValue)
  setStatus('Custo removido.', 'warn')
}

const syncDraftState = () => {
  draft.costs = draft.costs.map((item) => ({
    ...item,
    label: item.label.trim(),
    amount: clampCostAmount(item.amount),
  }))
}

const resolveTargetMarginPercent = () => {
  if (estimatedSaleValue.value <= 0) return 0
  return (Number(targetMarginValue.value || 0) / estimatedSaleValue.value) * 100
}

const buildRecord = (): AuctionCarRecord => {
  const now = new Date().toISOString()
  const createdAt = draft.createdAt || now
  const interested = resolveInterestedFromDraft()

  const costs = draft.costs.map((item) => ({
    id: item.id,
    label: item.label.trim() || 'Custo sem nome',
    amount: clampCostAmount(item.amount),
  }))

  const purchaseValue = effectivePurchaseValue.value
  const targetMarginPercent = resolveTargetMarginPercent()

  return {
    id: draft.id,
    plate: normalizePlate(draft.plate),
    photoDataUrl: draft.photoDataUrl || '',
    plateCropDataUrl: draft.plateCropDataUrl || '',
    galleryPhotos: draft.galleryPhotos.filter(Boolean),
    brand: draft.brand.trim(),
    model: draft.model.trim(),
    year: draft.year,
    km: typeof draft.km === 'number' ? Math.max(0, Math.round(draft.km)) : null,
    fipeValue: Math.max(0, Number(draft.fipeValue) || 0),
    purchaseValue,
    purchaseOverrideEnabled: Boolean(draft.purchaseOverrideEnabled),
    costs,
    targetMarginPercent,
    mountClass: draft.mountClass,
    interested: interested.name,
    interestedPreset: interested.preset,
    notes: draft.notes.trim(),
    status: draft.status,
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

const cloneRecordForStorage = (record: AuctionCarRecord): AuctionCarRecord => {
  const normalizedCosts = Array.isArray(record.costs)
    ? record.costs.map((item) => ({
      id: item.id || createId(),
      label: String(item.label || '').trim() || 'Custo sem nome',
      amount: clampCostAmount(item.amount),
    }))
    : []

  const fallbackSummary = calculateAuctionSummary({
    fipeValue: Number(record.fipeValue) || 0,
    purchaseValue: Number(record.purchaseValue) || 0,
    costs: normalizedCosts,
    targetMarginPercent: Number(record.targetMarginPercent) || 0,
    mountClass: record.mountClass || 'pequena',
  })

  return {
    id: record.id,
    plate: normalizePlate(record.plate || ''),
    photoDataUrl: record.photoDataUrl || '',
    plateCropDataUrl: record.plateCropDataUrl || '',
    galleryPhotos: Array.isArray(record.galleryPhotos) ? [...record.galleryPhotos] : [],
    brand: String(record.brand || '').trim(),
    model: String(record.model || '').trim(),
    year: record.year ?? null,
    km: typeof record.km === 'number' ? Math.max(0, Math.round(record.km)) : null,
    fipeValue: Math.max(0, Number(record.fipeValue) || 0),
    purchaseValue: Math.max(0, Number(record.purchaseValue) || 0),
    purchaseOverrideEnabled: Boolean(record.purchaseOverrideEnabled),
    costs: normalizedCosts,
    targetMarginPercent: Math.max(0, Number(record.targetMarginPercent) || 0),
    mountClass: record.mountClass || 'pequena',
    interested: String(record.interested || '').trim(),
    interestedPreset: normalizeInterestedPreset(record.interestedPreset, record.interested),
    notes: String(record.notes || '').trim(),
    status: normalizeCarStatus(record.status),
    createdAt: record.createdAt || new Date().toISOString(),
    updatedAt: record.updatedAt || new Date().toISOString(),
    summary: record.summary || fallbackSummary,
  }
}

const reloadLocal = async () => {
  const records = await indexedDb.listCars()
  localCars.value = records.map((record) => cloneRecordForStorage(record))
  savedCarsCount.value = localCars.value.length
}

const clearDraft = () => {
  const nextDraft = createEmptyDraft()
  draft.id = nextDraft.id
  draft.plate = nextDraft.plate
  draft.photoDataUrl = nextDraft.photoDataUrl
  draft.plateCropDataUrl = nextDraft.plateCropDataUrl
  draft.galleryPhotos = [...nextDraft.galleryPhotos]
  draft.brand = nextDraft.brand
  draft.model = nextDraft.model
  draft.year = nextDraft.year
  draft.km = nextDraft.km
  draft.fipeValue = nextDraft.fipeValue
  draft.purchaseValue = nextDraft.purchaseValue
  draft.purchaseOverrideEnabled = nextDraft.purchaseOverrideEnabled
  draft.costs = nextDraft.costs.map((item) => ({ ...item }))
  draft.targetMarginPercent = nextDraft.targetMarginPercent
  draft.mountClass = nextDraft.mountClass
  draft.interestedPreset = nextDraft.interestedPreset
  draft.interestedOther = nextDraft.interestedOther
  draft.notes = nextDraft.notes
  draft.status = nextDraft.status
  draft.createdAt = nextDraft.createdAt

  plateCandidates.value = []
  plateCandidateDetails.value = []
  ocrNotFound.value = false
  marginWasEdited.value = false
  targetMarginValue.value = 10000
  plateCheckAttempted.value = false
  isEditingCurrentCar.value = false
}

const saveCurrentCar = async () => {
  if (!indexedDb.isSupported) {
    setStatus('IndexedDB não disponível neste navegador.', 'error')
    return
  }

  if (!canSave.value) {
    setStatus('Preencha ao menos placa ou dados básicos antes de salvar.', 'warn')
    return
  }

  const record = buildRecord()
  await indexedDb.saveCar(record)
  draft.createdAt = record.createdAt
  draft.purchaseValue = record.purchaseValue

  await reloadLocal()
  setStatus('Carro atual salvo com sucesso.', 'ok')
}

const resolveTargetMarginFromRecord = (record: AuctionCarRecord) => {
  const saleValue = calculateSaleValue(record.fipeValue, record.mountClass)
  if (saleValue > 0 && Number(record.targetMarginPercent) > 0) {
    return (Number(record.targetMarginPercent) / 100) * saleValue
  }
  return suggestMarginByFipe(record.fipeValue)
}

const editCurrentCar = (record: AuctionCarRecord) => {
  const normalizedMountClass: MountClass = record.mountClass || 'pequena'

  draft.id = record.id
  draft.plate = record.plate || ''
  draft.photoDataUrl = record.photoDataUrl || ''
  draft.plateCropDataUrl = record.plateCropDataUrl || ''
  draft.galleryPhotos = Array.isArray(record.galleryPhotos) ? [...record.galleryPhotos] : []
  draft.brand = record.brand || ''
  draft.model = record.model || ''
  draft.year = record.year ?? null
  draft.km = typeof record.km === 'number' ? record.km : null
  draft.fipeValue = Number(record.fipeValue) || 0
  draft.mountClass = normalizedMountClass
  const normalizedInterestedPreset = normalizeInterestedPreset(record.interestedPreset, record.interested)
  draft.interestedPreset = normalizedInterestedPreset || ''
  draft.interestedOther = normalizedInterestedPreset === 'outro' ? String(record.interested || '').trim() : ''
  draft.notes = record.notes || ''
  draft.status = normalizeCarStatus(record.status)
  draft.createdAt = record.createdAt || null

  const costs = Array.isArray(record.costs) ? record.costs : []
  draft.costs = costs.map((item) => ({
    id: item.id || createId(),
    label: item.label || 'Custo sem nome',
    amount: clampCostAmount(item.amount),
  }))
  ensureLeilaoCostByMount(draft.mountClass)
  ensureMountDynamicCost(draft.mountClass, draft.fipeValue)

  targetMarginValue.value = resolveTargetMarginFromRecord(record)
  marginWasEdited.value = true

  const inferredAuto = Math.max(0, draft.fipeValue - targetMarginValue.value - calculateTotalCosts(draft.costs))
  const inferredOverride = Math.abs((record.purchaseValue || 0) - inferredAuto) > 1
  draft.purchaseOverrideEnabled =
    typeof record.purchaseOverrideEnabled === 'boolean' ? record.purchaseOverrideEnabled : inferredOverride
  draft.purchaseValue = Number(record.purchaseValue) || inferredAuto

  plateCandidates.value = []
  plateCandidateDetails.value = []
  ocrNotFound.value = false
  plateCheckAttempted.value = true
  isEditingCurrentCar.value = true

  setStatus('Carro atual carregado para edição.', 'ok')
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

const closeCurrentEditor = () => {
  clearDraft()
  setStatus('Edição fechada. Voltou para novo carro.', 'ok')
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

const updateCarStatus = async (record: AuctionCarRecord, status: AuctionCarStatus) => {
  if (!record?.id) {
    setStatus('Registro inválido para atualizar status.', 'error')
    return
  }

  if (isUpdatingStatus(record.id)) return
  setUpdatingStatus(record.id, true)

  try {
    const persistedRecord = await indexedDb.getCar(record.id)
    const base = cloneRecordForStorage(persistedRecord || record)
    const updated: AuctionCarRecord = {
      ...base,
      status: normalizeCarStatus(status),
      updatedAt: new Date().toISOString(),
    }

    await indexedDb.saveCar(updated)

    localCars.value = localCars.value.map((item) => (item.id === record.id ? updated : item))
    if (draft.id === record.id) {
      draft.status = normalizeCarStatus(updated.status)
    }

    if (updated.status === 'adquirido') setStatus('Status alterado para adquirido.', 'ok')
    else if (updated.status === 'anunciado') setStatus('Status alterado para anunciado.', 'ok')
    else if (updated.status === 'vendido') setStatus('Status alterado para vendido.', 'ok')
    else setStatus('Status alterado para em andamento.', 'ok')
  } catch (error) {
    setStatus(`Falha ao atualizar status: ${readErrorMessage(error)}`, 'error')
  } finally {
    setUpdatingStatus(record.id, false)
  }
}

const markAsAcquired = async (record: AuctionCarRecord) => {
  const status = getCarStatus(record)
  if (status === 'adquirido') {
    setStatus('Este carro já está adquirido.', 'warn')
    return
  }
  if (status !== 'em_andamento') {
    setStatus('Ação disponível apenas quando o carro está em andamento.', 'warn')
    return
  }
  await updateCarStatus(record, 'adquirido')
}

const markAsAnnounced = async (record: AuctionCarRecord) => {
  const status = getCarStatus(record)
  if (status === 'anunciado') {
    setStatus('Este carro já está anunciado.', 'warn')
    return
  }
  if (status !== 'adquirido') {
    setStatus('Para anunciar, o carro precisa estar adquirido.', 'warn')
    return
  }
  await updateCarStatus(record, 'anunciado')
}

const markAsSold = async (record: AuctionCarRecord) => {
  const status = getCarStatus(record)
  if (status === 'vendido') {
    setStatus('Este carro já está vendido.', 'warn')
    return
  }
  if (status !== 'anunciado') {
    setStatus('Para vender, o carro precisa estar anunciado.', 'warn')
    return
  }
  await updateCarStatus(record, 'vendido')
}

const markAsReactivated = async (record: AuctionCarRecord) => {
  const status = getCarStatus(record)
  if (status === 'em_andamento') {
    setStatus('Este carro já está em andamento.', 'warn')
    return
  }
  if (status !== 'vendido') {
    setStatus('Reativar só está disponível para carro vendido.', 'warn')
    return
  }
  await updateCarStatus(record, 'em_andamento')
}

const removeLocal = async (id: string) => {
  await indexedDb.deleteCar(id)
  await reloadLocal()

  if (draft.id === id) {
    clearDraft()
  }

  setStatus('Registro removido.', 'warn')
}

const scrollToCurrentCars = () => {
  const element = document.getElementById('current-cars')
  if (!element) return
  element.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

onMounted(async () => {
  isClientMounted.value = true
  await refreshPlateFipeQuota()

  if (!indexedDb.isSupported) {
    setStatus('Este navegador não suporta IndexedDB.', 'warn')
    return
  }

  await reloadLocal()
  onCostTypeChange()
})
</script>
