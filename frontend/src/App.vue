<script setup lang="ts">
import Avatar from 'primevue/avatar'
import { computed } from 'vue'
import { RouterLink, RouterView, useRouter } from 'vue-router'

import inform_logo from '@/assets/img/inform_logo.png'
import dsi_logo from '@/assets/img/dsi_logo.png'
import ceri_logo from '@/assets/img/CERI_logo.png'
import comp2bio_logo from '@/assets/img/comp2bio_logo.png'
import ita_logo from '@/assets/img/ita_logo.png'
import { useUserStore } from '@/stores/userStore'
import { apiRequestHandler } from '@/shared/api/apiRequestHandler'
import logo from './assets/img/lakehouse-logo.png'

const router = useRouter()
const userStore = useUserStore()
const user = computed(() => userStore.email)
const userInitial = computed(() => user.value?.toUpperCase().at(0) ?? '')
const isAuthenticatedPage = computed(() => router.currentRoute.value.name !== 'login')
const canManageSettings = computed(() => userStore.role === 'admin')

const logout = async () => {
  await apiRequestHandler('/auth/logout', 'POST')
  userStore.clearUser()
  await router.replace({ name: 'login' })
}
</script>

<template>
  <div class="app-container flex min-h-screen w-full overflow-x-hidden bg-stone-100">
    <aside
      v-if="isAuthenticatedPage"
      class="flex w-16 shrink-0 flex-col bg-slate-900 px-2 py-6 text-white shadow-xl sm:w-64 sm:px-4"
    >
      <RouterLink to="/dashboard" class="mb-8 flex items-center justify-center gap-3 rounded-xl px-1 py-2 sm:justify-start sm:px-3">
        <img :src="logo" alt="OpenHealthLake" class="h-9 w-9 shrink-0 object-contain" />
        <span class="hidden text-lg font-semibold tracking-wide sm:inline">OpenHealthLake</span>
      </RouterLink>

      <nav aria-label="Main navigation" class="flex flex-1 flex-col gap-2">
        <RouterLink
          to="/dashboard"
          aria-label="Dashboard"
          class="flex items-center justify-center gap-3 rounded-lg px-2 py-3 font-medium text-slate-200 transition hover:bg-slate-800 hover:text-white sm:justify-start sm:px-4"
          active-class="!bg-primary-600 !text-white shadow-md"
        >
          <i class="pi pi-home" aria-hidden="true"></i>
          <span class="hidden sm:inline">Dashboard</span>
        </RouterLink>

        <RouterLink
          to="/catalog"
          aria-label="Catalog"
          class="flex items-center justify-center gap-3 rounded-lg px-2 py-3 font-medium text-slate-200 transition hover:bg-slate-800 hover:text-white sm:justify-start sm:px-4"
          active-class="!bg-primary-600 !text-white shadow-md"
        >
          <i class="pi pi-book" aria-hidden="true"></i>
          <span class="hidden sm:inline">Catalog</span>
        </RouterLink>

        <RouterLink
          v-if="canManageSettings"
          to="/settings"
          aria-label="Settings"
          class="flex items-center justify-center gap-3 rounded-lg px-2 py-3 font-medium text-slate-200 transition hover:bg-slate-800 hover:text-white sm:justify-start sm:px-4"
          active-class="!bg-primary-600 !text-white shadow-md"
        >
          <i class="pi pi-cog" aria-hidden="true"></i>
          <span class="hidden sm:inline">Settings</span>
        </RouterLink>
      </nav>

      <div class="border-t border-slate-700 pt-4">
        <div class="mb-4 flex items-center justify-center gap-3 px-0 sm:justify-start sm:px-2">
          <Avatar
            :label="userInitial"
            class="bg-primary text-white font-semibold"
            size="medium"
            shape="circle"
          />
          <div class="hidden min-w-0 sm:block">
            <div class="truncate text-sm font-medium text-white">{{ user }}</div>
            <div class="text-xs text-slate-400">Logged in</div>
          </div>
        </div>
        <button
          type="button"
          aria-label="Logout"
          class="flex w-full items-center justify-center gap-3 rounded-lg px-2 py-3 text-left font-medium text-slate-200 transition hover:bg-slate-800 hover:text-white sm:justify-start sm:px-4"
          @click="logout"
        >
          <i class="pi pi-sign-out" aria-hidden="true"></i>
          <span class="hidden sm:inline">Logout</span>
        </button>
      </div>
    </aside>

    <div class="flex min-h-screen min-w-0 flex-1 flex-col">
      <main class="flex-1 min-w-0 overflow-auto">
        <RouterView />
      </main>

      <footer
        v-if="isAuthenticatedPage"
        class="w-full border-t border-gray-200 bg-white px-5 py-5 text-center text-xs text-gray-600"
      >
        <div class="mb-3 font-semibold text-gray-700">Powered by</div>
        <div class="flex flex-wrap justify-center items-center gap-x-8 gap-y-3">
          <img :src="inform_logo" alt="INFORM" class="h-8 object-contain" />
          <img :src="dsi_logo" alt="DSI" class="h-8 object-contain" />
          <img :src="ceri_logo" alt="CERI" class="h-8 object-contain" />
          <img :src="ita_logo" alt="ITA" class="h-7 object-contain" />
          <img :src="comp2bio_logo" alt="Comp2Bio" class="h-6 object-contain" />
        </div>
        <a
          href="https://github.com/danilo-dcs/lakehouse-platform"
          target="_blank"
          rel="noopener noreferrer"
          class="mt-3 inline-flex items-center gap-2 text-gray-500 transition-colors hover:text-[#2a95ea]"
        >
          <i class="pi pi-github"></i>
          <span>View Source Code and Platform Details</span>
        </a>
      </footer>
    </div>
  </div>
</template>
