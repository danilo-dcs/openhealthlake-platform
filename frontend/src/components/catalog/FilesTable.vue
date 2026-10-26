<!-- Files Table Component -->

<script setup lang="ts">
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import Toast from 'primevue/toast'
import DynamicDialog from 'primevue/dynamicdialog'
import Chip from 'primevue/chip'
import Tag from 'primevue/tag'
import ProgressSpinner from 'primevue/progressspinner'

import { useToast } from 'primevue/usetoast'
import { useDialog } from 'primevue/usedialog'

import { FilterMatchMode } from '@primevue/core/api'

import { ref, onMounted, nextTick, computed, watch } from 'vue'

import type { UserPassportResponse } from '@/shared/interfaces/http/UserVisasResponse'
import type {
  CatalogFileRecord,
  CatalogFileResponse,
} from '@/shared/interfaces/http/CatalogFileResponse'
import moment from 'moment'
import FileInfoContent from '@/components/catalog/FileInfoContent.vue'
import DeleteFileContent from '@/components/catalog/DeleteFileContent.vue'
import EditFileDialogContent from '@/components/catalog/EditFileDialogContent.vue'

import type { DownloadFilePayload } from '@/shared/interfaces/http/DownloadFilePayload'
import type { DownloadFileRequesResponse } from '@/shared/interfaces/http/DownloadFileRequesResponse'
import { useRouter } from 'vue-router'

import { useCatalogStore } from '@/stores/catalogStore'

import { useUserStore } from '@/stores/userStore'
import { apiRequestHandler } from '@/shared/api/apiRequestHandler'
import type { DynamicDialogCloseOptions } from 'primevue/dynamicdialogoptions'
import { defaultColors } from '@/shared/interfaces/types'

const userStore = useUserStore()

const dialog = useDialog()
const toast = useToast()
const router = useRouter()

const store = useCatalogStore()

const props = withDefaults(defineProps<{
  collectionId?: string
  refreshKey?: number
}>(), {
  collectionId: '',
  refreshKey: 0,
})

const catalogApiInfo = {
  files: {
    all: '/catalog/files/all/',
    search: '/catalog/files/search',
  },
}

const user_id = computed(() => userStore.userId)

const tableItems = ref<CatalogFileRecord[]>([])
const tableLoading = ref(true)

const totalRecordsNumber = ref<number>(1)
const paginatorValue = ref<number>(1)

const userPassport = ref<UserPassportResponse>()

const userCollectionAccess = ref<string[]>([])

const filters = ref({
  global: { value: null, matchMode: FilterMatchMode.CONTAINS },
})

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

const getStateColor = (state: string): string => {
  switch (state) {
    case 'raw':
      return '#e79e4c'
    case 'processed':
      return '#5794b5'
    case 'curated':
      return '#27b270'
    default:
      return 'gray'
  }
}

// LIFECYCLE

onMounted(() => {
  updateComponentData()
})

watch(
  () => props.refreshKey,
  async (refreshKey, previousRefreshKey) => {
    if (refreshKey <= 0 || refreshKey === previousRefreshKey) return
    tableLoading.value = true
    await fetchFileCatalog()
  },
)

const updateCurrentPage = (event: any) => {
  paginatorValue.value = Number(event?.page ?? 1) + 1
  // fetchUserFileCatalog()
  fetchFileCatalog()
}

const updateComponentData = async () => {
  await Promise.all([fetchFileCatalog(), fetchUserPassports()])
}

// ACTIONS

const openDeleteFileDialog = (data: CatalogFileRecord) => {
  const dialogSpecs = {
    props: { ...dialogDefaultProps, header: 'Delete File' },
    templates: {},
    data: data,
    onClose: async (options?: DynamicDialogCloseOptions) => {
      if (options?.data?.refresh) {
        await updateComponentData()
        await nextTick()
      }
    },
  }

  const dialogRef = dialog.open(DeleteFileContent, dialogSpecs)
}

const openEditFileDialog = (data: CatalogFileRecord) => {
  const dialogSpecs = {
    props: { ...dialogDefaultProps, header: 'Edit File Details' },
    templates: {},
    data,
    onClose: async (options?: DynamicDialogCloseOptions) => {
      if (options?.data?.refresh) {
        await updateComponentData()
        await nextTick()
      }
    },
  }

  dialog.open(EditFileDialogContent, dialogSpecs)
}

const extractUserCollections = (passport: UserPassportResponse): string[] => {
  return passport.passportVisaAssertions
    ? passport.passportVisaAssertions.map((item) => item.passportVisa.visaName.split(':')[0])
    : []
}

function formatSize(bytes: number) {
  const kb = bytes / 1024
  if (kb < 1024) return `${kb.toFixed(2)} KB`
  else return `${(kb / 1024).toFixed(2)} MB`
}

const extractEmail = (s: string): string => {
  const [_, email] = s.split(':')
  return email
}

const formatUnixDate = (timestamp: number): string => {
  return moment.unix(timestamp).format('YYYY-MM-DD')
}

const displayItemInfo = (data: CatalogFileRecord) => {
  const dialogSpecs = {
    props: { ...dialogDefaultProps, header: 'Additional Info' },
    templates: {},
    data: data,
    onClose: () => {},
  }

  const dialogRef = dialog.open(FileInfoContent, dialogSpecs)
}

const donwloadItemFile = async (data: CatalogFileRecord) => {
  const downloadFileResponse = (await downloadFileFileRequest(data.id)) as DownloadFileRequesResponse

  if (!downloadFileResponse) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Unable to fetch download link',
      life: 4000,
    })
  }

  toast.add({
    severity: 'info',
    summary: 'File Download',
    detail: 'Downloading file in the background',
    life: 4000,
  })

  // streamDownloadToFile(downloadFileResponse.download_url, data.file_name)
  downloadFile2(downloadFileResponse.download_url, data.file_name)
}

// API REQUESTS
const fetchUserPassports = async () => {
  try {
    const url = `/user/visas/${user_id.value}`

    const responseData = await apiRequestHandler<UserPassportResponse>(url, 'GET')

    userPassport.value = responseData
    userCollectionAccess.value = extractUserCollections(responseData)
  } catch (error) {
    console.error('Fetch error:', error)
    toast.add({
      severity: 'error',
      summary: 'Unable to fetch user visas',
      detail: String(error),
      life: 4000,
    })
  }
}

const fetchFileCatalog = async () => {
  if (!props.collectionId) {
    return []
  }

  try {
    const params = new URLSearchParams({
      page_number: String(paginatorValue.value),
    })

    const url = '/catalog/files/search'

    const body = {
      filters: [
        {
          property_name: 'collection_id',
          operator: '=',
          property_value: props.collectionId,
        },
      ],
      page_number: paginatorValue.value,
    }

    const responseData = await apiRequestHandler<CatalogFileResponse>(url, 'POST', body)

    tableItems.value = responseData.records ? responseData.records : []

    tableItems.value = tableItems.value.sort((item1, item2) =>
      item1.collection_name.localeCompare(item2.collection_name),
    )

    totalRecordsNumber.value = responseData.total!
  } catch (error) {
    console.error('Fetch error:', error)
    toast.add({
      severity: 'error',
      summary: 'Unable to fetch collections catalog',
      detail: String(error),
      life: 4000,
    })
  } finally {
    tableLoading.value = false
  }
}

// const fetchUserFileCatalog = async () => {
//   try {
//     const params = new URLSearchParams({
//       page_number: String(paginatorValue.value),
//     })

//     const endpoint = '/catalog/files/all'

//     const url = paginatorValue.value
//       ? `${apiBaseUrl}${endpoint}?${params.toString()}`
//       : `${apiBaseUrl}${endpoint}`

//     const headers = { Authorization: `Bearer ${session_token.value}` }

//     let response = await fetch(url, {
//       headers,
//     })

//     if (response.status === 401) {
//       unauthorizedRequestHandler(router)

//       response = await fetch(url, {
//         headers,
//       })
//     }

//     const data = (await response.json()) as CatalogFileResponse

//     tableItems.value = data.records ? data.records : []

//     tableItems.value = tableItems.value.sort((item1, item2) =>
//       item1.collection_name.localeCompare(item2.collection_name),
//     )

//     totalRecordsNumber.value = data.total!
//   } catch (error) {
//     console.error('Fetch error:', error)
//     toast.add({
//       severity: 'error',
//       summary: 'Unable to fetch collections catalog',
//       detail: String(error),
//       life: 4000,
//     })
//   } finally {
//     tableLoading.value = false
//   }
// }

const downloadFileFileRequest = async (
  file_record_id: string,
): Promise<DownloadFileRequesResponse | void> => {
  try {
    const params = new URLSearchParams({
      page_number: String(paginatorValue.value),
    })

    const url = '/storage/files/download-request'

    const body: DownloadFilePayload = {
      catalog_file_id: file_record_id,
    }

    const responseData = await apiRequestHandler<DownloadFileRequesResponse>(url, 'POST', body)

    return responseData
  } catch (error) {
    console.error('Fetch error:', error)
    toast.add({
      severity: 'error',
      summary: 'Unable to fetch download request',
      detail: String(error),
      life: 4000,
    })
  }
}

const downloadFile2 = async (
  url: string,
  suggestedFileName: string,
): Promise<void> => {
  try {
    const response = await fetch(url)
    if (!response.ok) {
      throw new Error(`Download failed (${response.status})`)
    }

    const blob = await response.blob()
    const objectUrl = URL.createObjectURL(blob)
    const link = document.createElement('a')

    link.href = objectUrl
    link.download = suggestedFileName
    document.body.appendChild(link)
    link.click()
    link.remove()

    // Keep the Blob URL alive briefly while the browser starts the download.
    window.setTimeout(() => URL.revokeObjectURL(objectUrl), 60_000)

    toast.add({
      severity: 'success',
      summary: 'File Download',
      detail: 'The download has started.',
      life: 4000,
    })
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: String(error),
      life: 4000,
    })
  }
}

const streamDownloadToFile = async (url: string, suggestedFileName: string): Promise<void> => {
  let message = ''

  try {
    if (!('showSaveFilePicker' in window)) {
      message = 'File System Access API not supported on this browser.'
      toast.add({
        severity: 'error',
        summary: 'Error',
        detail: message,
        life: 4000,
      })
      throw new Error(message)
    }

    const response = await fetch(url)

    if (!response.body) {
      throw new Error('ReadableStream not supported in fetch response.')
    }

    const fileHandle = await (window as any).showSaveFilePicker({
      suggestedName: suggestedFileName,
    })

    const writableStream = await fileHandle.createWritable()

    const reader = response.body.getReader()
    const writer = writableStream.getWriter()

    try {
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        await writer.write(value)
      }
    } finally {
      await writer.close()
      toast.add({
        severity: 'success',
        summary: 'File Download',
        detail: 'The file was successfully downloaded to the destination folder',
        life: 4000,
      })
    }
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: String(error),
      life: 4000,
    })
  }
}
</script>

<template>
  <Toast />
  <div id="file-table-container" class="flex flex-col h-full min-h-[300px] max-h-[72vh]">
    <DynamicDialog />
    <DataTable
      v-if="tableItems && tableItems.length > 0"
      :value="tableItems"
      class="flex-1 overflow-hidden"
      tableStyle="min-width: 50rem"
      scrollable
      size="small"
      scroll-height="flex"
      :loading="tableLoading"
      stripedRows
    >
      <!-- <DataTable
      v-if="tableItems && tableItems.length > 0"
      :value="tableItems"
      tableStyle="min-width: 50rem"
      class="w-full h-full flex-1 overflow-auto"
      scrollable
      size="small"
      scroll-height="flex"
      :loading="tableLoading"
      :filters="filters"
      filterDisplay="row"
      stripedRows
      :globalFilterFields="['file_name', 'collection_name', 'processing_level', 'file_category']"
    > -->

      <template #loading> Loading files catalog. Please wait ... </template>

      <!-- <template #empty>
        <div class="flex justify-center items-center w-full py-4">
          <Chip
            label="No files available in this collection."
            icon="pi pi-info text-white"
            class="bg-black text-white font-semibold shadow-md"
          />
        </div>
      </template> -->

      <!-- <template #header>
        <div class="flex flex-wrap gap-2 items-center justify-between">
          <IconField>
            <InputIcon>
              <i class="pi pi-search" />
            </InputIcon>
            <InputText v-model="filters['global'].value" placeholder="Search..." />
          </IconField>
        </div>
      </template> -->

      <!-- <template #footer>
        <Paginator
          :template="{
            default: 'FirstPageLink PrevPageLink JumpToPageDropdown NextPageLink LastPageLink',
          }"
          :totalRecords="totalRecordsNumber"
          :rows="1000"
          @page="updateCurrentPage"
        ></Paginator>
      </template> -->

      <Column field="file_name" header="Name"></Column>
      <!-- <Column field="collection_name" header="Collection"></Column> -->
      <Column field="file_size" header="Size">
        <template #body="{ data }">
          {{ formatSize(data.file_size) }}
        </template>
      </Column>
      <Column field="file_version" header="Version"></Column>
      <Column field="processing_level" header="State">
        <template #body="{ data }">
          <Chip
            :label="data.processing_level"
            :style="{ 'background-color': getStateColor(data.processing_level), color: 'white' }"
          />
        </template>
      </Column>
      <Column field="labels" header="Labels">
        <template #body="{ data }">
          <div class="flex flex-wrap items-start gap-1">
            <template v-if="data.labels?.length">
              <Tag
                v-for="label in data.labels"
                :key="label.value"
                :value="label.value"
                :style="{ backgroundColor: label.color }"
                class="text-white"
              />
            </template>

            <Tag v-else value="No Labels" severity="secondary" />
          </div>
        </template>
      </Column>
      <Column class="w-24 !text-end" header="Actions">
        <template #body="{ data }">
          <div class="flex justify-end gap-2">
            <Button
              v-if="user_id && data.inserted_by.includes(user_id)"
              id="edit-file-btn"
              icon="pi pi-pencil"
              @click="openEditFileDialog(data)"
              severity="secondary"
              size="small"
              rounded
              v-tooltip.bottom="'Edit File Details'"
            />
            <Button
              id="info-btn"
              icon="pi pi-search"
              @click="displayItemInfo(data)"
              severity="secondary"
              size="small"
              rounded
              v-tooltip.bottom="'Info'"
            />
            <Button
              id="download-btn"
              icon="pi pi-arrow-circle-down"
              @click="donwloadItemFile(data)"
              severity="secondary"
              size="small"
              rounded
              v-tooltip.bottom="'Download'"
            />
            <Button
              icon="pi pi-trash"
              @click="openDeleteFileDialog(data)"
              severity="secondary"
              size="small"
              rounded
              v-tooltip.bottom="'Delete'"
            />
          </div>
        </template>
      </Column>
    </DataTable>

    <div v-if="tableLoading" class="flex justify-center items-center w-full py-4">
      <ProgressSpinner
        style="width: 50px; height: 50px"
        strokeWidth="8"
        fill="transparent"
        animationDuration=".5s"
        aria-label="Loading"
      />
    </div>

    <div
      v-if="tableItems && tableItems.length === 0 && !tableLoading"
      class="flex justify-center items-center w-full py-4"
    >
      <Chip
        label="No files available in this collection"
        icon="pi pi-info text-white"
        class="bg-black text-white font-semibold shadow-md"
      />
    </div>
  </div>
</template>
