<template>
  <div class="space-y-4 pb-8">
    <section
      v-if="statusMessage"
      class="rounded-xl border px-3 py-2 text-sm"
      :class="{
        'border-emerald-700/35 bg-emerald-50 text-emerald-900': statusTone === 'ok',
        'border-amber-700/35 bg-amber-50 text-amber-900': statusTone === 'warn',
        'border-rose-700/35 bg-rose-50 text-rose-900': statusTone === 'error',
      }"
    >
      {{ statusMessage }}
    </section>

    <div class="grid gap-4 lg:grid-cols-[1.35fr_0.85fr]">
      <section class="surface-card rounded-2xl p-4 sm:p-5">
        <div class="mb-4 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h2 class="text-xl font-bold text-slate-900">Cadastro rápido</h2>
            <p class="text-sm text-slate-600">Foto frontal + placa + custos para calcular margem na hora.</p>
          </div>
          <button
            class="rounded-lg border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-800 hover:bg-slate-100"
            type="button"
            @click="clearDraft"
          >
            Novo rascunho
          </button>
        </div>

        <div class="grid gap-3 sm:grid-cols-2">
          <div>
            <label class="field-label">Placa</label>
            <input
              class="field-input"
              inputmode="text"
              placeholder="ABC1D23"
              :value="draft.plate"
              @input="onPlateInput"
            >
          </div>

          <div>
            <label class="field-label">Ano</label>
            <input
              class="field-input"
              type="number"
              min="1980"
              max="2050"
              :value="draft.year ?? ''"
              @input="onYearInput"
            >
          </div>

          <div class="sm:col-span-2">
            <label class="field-label">Foto frontal (camera do celular)</label>
            <input
              class="field-input"
              type="file"
              accept="image/*"
              capture="environment"
              @change="onPhotoSelected"
            >
            <img
              v-if="draft.photoDataUrl"
              :src="draft.photoDataUrl"
              alt="Foto do carro"
              class="mt-3 h-36 w-full rounded-xl object-cover sm:h-44"
            >
          </div>

          <div>
            <label class="field-label">Marca</label>
            <input v-model="draft.brand" class="field-input" placeholder="Chevrolet">
          </div>

          <div>
            <label class="field-label">Modelo</label>
            <input v-model="draft.model" class="field-input" placeholder="Onix LT">
          </div>

          <div>
            <label class="field-label">Valor FIPE (R$)</label>
            <input v-model.number="draft.fipeValue" class="field-input" type="number" min="0" step="100">
          </div>

          <div>
            <label class="field-label">Compra no leilao (R$)</label>
            <input
              v-model.number="draft.purchaseValue"
              class="field-input"
              type="number"
              min="0"
              step="100"
            >
          </div>

          <div class="sm:col-span-2">
            <label class="field-label">Observacoes</label>
            <textarea
              v-model="draft.notes"
              class="field-input min-h-20"
              placeholder="Detalhes de avarias, riscos e observacoes de patio"
            />
          </div>
        </div>

        <div class="mt-5 space-y-3 rounded-xl border border-slate-200 bg-white/70 p-3">
          <div class="flex items-center justify-between">
            <h3 class="text-base font-semibold text-slate-900">Custos de recuperacao</h3>
            <button
              class="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-100"
              type="button"
              @click="addCostItem"
            >
              + custo
            </button>
          </div>

          <div
            v-for="cost in draft.costs"
            :key="cost.id"
            class="grid gap-2 rounded-lg border border-slate-200 bg-white p-2 sm:grid-cols-[1fr_140px_auto]"
          >
            <input v-model="cost.label" class="field-input" placeholder="Pintura">
            <input v-model.number="cost.amount" class="field-input" type="number" min="0" step="50">
            <button
              class="rounded-lg border border-rose-300 px-2 py-1 text-xs font-semibold text-rose-700 hover:bg-rose-50"
              type="button"
              @click="removeCostItem(cost.id)"
            >
              remover
            </button>
          </div>

          <div>
            <label class="field-label">Meta de margem (%)</label>
            <input
              v-model.number="draft.targetMarginPercent"
              class="field-input"
              type="number"
              min="0"
              max="100"
              step="0.5"
            >
          </div>
        </div>

        <div class="mt-5 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
          <button
            class="rounded-xl bg-slate-900 px-3 py-2 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-60"
            type="button"
            :disabled="loadingLookup"
            @click="lookupFipe"
          >
            {{ loadingLookup ? 'Buscando...' : 'Buscar placa/FIPE' }}
          </button>

          <button
            class="rounded-xl bg-teal-700 px-3 py-2 text-sm font-semibold text-white hover:bg-teal-600"
            type="button"
            @click="saveLocal"
          >
            Salvar local
          </button>

          <button
            class="rounded-xl bg-amber-600 px-3 py-2 text-sm font-semibold text-white hover:bg-amber-500"
            type="button"
            :disabled="syncingRemote"
            @click="syncRemote"
          >
            {{ syncingRemote ? 'Sincronizando...' : 'Sincronizar API' }}
          </button>

          <button
            class="rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100"
            type="button"
            @click="reloadLocal"
          >
            Recarregar lista
          </button>
        </div>
      </section>

      <section class="surface-card rounded-2xl p-4 sm:p-5">
        <h2 class="text-xl font-bold text-slate-900">Analise de margem</h2>
        <p class="text-sm text-slate-600">Atualiza em tempo real com base nos custos informados.</p>

        <div class="mt-4 space-y-3">
          <article class="rounded-xl border border-slate-200 bg-white/80 p-3">
            <p class="text-xs uppercase tracking-[0.16em] text-slate-500">Custos totais</p>
            <p class="metric-value text-slate-900">{{ formatMoney(summary.totalCosts) }}</p>
          </article>

          <article class="rounded-xl border border-slate-200 bg-white/80 p-3">
            <p class="text-xs uppercase tracking-[0.16em] text-slate-500">Investimento total</p>
            <p class="metric-value text-slate-900">{{ formatMoney(summary.totalInvestment) }}</p>
          </article>

          <article class="rounded-xl border border-slate-200 bg-white/80 p-3">
            <p class="text-xs uppercase tracking-[0.16em] text-slate-500">Lucro estimado</p>
            <p class="metric-value" :class="summary.expectedProfit >= 0 ? 'text-emerald-700' : 'text-rose-700'">
              {{ formatMoney(summary.expectedProfit) }}
            </p>
          </article>

          <article class="rounded-xl border border-slate-200 bg-white/80 p-3">
            <p class="text-xs uppercase tracking-[0.16em] text-slate-500">Margem</p>
            <p class="metric-value" :class="summary.targetReached ? 'text-emerald-700' : 'text-amber-700'">
              {{ formatPercent(summary.marginPercent) }}
            </p>
            <p class="mt-1 text-xs text-slate-600">
              Meta: {{ formatPercent(summary.targetMarginPercent) }}
            </p>
          </article>
        </div>
      </section>
    </div>

    <section class="surface-card rounded-2xl p-4 sm:p-5">
      <div class="mb-3 flex items-center justify-between">
        <h2 class="text-xl font-bold text-slate-900">Carros salvos no celular</h2>
        <span class="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
          {{ localCars.length }} registros
        </span>
      </div>

      <div v-if="!indexedDb.isSupported" class="rounded-xl border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900">
        IndexedDB nao esta disponivel neste navegador.
      </div>

      <div v-else-if="localCars.length === 0" class="rounded-xl border border-slate-200 bg-white/70 px-3 py-5 text-sm text-slate-600">
        Nenhum carro salvo ainda.
      </div>

      <div v-else class="grid gap-2">
        <article
          v-for="item in localCars"
          :key="item.id"
          class="rounded-xl border border-slate-200 bg-white px-3 py-3"
        >
          <div class="flex items-start justify-between gap-2">
            <div>
              <p class="text-sm font-bold text-slate-900">{{ item.plate || 'SEM PLACA' }} · {{ item.brand || 'Marca' }}</p>
              <p class="text-xs text-slate-600">{{ item.model || 'Modelo' }} · atualizado {{ formatDate(item.updatedAt) }}</p>
              <p class="mt-1 text-xs text-slate-600">
                Margem {{ formatPercent(item.summary.marginPercent) }} | FIPE {{ formatMoney(item.fipeValue) }}
              </p>
            </div>

            <div class="flex gap-2">
              <button
                class="rounded-lg border border-slate-300 px-2 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-100"
                type="button"
                @click="loadFromLocal(item)"
              >
                Abrir
              </button>
              <button
                class="rounded-lg border border-rose-300 px-2 py-1 text-xs font-semibold text-rose-700 hover:bg-rose-50"
                type="button"
                @click="removeLocal(item.id)"
              >
                Excluir
              </button>
            </div>
          </div>
        </article>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useAuctionCarsApi } from '~/composables/useAuctionCarsApi'
import { useIndexedAuctionCars } from '~/composables/useIndexedAuctionCars'
import { calculateAuctionSummary, normalizePlate } from '@core/shared/valuation'
import type { AuctionCarRecord, CostItem } from '@core/shared/types/auction'

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
  notes: string
  createdAt: string | null
}

const costPresets = ['Taxa do leiloeiro', 'Pintura', 'Mecanica', 'Suspensao', 'Vidros']

const createId = () => {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return Math.random().toString(36).slice(2, 12)
}

const buildDefaultCosts = (): CostItem[] =>
  costPresets.map((label) => ({ id: createId(), label, amount: 0 }))

const createEmptyDraft = (): DraftState => ({
  id: createId(),
  plate: '',
  photoDataUrl: '',
  brand: '',
  model: '',
  year: null,
  fipeValue: 0,
  purchaseValue: 0,
  costs: buildDefaultCosts(),
  targetMarginPercent: 12,
  notes: '',
  createdAt: null,
})

const draft = reactive<DraftState>(createEmptyDraft())
const localCars = ref<AuctionCarRecord[]>([])
const loadingLookup = ref(false)
const syncingRemote = ref(false)
const statusMessage = ref('')
const statusTone = ref<'ok' | 'warn' | 'error'>('ok')

const indexedDb = useIndexedAuctionCars()
const api = useAuctionCarsApi()

const summary = computed(() =>
  calculateAuctionSummary({
    fipeValue: draft.fipeValue,
    purchaseValue: draft.purchaseValue,
    costs: draft.costs,
    targetMarginPercent: draft.targetMarginPercent,
  }),
)

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

const setStatus = (message: string, tone: 'ok' | 'warn' | 'error' = 'ok') => {
  statusMessage.value = message
  statusTone.value = tone
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
  setStatus('Novo rascunho iniciado.', 'ok')
}

const onPlateInput = (event: Event) => {
  const input = event.target as HTMLInputElement
  draft.plate = normalizePlate(input.value)
}

const onYearInput = (event: Event) => {
  const input = event.target as HTMLInputElement
  const rawValue = Number(input.value)
  draft.year = Number.isFinite(rawValue) && rawValue > 0 ? rawValue : null
}

const onPhotoSelected = async (event: Event) => {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]

  if (!file) {
    return
  }

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

  draft.photoDataUrl = fileData
  setStatus('Foto carregada para analise da placa.', 'ok')
}

const buildRecord = (): AuctionCarRecord => {
  const now = new Date().toISOString()
  const createdAt = draft.createdAt || now

  const costs = draft.costs.map((item) => ({
    id: item.id,
    label: item.label.trim() || 'Custo sem nome',
    amount: Math.max(0, Number(item.amount) || 0),
  }))

  return {
    id: draft.id,
    plate: normalizePlate(draft.plate),
    photoDataUrl: draft.photoDataUrl || '',
    brand: draft.brand.trim(),
    model: draft.model.trim(),
    year: draft.year,
    fipeValue: Math.max(0, Number(draft.fipeValue) || 0),
    purchaseValue: Math.max(0, Number(draft.purchaseValue) || 0),
    costs,
    targetMarginPercent: Math.max(0, Number(draft.targetMarginPercent) || 0),
    notes: draft.notes.trim(),
    createdAt,
    updatedAt: now,
    summary: calculateAuctionSummary({
      fipeValue: draft.fipeValue,
      purchaseValue: draft.purchaseValue,
      costs,
      targetMarginPercent: draft.targetMarginPercent,
    }),
  }
}

const reloadLocal = async () => {
  localCars.value = await indexedDb.listCars()
}

const saveLocal = async () => {
  if (!indexedDb.isSupported) {
    setStatus('IndexedDB nao disponivel neste navegador.', 'error')
    return
  }

  const record = buildRecord()
  await indexedDb.saveCar(record)
  draft.createdAt = record.createdAt
  await reloadLocal()

  setStatus('Carro salvo localmente no celular.', 'ok')
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
    notes: record.notes,
    createdAt: record.createdAt,
  })

  setStatus('Rascunho carregado do celular.', 'ok')
}

const removeLocal = async (id: string) => {
  await indexedDb.deleteCar(id)
  await reloadLocal()
  if (draft.id === id) {
    clearDraft()
  }
  setStatus('Registro local removido.', 'warn')
}

const addCostItem = () => {
  draft.costs.push({ id: createId(), label: '', amount: 0 })
}

const removeCostItem = (id: string) => {
  if (draft.costs.length <= 1) {
    setStatus('Mantenha pelo menos um campo de custo.', 'warn')
    return
  }

  draft.costs = draft.costs.filter((cost) => cost.id !== id)
}

const readErrorMessage = (error: unknown) => {
  if (error && typeof error === 'object') {
    const maybeData = (error as { data?: { statusMessage?: string } }).data
    if (maybeData?.statusMessage) return maybeData.statusMessage
  }

  if (error instanceof Error && error.message) {
    return error.message
  }

  return 'Falha na operacao.'
}

const lookupFipe = async () => {
  if (!draft.plate && !draft.photoDataUrl) {
    setStatus('Informe a placa ou envie foto frontal antes da busca.', 'warn')
    return
  }

  loadingLookup.value = true

  try {
    const { result } = await api.lookupPlateAndFipe({
      plate: draft.plate || undefined,
      imageBase64: draft.photoDataUrl || undefined,
    })

    draft.plate = normalizePlate(result.plate)
    if (result.brand) draft.brand = result.brand
    if (result.model) draft.model = result.model
    if (result.year !== null) draft.year = result.year
    if (result.fipeValue !== null) draft.fipeValue = result.fipeValue

    const sourceLabel = result.source === 'placa-fipe' ? 'Placa FIPE' : 'mock local'
    setStatus(`Consulta concluida via ${sourceLabel}.`, 'ok')
  } catch (error) {
    setStatus(readErrorMessage(error), 'error')
  } finally {
    loadingLookup.value = false
  }
}

const syncRemote = async () => {
  syncingRemote.value = true

  try {
    const payload = buildRecord()
    const { item } = await api.saveRemoteCar(payload)
    setStatus(`Sincronizado na API (${item.id}).`, 'ok')
  } catch (error) {
    setStatus(readErrorMessage(error), 'error')
  } finally {
    syncingRemote.value = false
  }
}

const formatMoney = (value: number) => moneyFormatter.format(Number(value) || 0)
const formatPercent = (value: number) => `${percentFormatter.format(Number(value) || 0)}%`
const formatDate = (value: string) => dateFormatter.format(new Date(value))

onMounted(async () => {
  if (!indexedDb.isSupported) {
    setStatus('Este navegador nao suporta IndexedDB.', 'warn')
    return
  }

  await reloadLocal()
})
</script>
