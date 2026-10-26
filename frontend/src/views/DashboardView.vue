<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { apiRequestHandler } from '@/shared/api/apiRequestHandler'
import type { CollectionVisibilityStatsResponse } from '@/shared/interfaces/http/CollectionsVisibilityStatsResponse'
import type { FileProcessingStatsResponse } from '@/shared/interfaces/http/FileProcessingStatsResponse'
import type { TotalStatsResponse } from '@/shared/interfaces/http/TotalStatsResponse'





const bucketTotal = ref<number | null>(null)
const collectionTotal = ref<number | null>(null)
const fileTotal = ref<number | null>(null)
const collectionVisibility = ref<CollectionVisibilityStatsResponse | null>(null)
const fileProcessingLevels = ref<FileProcessingStatsResponse | null>(null)
const loading = ref(true)
const loadError = ref('')

const collectionTotalForPercent = computed(
  () => (collectionVisibility.value?.public ?? 0) + (collectionVisibility.value?.private ?? 0),
)

const publicPercentage = computed(() =>
  collectionTotalForPercent.value
    ? Math.round(((collectionVisibility.value?.public ?? 0) / collectionTotalForPercent.value) * 100)
    : 0,
)

const fileProcessingRows = computed(() => {
  const total = fileTotal.value ?? 0
  const levels = fileProcessingLevels.value

  return [
    { label: 'Raw', count: levels?.raw ?? 0 },
    { label: 'Processed', count: levels?.processed ?? 0 },
    { label: 'Curated', count: levels?.curated ?? 0 },
  ].map((level) => ({
    ...level,
    percentage: total ? Math.round((level.count / total) * 100) : 0,
  }))
})

const formatNumber = (value: number | null): string =>
  value === null ? '—' : new Intl.NumberFormat().format(value)

onMounted(async () => {
  try {
    const [buckets, collections, visibility, files, categories] = await Promise.all([
      apiRequestHandler<TotalStatsResponse>('/stats/buckets'),
      apiRequestHandler<TotalStatsResponse>('/stats/collections/total'),
      apiRequestHandler<CollectionVisibilityStatsResponse>('/stats/collections/visibility'),
      apiRequestHandler<TotalStatsResponse>('/stats/files'),
      apiRequestHandler<FileProcessingStatsResponse>('/stats/files/category'),
    ])

    bucketTotal.value = buckets.total
    collectionTotal.value = collections.total
    collectionVisibility.value = visibility
    fileTotal.value = files.total
    fileProcessingLevels.value = categories
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : 'Unable to load dashboard statistics.'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="min-h-full bg-stone-100 px-5 py-8 sm:px-8 lg:px-10">
    <div class="mx-auto max-w-7xl">
      <header class="mb-8">
        <p class="text-sm font-semibold uppercase tracking-wider text-primary-600">
          OpenHealthLake
        </p>
        <h1 class="mt-1 text-3xl font-bold text-gray-900">Dashboard</h1>
        <p class="mt-2 text-gray-600">An overview of the data stored in the OpenHealthLake platform.</p>
      </header>

      <p v-if="loadError" role="alert" class="mb-5 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
        Could not load all dashboard statistics. {{ loadError }}
      </p>

      <section aria-label="Application statistics" class="grid grid-cols-1 gap-5 md:grid-cols-2">
        <article class="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
          <div class="flex items-start justify-between">
            <div>
              <p class="text-sm font-medium text-gray-500">Total buckets</p>
              <p class="mt-3 text-3xl font-bold text-gray-900" aria-live="polite">
                {{ loading ? '…' : formatNumber(bucketTotal) }}
              </p>
              <p class="mt-1 text-sm text-gray-500">Connected storage buckets</p>
            </div>
            <span class="flex h-12 w-12 items-center justify-center rounded-xl bg-blue-50 text-primary-600">
              <i class="pi pi-server text-xl" aria-hidden="true"></i>
            </span>
          </div>
        </article>

        <article class="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
          <div class="flex items-start justify-between">
            <div>
              <p class="text-sm font-medium text-gray-500">Total collections</p>
              <p class="mt-3 text-3xl font-bold text-gray-900" aria-live="polite">
                {{ loading ? '…' : formatNumber(collectionTotal) }}
              </p>
              <p class="mt-1 text-sm text-gray-500">Collections available in the catalog</p>
            </div>
            <span class="flex h-12 w-12 items-center justify-center rounded-xl bg-violet-50 text-violet-600">
              <i class="pi pi-folder text-xl" aria-hidden="true"></i>
            </span>
          </div>
        </article>

        <article class="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
          <div>
            <h2 class="text-lg font-semibold text-gray-900">Collection visibility</h2>
            <p class="mt-1 text-sm text-gray-500">Public and private collections</p>
          </div>
          <div class="mt-6 flex flex-col items-center gap-6 sm:flex-row sm:justify-center">
            <div
              class="flex h-36 w-36 shrink-0 items-center justify-center rounded-full"
              :style="{
                background: `conic-gradient(#3b82f6 0 ${publicPercentage}%, #9ca3af ${publicPercentage}% 100%)`,
              }"
              role="img"
              :aria-label="`Public collections: ${publicPercentage}%, private collections: ${100 - publicPercentage}%`"
            >
              <div class="flex h-24 w-24 items-center justify-center rounded-full bg-white text-sm font-semibold text-gray-700">
                {{ loading ? '…' : `${publicPercentage}%` }} public
              </div>
            </div>
            <dl class="grid w-full grid-cols-2 gap-4 sm:max-w-xs sm:grid-cols-1">
              <div class="rounded-lg bg-gray-50 px-4 py-3">
                <dt class="flex items-center gap-2 text-sm text-gray-600">
                  <span class="h-2.5 w-2.5 rounded-full bg-blue-500"></span>Public
                </dt>
                <dd class="mt-1 text-xl font-semibold text-gray-900">
                  {{ loading ? '…' : `${formatNumber(collectionVisibility?.public ?? null)} (${publicPercentage}%)` }}
                </dd>
              </div>
              <div class="rounded-lg bg-gray-50 px-4 py-3">
                <dt class="flex items-center gap-2 text-sm text-gray-600">
                  <span class="h-2.5 w-2.5 rounded-full bg-gray-400"></span>Private
                </dt>
                <dd class="mt-1 text-xl font-semibold text-gray-900">
                  {{ loading ? '…' : `${formatNumber(collectionVisibility?.private ?? null)} (${100 - publicPercentage}%)` }}
                </dd>
              </div>
            </dl>
          </div>
        </article>

        <article class="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
          <div class="flex items-start justify-between">
            <div>
              <h2 class="text-lg font-semibold text-gray-900">Files in catalog</h2>
              <p class="mt-1 text-sm text-gray-500">Total active file records</p>
            </div>
            <span class="flex h-12 w-12 items-center justify-center rounded-xl bg-emerald-50 text-emerald-600">
              <i class="pi pi-file text-xl" aria-hidden="true"></i>
            </span>
          </div>
          <p class="mt-5 text-3xl font-bold text-gray-900" aria-live="polite">
            {{ loading ? '…' : formatNumber(fileTotal) }}
          </p>
        </article>

        <article class="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm md:col-span-2">
          <div>
            <h2 class="text-lg font-semibold text-gray-900">File processing levels</h2>
            <p class="mt-1 text-sm text-gray-500">Share of catalog files at each processing stage</p>
          </div>
          <div class="mt-6 grid grid-cols-1 gap-5 sm:grid-cols-3">
            <div v-for="level in fileProcessingRows" :key="level.label">
              <div class="mb-2 flex items-center justify-between">
                <span class="text-sm font-medium text-gray-700">{{ level.label }}</span>
                <span class="text-sm text-gray-600">
                  {{ loading ? '…' : `${level.percentage}% (${formatNumber(level.count)})` }}
                </span>
              </div>
              <div
                class="h-2.5 overflow-hidden rounded-full bg-gray-100"
                role="progressbar"
                :aria-label="`${level.label} files`"
                :aria-valuenow="loading ? 0 : level.percentage"
                aria-valuemin="0"
                aria-valuemax="100"
              >
                <div
                  class="h-full rounded-full bg-primary-500 transition-all duration-500"
                  :style="{ width: loading ? '0%' : `${level.percentage}%` }"
                ></div>
              </div>
            </div>
          </div>
        </article>
      </section>
    </div>
  </div>
</template>
