<script setup lang="ts">
import InputText from 'primevue/inputtext'
import InputGroup from 'primevue/inputgroup'
import InputGroupAddon from 'primevue/inputgroupaddon'
import Button from 'primevue/button'
import Divider from 'primevue/divider'
import Chip from 'primevue/chip'
import Toast from 'primevue/toast'
import Password from 'primevue/password'
import DynamicDialog from 'primevue/dynamicdialog'

import uiConf from '../assets/configs/ui.json'

import logo from '../assets/img/lakehouse-logo.png'

import backgroundImage from '@/assets/img/landing-background.png'

import inform_logo from '@/assets/img/inform_logo.png'
import dsi_logo from '@/assets/img/dsi_logo.png'
import ceri_logo from '@/assets/img/CERI_logo.png'
import comp2bio_logo from '@/assets/img/comp2bio_logo.png'
import ita_logo from '@/assets/img/ita_logo.png'

import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import { useDialog } from 'primevue/usedialog'

import type { UiConfigs } from '@/shared/interfaces/configs/UiConfigs'
import type { LoginResponse } from '@/shared/interfaces/http/LoginResponse'

import SubscriptionForm from '@/components/login/SubscriptionForm.vue'
import PasswordRecoveryForm from '@/components/login/PasswordRecoveryForm.vue'

import { useUserStore } from '@/stores/userStore'
import { apiRequestHandler } from '@/shared/api/apiRequestHandler'

const userStore = useUserStore()

const dialog = useDialog()

const uiSettings: UiConfigs = uiConf

const pageTitle = ref(uiSettings.landing_page_title)
const pageText = ref(uiSettings.landing_page_text)

const toast = useToast()

const features = ref([
  { label: 'Passport-based Access Control', icon: 'pi pi-shield' },
  { label: 'Data Storage', icon: 'pi pi-database' },
  { label: 'Data Cataloguing', icon: 'pi pi-book' },
  { label: 'Data Sharing', icon: 'pi pi-share-alt' },
])
// Reactive references with types
const formValues = ref({
  email: '',
  password: '',
})

const router = useRouter()

const dialogDefaultProps = {
  header: 'Product List',
  style: {
    width: '50vw',
  },
  breakpoints: {
    '960px': '75vw',
    '640px': '90vw',
  },
  modal: true,
}

const openSubscribeModal = (): void => {
  const dialogSpecs = {
    props: {
      ...dialogDefaultProps,
      header: 'Sign up to get started with Data Lakehouse',
      style: {
        width: '50vw',
      },
    },
    templates: {},
    modal: true,
    maximizable: true,
    breakpoints: { '960px': '75vw', '640px': '90vw' },
    onClose: () => {},
  }

  const dialogRef = dialog.open(SubscriptionForm, dialogSpecs)
}

const openPasswordRecoveryModal = (): void => {
  const dialogSpecs = {
    props: {
      ...dialogDefaultProps,
      header: 'Password Recovery',
      style: {
        width: '50vw',
      },
    },
    templates: {},
    modal: true,
    maximizable: true,
    breakpoints: { '960px': '75vw', '640px': '90vw' },
    onClose: () => {},
  }

  const dialogRef = dialog.open(PasswordRecoveryForm, dialogSpecs)
}

const loginOnSubmit = async (): Promise<void> => {
  try {
    if (!formValues.value.email || !formValues.value.password) {
      throw new Error('Empty Fields')
    }

    const url = '/auth/login'

    const body = {
      email: formValues.value.email,
      password: formValues.value.password,
    }

    const responseData = await apiRequestHandler<LoginResponse>(url, 'POST', body)

    userStore.setUser({
      email: formValues.value.email,
      role: responseData.user_role,
      userId: responseData.user_id,
      accessToken: responseData.access_token,
      refreshToken: responseData.refresh_token,
      tokenType: responseData.token_type,
    })

    // Redirect to home page
    router.push('/')
  } catch (err: unknown) {
    let error = ''
    if (err instanceof Error) {
      error = err.message
    } else {
      error = 'Login failed'
    }
    toast.add({
      severity: 'error',
      summary: 'Login error',
      detail: error,
      life: 4000,
    })
  }
}
</script>

<template>
  <div class="min-h-screen flex items-center justify-center relative overflow-hidden px-6">
    <Toast />
    <DynamicDialog />

    <!-- White Base -->
    <div class="absolute inset-0 bg-white"></div>

    <!-- Background Image -->
    <div
      class="absolute inset-0 bg-cover bg-center opacity-100"
      :style="{
        backgroundImage: `url(${backgroundImage})`,
      }"
    ></div>

    <!-- Opacity Overlay Layer -->
    <div class="absolute inset-0 bg-white/70"></div>

    <!-- Main Container -->
    <div class="max-w-7xl w-full grid grid-cols-1 lg:grid-cols-2 gap-12 items-center relative z-10">
      <!-- left : Platform Info -->
      <div class="space-y-5">
        <Chip label="Open-source platform" class="bg-primary text-white font-bold border-none" />

        <h2 class="text-4xl font-bold leading-tight">
          Secure Health Data Governance
          <br />
          <span class=""> for Research & Public Health </span>
        </h2>

        <p class="max-w-8xl text-lg">
          OpenHealth Lake provides a secure and scalable environment for managing structured and
          unstructured health data. It serves as a supplementary tool for data management and can be
          adapted to various use cases.
        </p>

        <ul class="space-y-3 mt-6">
          <li v-for="feature in features" :key="feature.label" class="flex items-center">
            <i :class="feature.icon" class="mr-3 text-primary"></i>
            {{ feature.label }}
          </li>
        </ul>
      </div>

      <!-- RIGHT SIDE : Login Card -->
      <div class="flex justify-center lg:justify-end">
        <div
          class="bg-white/90 backdrop-blur-md shadow-2xl rounded-2xl p-10 w-full max-w-md flex flex-col items-center"
        >
          <!-- Logo -->
          <div class="text-center mb-8">
            <div class="flex items-center justify-center">
              <img :src="logo" alt="Lakehouse Logo" class="w-10 h-10 mr-2 object-contain" />
              <h3 class="text-3xl font-bold">OpenHealth</h3>
              <h3 class="text-3xl font-bold text-primary">Lake</h3>
            </div>

            <p class="text-gray-500 text-sm mt-3">Sign in to your workspace</p>
          </div>

          <!-- Form -->
          <div class="w-full space-y-5">
            <InputGroup>
              <InputGroupAddon>
                <i class="pi pi-envelope text-primary"></i>
              </InputGroupAddon>
              <InputText
                v-model="formValues.email"
                type="email"
                placeholder="Email"
                class="w-full"
              />
            </InputGroup>

            <InputGroup>
              <InputGroupAddon>
                <i class="pi pi-lock text-primary"></i>
              </InputGroupAddon>
              <Password
                v-model="formValues.password"
                placeholder="Password"
                toggleMask
                :feedback="false"
                class="w-full"
              />
            </InputGroup>

            <div class="flex justify-end">
              <Button
                variant="text"
                size="small"
                @click="openPasswordRecoveryModal()"
                label="Forgot Password?"
              />
            </div>

            <div class="space-y-4 pt-6">
              <Button
                class="w-full bg-primary text-white border-none"
                @click="loginOnSubmit"
                label="Login"
              />

              <Button
                class="w-full bg-gray-800 text-white border-none"
                @click="openSubscribeModal()"
                label="Sign Up"
              />
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Footer -->
    <footer class="absolute bottom-6 w-full text-center text-sm text-gray-600">
      <div class="flex flex-col items-center space-y-10">
        <!-- Powered By -->
        <div>
          <div class="text-gray-700 mb-4">Powered by:</div>
          <div class="flex flex-row items-center gap-x-7">
            <img :src="inform_logo" alt="Logo" class="h-16" />
            <img :src="dsi_logo" alt="Logo" class="h-15" />
            <img :src="ceri_logo" alt="Logo" class="h-20" />
            <img :src="ita_logo" alt="Logo" class="h-14" />
            <img :src="comp2bio_logo" alt="Logo" class="h-4" />
          </div>
          <!-- Powered by
          <span class="font-semibold text-[#2a95ea]"> INFORM Africa Hub </span> -->
        </div>

        <!-- GitHub Link -->
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

<style scoped>
.pattern {
  background-image: url("data:image/svg+xml,%3Csvg width='80' height='80' viewBox='0 0 80 80' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath fill='%23ffffff' fill-opacity='0.12' d='M35 20h10v15h15v10H45v15H35V45H20V35h15z'/%3E%3C/svg%3E");
  background-repeat: repeat;
}
</style>
