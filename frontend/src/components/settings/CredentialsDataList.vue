<!-- CredentialsDataList -->

<script setup lang="ts">
import DataView from 'primevue/dataview'
import Chip from 'primevue/chip'
import Toast from 'primevue/toast'
import ProgressSpinner from 'primevue/progressspinner'

import { ref, onMounted, watch, computed } from 'vue'
import { useToast } from 'primevue/usetoast'
import { useRouter } from 'vue-router'

import type {
  CredentialItem,
  CredentialsAllResponse,
} from '@/shared/interfaces/http/CredentialsAllResponse'
import { useSettingsStore, type SettingsStore } from '@/stores/settingsStore'

import { useUserStore } from '@/stores/userStore'
import { apiRequestHandler } from '@/shared/api/apiRequestHandler'

const userStore = useUserStore()

const toast = useToast()
const router = useRouter()

const store = useSettingsStore() as SettingsStore

const systemCredentials = ref<CredentialsAllResponse>([])

const loading = ref<boolean>(false)

// LIFECYCLE

watch(
  () => store.updateListTrigger,
  (newVal) => {
    if (newVal) {
      updateComponentData()
      store.setUpdateTrigger(false)
    }
  },
)

onMounted(() => {
  updateComponentData()
})

const updateComponentData = async () => {
  fetchCredentials()
  // fetchUserPassports()
}

// ACTIONS

const getIconClass = (item: CredentialItem): string => {
  return item.storage_type === 'gcs'
    ? 'pi pi-google'
    : item.storage_type === 's3'
      ? 'pi pi-amazon'
      : 'pi pi-server'
}

const getStorageColor = (item: CredentialItem): string => {
  return item.storage_type === 'gcs'
    ? 'bg-blue-400'
    : item.storage_type === 's3'
      ? 'bg-red-500'
      : item.storage_type === 'minio' ?
        'bg-orange-500'
        : 'bg-yellow-300'
}

// API REQUESTS
const fetchCredentials = async (): Promise<void> => {
  loading.value = true

  try {
    const url = '/credentials/all'
    const responseData = await apiRequestHandler<CredentialsAllResponse>(url, 'GET')
    systemCredentials.value = responseData
  } catch (error) {
    console.error('Fetch error:', error)
    toast.add({
      severity: 'error',
      summary: 'Unable to fetch system credentials',
      detail: String(error),
      life: 4000,
    })
  } finally {
    loading.value = false
  }
}
</script>
<template>
  <Toast />
  <DataView class="min-w-full" :value="systemCredentials" data-key="credentials">
    <template #empty>
      <div class="flex flex-col justify-center" v-if="loading">
        <ProgressSpinner aria-label="Loading" />
      </div>
      <div v-else class="flex flex-col justify-center">
        <strong>No Data Sources</strong>
      </div>
    </template>
    <template #list="slotProps">
      <div class="flex flex-col">
        <div v-for="(item, index) in slotProps.items" :key="index" class="hover:bg-gray-100">
          <div
            class="flex flex-col sm:flex-row sm:items-center p-6 gap-4"
            :class="{
              'border-t border-surface-200 dark:border-surface-700': index !== 0,
            }"
          >
            <div class="flex flex-col md:flex-row justify-between md:items-center flex-1 gap-6">
              <div class="flex items-center gap-3">
                <div class="w-1 h-12 mr-4" :class="getStorageColor(item)"></div>
                <i :class="getIconClass(item)"></i>
                <div class="ml-5">
                  <span class="font-medium text-surface-500 dark:text-surface-400 text-sm"
                    >Storage Env:</span
                  >
                  <div class="text-lg font-medium mt-2">
                    {{ item.storage_type }}
                  </div>
                </div>
              </div>
              <div class="flex items-center">
                <div>
                  <span class="font-medium text-surface-500 dark:text-surface-400 text-sm"
                    >Storage Buckets</span
                  >
                  <div v-for="bucket in item.bucket_names" class="text-lg font-medium mt-2">
                    <Chip :label="bucket" icon="pi pi-folder" />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>
  </DataView>
</template>
