<script setup lang="ts">
import Avatar from 'primevue/avatar'
import Button from 'primevue/button'
import Menu from 'primevue/menu'

import { computed, ref, watch } from 'vue'
import { RouterView, RouterLink, useRouter } from 'vue-router'
import inform_logo from '@/assets/img/inform_logo.png'
import dsi_logo from '@/assets/img/dsi_logo.png'
import ceri_logo from '@/assets/img/CERI_logo.png'
import comp2bio_logo from '@/assets/img/comp2bio_logo.png'
import ita_logo from '@/assets/img/ita_logo.png'

import { useUserStore } from '@/stores/userStore'
import { apiRequestHandler } from './shared/api/apiRequestHandler'

import logo from './assets/img/lakehouse-logo.png'

const router = useRouter()

const userStore = useUserStore()

const user = computed(() => userStore.email)

const userInitial = computed(() => user.value?.toUpperCase().at(0) ?? '')

const logout = async () => {
  await apiRequestHandler(`/auth/logout`, 'POST')
  userStore.clearUser()
  router.push('/login')
}

const isHeaderVisible = computed(() => router.currentRoute.value.name !== 'login')

const menu = ref()
const items = ref([
  {
    label: 'Settings',
    items: [
      {
        label: 'Logout',
        icon: 'pi pi-sign-out',
        action: () => logout(),
      },
    ],
  },
])

const toggle = (event: any) => {
  menu.value.toggle(event)
}
</script>

<template>
  <div class="app-container flex flex-col min-h-screen w-screen overflow-x-hidden">
    <!-- Header -->
    <header
      v-if="isHeaderVisible"
      class="bg-white shadow-md px-8 py-3 flex justify-between items-center border-b border-gray-200 w-full"
    >
      <div>
        <RouterLink
          to="/"
          class="flex items-center space-x-2 text-xl font-semibold text-gray-800 hover:text-blue-600 transition-colors duration-200"
        >
          <img :src="logo" alt="Lakehouse Home" class="w-7 h-7 object-contain" />
          <span>Home</span>
        </RouterLink>
      </div>

      <div class="flex items-center space-x-5">
        <div class="text-right hidden sm:block">
          <div class="font-medium text-gray-800">{{ user }}</div>
          <div class="text-sm text-gray-500">Logged in</div>
        </div>

        <Avatar
          :label="userInitial"
          class="bg-primary text-white font-semibold"
          size="medium"
          shape="circle"
        />

        <div class="card flex justify-center">
          <Button
            type="button"
            icon="pi pi-cog"
            size="small"
            rounded
            variant="outlined"
            @click="toggle"
            aria-haspopup="true"
            aria-controls="overlay_menu"
            class="w-full border-none bg-gray-800 hover:bg-gray-700 text-white font-semibold py-2 shadow-md active:scale-95 transition duration-150"
            v-tooltip.bottom="'Settings'"
          />
          <Menu ref="menu" id="overlay_menu" :model="items" :popup="true">
            <template #item="{ item }">
              <a
                @click="item.action"
                class="flex items-center px-3 py-2 rounded-lg transition-all duration-300 ease-in-out hover:bg-blue-100 hover:text-blue-700 active:scale-95 active:bg-blue-200 cursor-pointer select-none"
              >
                <span :class="[item.icon, 'text-primary group-hover:text-inherit']" />
                <span :class="['ml-2', { 'font-semibold': item.items }]">{{ item.label }}</span>
              </a>
            </template>
          </Menu>
        </div>

        <!-- <Button
          class="bg-black hover:bg-red-600 border-none text-white p-2 rounded-full transition-all duration-150"
          icon="pi pi-sign-out"
          @click="logout"
          v-tooltip.bottom="'Logout'"
        /> -->
      </div>
    </header>

    <!-- Main -->
    <main class="flex-1 w-full h-full bg-stone-100 overflow-hidden">
      <RouterView />
    </main>

    <!-- Footer -->
    <footer
      v-if="isHeaderVisible"
      class="bg-gray-200 w-full p-8 text-center text-sm text-gray-700 flex flex-col items-center gap-y-7"
    >
      <div class="font-semibold text-gray-700">Powered by:</div>
      <div class="flex flex-row items-center gap-x-10">
        <img :src="inform_logo" alt="Logo" class="h-16" />
        <img :src="dsi_logo" alt="Logo" class="h-16" />
        <img :src="ceri_logo" alt="Logo" class="h-16" />
        <img :src="ita_logo" alt="Logo" class="h-14" />
        <img :src="comp2bio_logo" alt="Logo" class="h-8" />
      </div>
      <div class="flex flex-col items-center space-y-2">
        <a
          href="https://github.com/danilo-dcs/lakehouse-platform"
          target="_blank"
          rel="noopener noreferrer"
          class="flex items-center space-x-2 text-gray-500 hover:text-[#2a95ea] transition-colors"
        >
          <i class="pi pi-github text-base"></i>
          <span>View Source Code and Platform Details</span>
        </a>
      </div>
    </footer>
  </div>
</template>
