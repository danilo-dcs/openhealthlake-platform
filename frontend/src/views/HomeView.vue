<script setup lang="ts">
import Card from 'primevue/card'
import Button from 'primevue/button'
import { RouterLink } from 'vue-router'
import { computed, onMounted, ref } from 'vue'

import { useUserStore } from '@/stores/userStore'

const userStore = useUserStore()

const userRole = computed(() => userStore.role)

const roleOpions = {
  admin: 'admin',
  user: 'user',
}

const displayFunctionality = (role: string): boolean => {
  return role === roleOpions.admin ? true : false
}

const menuItems = ref([
  {
    title: 'Catalog',
    icon: 'pi pi-book',
    colors: 'bg-primary-500',
    link: '/catalog',
    desc: 'Find dataset collections',
    visibility: true,
  },
  // {
  //   title: 'Passports',
  //   icon: 'pi pi-id-card',
  //   colors: 'bg-primary-400',
  //   link: '/passports',
  //   desc: 'Check your passport details',
  //   visibility: displayFunctionality(userRole),
  // },
  {
    title: 'Settings',
    icon: 'pi pi-cog',
    colors: 'bg-primary-500',
    link: '/settings',
    desc: 'Manage data sources',
    visibility: displayFunctionality(userRole.value!),
  },
  {
    title: 'Logout',
    icon: 'pi pi-sign-out',
    colors: 'bg-gray-700',
    link: '/login',
    desc: 'Click here to logout',
    visibility: true,
  },
])
</script>

<template>
  <div class="flex flex-col items-center min-h-screen bg-stone-100">
    <header class="text-center mt-10 mb-15">
      <h1 class="text-4xl font-bold text-gray-800">OpenHealthLake (OHL)</h1>
      <p class="text-gray-600 mt-2 text-lg">
        A data lakehouse to manage, explore, and control your data seamlessly.
      </p>
    </header>

    <section class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 w-[90%] max-w-6xl mb-5">
      <div v-for="item in menuItems" :key="item.title" class="flex">
        <div
          v-if="item.visibility"
          class="card flex flex-col justify-center flex-1 transition-transform duration-200 transform hover:scale-105 shadow-lg border-none bg-white rounded-xl"
        >
          <div
            class="flex flex-col sm:flex-row items-center justify-center text-center sm:text-left p-6 gap-4 h-full"
          >
            <RouterLink :to="item.link">
              <Button
                :class="item.colors"
                class="border-none w-20 h-20 flex items-center justify-center rounded-full shadow-md active:scale-95 shrink-0"
              >
                <i :class="item.icon" class="text-white text-3xl leading-none"></i>
              </Button>
            </RouterLink>

            <div class="flex flex-col justify-center">
              <h3 class="text-lg font-semibold text-gray-800">{{ item.title }}</h3>
              <p class="text-gray-600 mt-2">{{ item.desc }}</p>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section class="w-full flex justify-center bg-transparent p-4">
      <img
        src="/landing_image.png"
        alt="Data Lake Visualization"
        class="w-[50%] max-w-5xl object-cover"
      />
    </section>
  </div>
</template>
