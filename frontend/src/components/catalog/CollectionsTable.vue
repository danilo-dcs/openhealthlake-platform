<!-- CollectionsTable -->

<script setup lang="ts">
import moment from 'moment'

import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import DynamicDialog from 'primevue/dynamicdialog'
import type { DynamicDialogCloseOptions } from 'primevue/dynamicdialogoptions'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import InputText from 'primevue/inputtext'
import Paginator from 'primevue/paginator'
import Tag from 'primevue/tag'
import Toast from 'primevue/toast'
import ProgressSpinner from 'primevue/progressspinner'
import Chip from 'primevue/chip'

import { useDialog } from 'primevue/usedialog'
import { useToast } from 'primevue/usetoast'
import { FilterMatchMode } from '@primevue/core/api'

import { ref, onMounted, nextTick, computed, watch } from 'vue'

import CreateCollectionDialogContent from '@/components/catalog/CreateCollectionDialogContent.vue'

import RequestAccessContent from '@/components/catalog/RequestAccessContent.vue'
// import UploadFileContent from '@/components/catalog/UploadFileContent.vue'
import InfoContent from '@/components/catalog/CollectionInfoContent.vue'
import ControlAccessContent from '@/components/catalog/ControlAccessContent.vue'
import DeleteCollectionContent from '@/components/catalog/DeleteCollectionContent.vue'
import EditCollectionDialogContent from '@/components/catalog/EditCollectionDialogContent.vue'

import type {
  CatalogCollectionRecord,
  CatalogCollectionResponse,
} from '@/shared/interfaces/http/CatalogCollectionResponse'
import type { UserPassportResponse } from '@/shared/interfaces/http/UserVisasResponse'
import { useRouter } from 'vue-router'

import { useUserStore } from '@/stores/userStore'
import { useCatalogStore } from '@/stores/catalogStore'

import AdvancedFiltersForm from './AdvancedFiltersForm.vue'
import type { CollectionSearchRequest } from '@/shared/interfaces/http/CollectionSearchRequest'
import { apiRequestHandler } from '@/shared/api/apiRequestHandler'
import type { Label } from '@/shared/interfaces/http/CreateCollectionPayload.ts'

const userStore = useUserStore()
const catalogStore = useCatalogStore()
const dialog = useDialog()
const toast = useToast()
const router = useRouter()

const { viewmode = 'all' } = defineProps<{
  viewmode?: string
}>()

const catalogApiInfo = {
  all: '/catalog/collections/all/',
  search: '/catalog/collections/search',
  create: '/storage/collections/create',
}

const user_id = computed(() => userStore.userId)

const tableItems = ref<CatalogCollectionRecord[]>([])
const tableLoading = ref(true)

const totalRecordsNumber = ref<number>(1)
const paginatorValue = ref<number>(1)

const userPassport = ref<UserPassportResponse>()
const userCollectionAccess = ref<string[]>([])

const applyFiltersVisible = ref(catalogStore.is_filter_visible)

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

const getStatusColor = (status: string): string => {
  switch (status) {
    case 'unavailable':
      return 'danger'

    case 'restricted':
      return 'danger'

    case 'open':
      return 'success'

    case 'owner':
      return 'contrast'

    case 'ready':
      return 'success'
  }

  return 'success'
}

const getAccessStatus = (data: CatalogCollectionRecord): string => {
  return user_id.value && data.inserted_by.includes(user_id.value!)
    ? 'owner'
    : data.public || userCollectionAccess.value.includes(data.id)
      ? 'open'
      : 'restricted'
}

const getStorageSeverity = (status: string): string => {
  switch (status) {
    case 's3':
      return 'danger'

    case 'gcs':
      return 'info'

    case 'hdfs':
      return 'warn'
  }

  return 'info'
}

let initialized = false

// LIFECYCLE

// watch(
//   () => catalogStore.is_filter_visible,
//   async (newValue) => {
//     if (!initialized) return
//     await nextTick()
//     if (!newValue) await fetchUserCollectionsFilter()
//   },
// )

onMounted(async () => {
  initialized = true
  await updateComponentData()
})

const updateCurrentPage = async (event: any) => {
  paginatorValue.value = Number(event?.page ?? 1) + 1

  if (applyFiltersVisible.value) {
    await fetchUserCollectionCatalog()
  } else {
    await fetchUserCollectionsFilter()
  }
}

const updateComponentData = async () => {
  applyFiltersVisible.value = catalogStore.is_filter_visible

  if (applyFiltersVisible.value) {
    await fetchUserCollectionCatalog()
  } else {
    await fetchUserCollectionsFilter()
  }

  fetchUserPassports()
}

// ACTIONS

const extractUserCollections = (passport: UserPassportResponse): string[] => {
  return passport.passportVisaAssertions
    ? passport.passportVisaAssertions.map((item) => item.passportVisa.visaName.split(':')[0])
    : []
}

const extractEmail = (s: string): string => {
  const [_, email] = s.split(':')
  return email
}

const formatUnixDate = (timestamp: number): string => {
  return moment.unix(timestamp).format('YYYY-MM-DD')
}

const toUpper = (s: string): string => {
  return s.toUpperCase()
}

const clearFilters = async () => {
  catalogStore.clearCollectionFilters()
  applyFiltersVisible.value = catalogStore.is_filter_visible
  await nextTick()
  await fetchUserCollectionCatalog()
}

const openFilterDialog = () => {
  const dialogSpecs = {
    props: { ...dialogDefaultProps, header: 'Advanced Filters' },
    templates: {},
    onClose: async () => {
      updateComponentData()
      await nextTick()
    },
  }

  const dialogRef = dialog.open(AdvancedFiltersForm, dialogSpecs)
}

const openCreatCollectionDialog = () => {
  const dialogSpecs = {
    props: { ...dialogDefaultProps, header: 'Create New Collection' },
    templates: {},
    onClose: async () => {
      updateComponentData()
      await nextTick()
    },
  }

  const dialogRef = dialog.open(CreateCollectionDialogContent, dialogSpecs)
}

const openItemInfoDialog = (data: CatalogCollectionRecord) => {
  const dialogSpecs = {
    props: {
      ...dialogDefaultProps,
      header: 'Collection Data',
      style: {
        width: '80vw',
      },
    },
    templates: {},
    data: data,
    modal: true,
    maximizable: true,
    breakpoints: { '960px': '75vw', '640px': '90vw' },
    onClose: () => {},
  }

  const dialogRef = dialog.open(InfoContent, dialogSpecs)
}

const openRequestAccessDialog = (data: CatalogCollectionRecord) => {
  const dialogSpecs = {
    props: { ...dialogDefaultProps, header: 'Access Request' },
    templates: {},
    data: data,
    onClose: () => {},
  }

  const dialogRef = dialog.open(RequestAccessContent, dialogSpecs)
  // const dialogRef = dialog.open(AccessRequestDialogContent, dialogSpecs)
}

const openAccessControlDialog = (data: CatalogCollectionRecord) => {
  const dialogSpecs = {
    props: {
      ...dialogDefaultProps,
      header: 'Access Control',
      style: {
        width: '50vw',
      },
    },
    templates: {},
    data: data,
    onClose: () => {},
  }

  const dialogRef = dialog.open(ControlAccessContent, dialogSpecs)
  // const dialogRef = dialog.open(AccessControlDialogContent, dialogSpecs)
}

const openDeleteCollectionDialog = (data: CatalogCollectionRecord) => {
  const dialogSpecs = {
    props: {
      ...dialogDefaultProps,
      header: 'Delete Collection',
      style: {
        width: '50vw',
      },
    },
    templates: {},
    data: data,
    onClose: async (options?: DynamicDialogCloseOptions) => {
      if (options?.data?.refresh) {
        await updateComponentData()
        await nextTick()
      }
    },
  }

  const dialogRef = dialog.open(DeleteCollectionContent, dialogSpecs)
}

const openEditCollectionDialog = (data: CatalogCollectionRecord) => {
  const dialogSpecs = {
    props: {
      ...dialogDefaultProps,
      header: 'Edit Collection',
      style: { width: '50vw' },
    },
    templates: {},
    data,
    onClose: async (options?: DynamicDialogCloseOptions) => {
      if (options?.data?.refresh) {
        await updateComponentData()
        await nextTick()
      }
    },
  }

  dialog.open(EditCollectionDialogContent, dialogSpecs)
}

// const openUploadFileDialog = (data: CatalogCollectionRecord) => {
//   const dialogSpecs = {
//     props: { ...dialogDefaultProps, header: 'Upload File' },
//     templates: {},
//     data: data,
//     onClose: () => {},
//   }

//   const dialogRef = dialog.open(UploadFileContent, dialogSpecs)
//   // const dialogRef = dialog.open(UploadFileDialogContent, dialogSpecs)
// }

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

const fetchUserCollectionsFilter = async () => {
  if (catalogStore.collectionFilters.length === 0) return

  try {
    tableLoading.value = true

    const url = `/catalog/collections/search`

    const body = {
      filters: catalogStore.collectionFilters,
      page_number: paginatorValue.value,
    } as CollectionSearchRequest

    const responseData = await apiRequestHandler<CatalogCollectionResponse>(url, 'POST', body)

    tableItems.value = responseData.records ? responseData.records : []

    tableItems.value = tableItems.value.sort((item1, item2) =>
      item1.collection_name.localeCompare(item2.collection_name),
    )

    tableItems.value = tableItems.value.filter((item) =>
      viewmode === 'my' ? item.inserted_by.includes(user_id.value ?? '') : true,
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

const fetchUserCollectionCatalog = async () => {
  try {
    tableLoading.value = true

    const params = new URLSearchParams({
      page_number: String(paginatorValue.value),
    })

    const url = `/catalog/collections/all/?${params.toString()}`

    const responseData = await apiRequestHandler<CatalogCollectionResponse>(url, 'GET')

    tableItems.value = responseData.records ? responseData.records : []

    tableItems.value = tableItems.value.sort((item1, item2) =>
      item1.collection_name.localeCompare(item2.collection_name),
    )

    tableItems.value = tableItems.value.filter((item) =>
      viewmode === 'my' ? item.inserted_by.includes(user_id.value ?? '') : true,
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
</script>

<template>
  <Toast />
  <div id="collections-table-container" class="flex flex-col h-full min-h-[300px] max-h-[72vh]">
    <DynamicDialog />
    <DataTable
      v-if="!tableLoading"
      :value="tableItems"
      class="flex-1 overflow-hidden"
      tableStyle="min-width: 50rem"
      scrollable
      scroll-height="flex"
      :loading="tableLoading"
      :filters="filters"
      filterDisplay="row"
      :globalFilterFields="['collection_name', 'status', 'storage_type', 'location', 'inserted_by']"
    >
      <template #empty>
        <div class="flex justify-center items-center w-full py-4">
          <Chip
            label="No collections available in the catalog"
            icon="pi pi-info text-white"
            class="bg-black text-white font-semibold shadow-md"
          />
        </div>
      </template>

      <template #loading> Loading catalog data. Please wait. </template>

      <template #header>
        <div class="flex flex-wrap gap-2 items-center justify-between">
          <IconField>
            <InputIcon>
              <i class="pi pi-search" />
            </InputIcon>
            <InputText v-model="filters['global'].value" placeholder="Search..." />
          </IconField>
          <div class="flex flex-wrap gap-2">
            <Button
              id="add-btn"
              icon="pi pi-plus"
              @click="openCreatCollectionDialog()"
              severity="primary-500"
              label="New Collection"
              size="small"
              v-tooltip.bottom="'Click to create a new collection'"
            />
            <Button
              v-if="applyFiltersVisible"
              id="filter-btn"
              variant="outlined"
              icon="pi pi-filter"
              @click="openFilterDialog()"
              severity="primary-500"
              label="Apply Filters"
              size="small"
              v-tooltip.bottom="'Click to filter collections'"
            />
            <Button
              v-else
              class="border-none bg-gray-800 hover:bg-gray-700 text-white"
              id="clear-filters"
              icon="pi pi-filter-slash"
              @click="clearFilters()"
              label="Clear Filters"
              size="small"
              v-tooltip.bottom="'Click to filter collections'"
            />
          </div>
        </div>
      </template>

      <template #footer>
        <div id="collections-paginator" class="p-2">
          <Paginator
            :template="{
              default: 'FirstPageLink PrevPageLink JumpToPageDropdown NextPageLink LastPageLink',
            }"
            :totalRecords="totalRecordsNumber"
            :rows="1000"
            @page="updateCurrentPage"
          ></Paginator>
        </div>
      </template>

      <Column field="collection_name" header="Name"></Column>
      <Column field="inserted_by" header="Creator">
        <template #body="{ data }">
          {{ extractEmail(data.inserted_by) }}
        </template>
      </Column>
      <Column field="inserted_at" header="Creation date">
        <template #body="{ data }">
          {{ formatUnixDate(data.inserted_at) }}
        </template>
      </Column>
      <Column field="status" header="Access Status">
        <template #body="{ data }">
          <Tag
            :value="toUpper(getAccessStatus(data))"
            :severity="getStatusColor(getAccessStatus(data))"
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
      <!-- <Column field="storage_type" header="Storage Env">
        <template #body="{ data }">
          <Tag :value="data.storage_type" :severity="getStorageSeverity(data.storage_type)" />
        </template>
      </Column>
      <Column field="location" header="Storage Location"></Column> -->

      <Column class="w-24 !text-end" header="Actions">
        <template #body="{ data }">
          <div class="flex justify-end gap-2">
            <Button
              v-if="user_id && data.inserted_by.includes(user_id)"
              id="edit-collection-btn"
              icon="pi pi-pencil"
              @click="openEditCollectionDialog(data)"
              severity="secondary"
              size="small"
              rounded
              v-tooltip.bottom="'Edit Collection'"
            />
            <Button
              id="info-btn"
              icon="pi pi-folder-open"
              @click="openItemInfoDialog(data)"
              severity="secondary"
              size="small"
              rounded
              v-tooltip.bottom="'Open Collection'"
            />
            <Button
              v-if="
                user_id &&
                !data.inserted_by.includes(user_id) &&
                !userCollectionAccess.includes(data.id) &&
                !data.public
              "
              id="reques-access-btn"
              icon="pi pi-key"
              @click="openRequestAccessDialog(data)"
              severity="secondary"
              size="small"
              rounded
              v-tooltip.bottom="'Request Access'"
            />
            <Button
              v-if="user_id && data.inserted_by.includes(user_id)"
              id="grant-access-btn"
              icon="pi pi-users"
              @click="openAccessControlDialog(data)"
              severity="secondary"
              size="small"
              rounded
              v-tooltip.bottom="'Access Control'"
            />
            <Button
              v-if="user_id && data.inserted_by.includes(user_id)"
              id="delete-collection-btn"
              icon="pi pi-trash"
              @click="openDeleteCollectionDialog(data)"
              severity="secondary"
              size="small"
              rounded
              v-tooltip.bottom="'Delete Collection'"
            />
            <!-- <Button
              v-if="['owner', 'open'].includes(getAccessStatus(data))"
              id="upload-btn"
              icon="pi pi-upload"
              @click="openUploadFileDialog(data)"
              severity="secondary"
              size="small"
              rounded
              v-tooltip.bottom="'Add file'"
            /> -->
          </div>
        </template>
      </Column>
    </DataTable>

    <div v-if="tableLoading" class="flex justify-center items-center w-full h-full py-4">
      <ProgressSpinner
        style="width: 50px; height: 50px"
        strokeWidth="8"
        fill="transparent"
        animationDuration=".5s"
        aria-label="Loading"
      />
    </div>
  </div>
</template>
