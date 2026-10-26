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

      <section aria-label="Application statistics" class="grid grid-cols-1 gap-5 md:grid-cols-2">
        <article class="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
          <div class="flex items-start justify-between">
            <div>
              <p class="text-sm font-medium text-gray-500">Total storage used</p>
              <p class="mt-3 text-3xl font-bold text-gray-900">—</p>
              <p class="mt-1 text-sm text-gray-500">Number of connected storage environments (e.g., buckets)</p>
            </div>
            <span class="flex h-12 w-12 items-center justify-center rounded-xl bg-blue-50 text-primary-600">
              <i class="pi pi-database text-xl" aria-hidden="true"></i>
            </span>
          </div>
        </article>

        <article class="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
          <div class="flex items-start justify-between">
            <div>
              <p class="text-sm font-medium text-gray-500">Total collections</p>
              <p class="mt-3 text-3xl font-bold text-gray-900">—</p>
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
              class="flex h-36 w-36 shrink-0 items-center justify-center rounded-full border-[18px] border-gray-100 bg-white"
              role="img"
              aria-label="Placeholder for public and private collection chart"
            >
              <i class="pi pi-chart-pie text-4xl text-gray-300" aria-hidden="true"></i>
            </div>
            <dl class="grid w-full grid-cols-2 gap-4 sm:max-w-xs sm:grid-cols-1">
              <div class="rounded-lg bg-gray-50 px-4 py-3">
                <dt class="flex items-center gap-2 text-sm text-gray-600">
                  <span class="h-2.5 w-2.5 rounded-full bg-primary-500"></span>Public
                </dt>
                <dd class="mt-1 text-xl font-semibold text-gray-900">—%</dd>
              </div>
              <div class="rounded-lg bg-gray-50 px-4 py-3">
                <dt class="flex items-center gap-2 text-sm text-gray-600">
                  <span class="h-2.5 w-2.5 rounded-full bg-gray-400"></span>Private
                </dt>
                <dd class="mt-1 text-xl font-semibold text-gray-900">—%</dd>
              </div>
            </dl>
          </div>
        </article>

        <article class="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
          <div>
            <h2 class="text-lg font-semibold text-gray-900">File processing levels</h2>
            <p class="mt-1 text-sm text-gray-500">Share of files at each processing stage</p>
          </div>
          <div class="mt-6 space-y-5">
            <div v-for="level in ['Raw', 'Processed', 'Curated']" :key="level">
              <div class="mb-2 flex items-center justify-between">
                <span class="text-sm font-medium text-gray-700">{{ level }}</span>
                <span class="text-sm text-gray-500">—%</span>
              </div>
              <div class="h-2.5 overflow-hidden rounded-full bg-gray-100">
                <div class="h-full w-1/3 rounded-full bg-primary-200"></div>
              </div>
            </div>
          </div>
        </article>
      </section>
    </div>
  </div>
</template>
