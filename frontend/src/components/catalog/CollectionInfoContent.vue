<!-- InfoContent -->

<script setup lang="ts">
import Chip from 'primevue/chip'
import Button from 'primevue/button'
import Toolbar from 'primevue/toolbar'

import FilesTable from '@/components/catalog/FilesTable.vue'
import UploadFileContent from './UploadFileContent.vue'

import { useCatalogStore } from '@/stores/catalogStore'

import type { CatalogCollectionRecord } from '@/shared/interfaces/http/CatalogCollectionResponse'
import type { DynamicDialogCloseOptions, DynamicDialogInstance } from 'primevue/dynamicdialogoptions'
import { onMounted, ref, inject, type Ref, computed } from 'vue'
import { useDialog } from 'primevue/usedialog'

import { useUserStore } from '@/stores/userStore'

const userStore = useUserStore()

const dialogRef = inject('dialogRef') as Ref<DynamicDialogInstance>

const dialog = useDialog()

const store = useCatalogStore()

const { collectionId = '' } = defineProps<{
  collectionId?: string
}>()

const user_id = computed(() => userStore.userId)

const collection = ref<CatalogCollectionRecord>()
const filesRefreshKey = ref(0)

const creatorEmail = computed(() => {
  const creator = collection.value?.inserted_by?.trim() ?? ''
  const separatorIndex = creator.lastIndexOf(':')

  return separatorIndex >= 0 ? creator.slice(separatorIndex + 1) : creator
})

const closeDialog = () => {
  dialogRef.value.close()
}

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

onMounted(() => {
  const param = dialogRef.value.data
  collection.value = param as CatalogCollectionRecord
})

const getCollectionsTitle = computed(() => {
  return `${collection.value?.collection_name}'s Description'`
})

const openUploadFileDialog = (data: CatalogCollectionRecord) => {
  filesRefreshKey.value = 0

  const dialogSpecs = {
    props: { ...dialogDefaultProps, header: 'Upload File' },
    templates: {},
    data: data,
    onClose: (options?: DynamicDialogCloseOptions) => {
      if (options?.data?.refresh) {
        filesRefreshKey.value += 1
      }
    },
  }

  const dialogRef = dialog.open(UploadFileContent, dialogSpecs)
  // const dialogRef = dialog.open(UploadFileDialogContent, dialogSpecs)
}
</script>

<template>
  <article class="mb-5 rounded-2xl border border-gray-200 bg-white p-5 shadow-sm sm:p-6">
    <div v-if="collection">
      <div class="mb-5 border-b border-gray-100 pb-5">
        <article class="flex min-w-0 items-center justify-between gap-4 rounded-xl bg-gray-50 p-4">
          <div class="min-w-0">
            <h2 class="text-xs font-semibold uppercase tracking-wide text-gray-500">Collection name</h2>
            <p class="mt-1 break-words text-lg font-semibold text-gray-900">{{ collection.collection_name }}</p>
          </div>
          <span
            class="inline-flex shrink-0 items-center rounded-full px-3 py-1 text-sm font-medium"
            :class="collection.public ? 'bg-emerald-50 text-emerald-700' : 'bg-gray-100 text-gray-700'"
          >
            <span class="mr-2 h-2 w-2 rounded-full" :class="collection.public ? 'bg-emerald-500' : 'bg-gray-400'"></span>
            {{ collection.public ? 'Public' : 'Private' }}
          </span>
        </article>
      </div>

      <dl class="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
        <div class="min-w-0 rounded-xl bg-gray-50 p-4 sm:col-span-2 xl:col-span-3">
          <dt class="text-xs font-semibold uppercase tracking-wide text-gray-500">Created by</dt>
          <dd class="mt-1 break-words text-sm font-medium text-gray-800">{{ creatorEmail }}</dd>
        </div>
        <div class="rounded-xl bg-gray-50 p-4 sm:col-span-2 xl:col-span-1">
          <dt class="text-xs font-semibold uppercase tracking-wide text-gray-500">Created at</dt>
          <dd class="mt-1 text-sm font-medium text-gray-800">{{ new Date(collection.inserted_at).toLocaleString() }}</dd>
        </div>
        <div class="rounded-xl bg-gray-50 p-4">
          <dt class="text-xs font-semibold uppercase tracking-wide text-gray-500">Storage</dt>
          <dd class="mt-1 text-sm font-medium text-gray-800">{{ collection.storage_type.toUpperCase() }}</dd>
        </div>
        <div class="min-w-0 rounded-xl bg-gray-50 p-4">
          <dt class="text-xs font-semibold uppercase tracking-wide text-gray-500">Bucket name</dt>
          <dd class="mt-1 break-words text-sm font-medium text-gray-800">{{ collection.bucket }}</dd>
        </div>
        <div class="rounded-xl bg-gray-50 p-4 sm:col-span-2 xl:col-span-3">
          <dt class="text-xs font-semibold uppercase tracking-wide text-gray-500">Description</dt>
          <dd class="mt-1 whitespace-pre-wrap text-sm leading-6 text-gray-700">
            {{ collection.collection_description || 'No description.' }}
          </dd>
        </div>
      </dl>
    </div>

    <p v-else class="text-sm text-gray-500">
      {{ 'No Details provided for this collection.' }}
    </p>
  </article>
  <article class="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm sm:p-6">
    <div
      v-if="!collection?.public && !collection?.inserted_by.includes(user_id!)"
      class="flex justify-center"
    >
      <Chip
        label="You do not have permission to view the files in this collection. Please request access to
        it!"
        icon="pi pi-lock text-yellow-900"
        class="bg-yellow-500 text-yellow-900 font-semibold"
      />
    </div>

    <div v-else>
      <Toolbar class="mb-4 rounded-xl border border-gray-200 bg-gray-50 px-4 py-3">
        <template #start>
          <strong>List of Files</strong>
        </template>

        <template #end>
          <Button
            size="small"
            v-tooltip.bottom="'Add file'"
            class="py-1 px-3"
            @click="openUploadFileDialog(collection)"
          >
            <i class="pi pi-upload mr-2"></i>
            <span class="hidden sm:inline">Upload File</span>
          </Button>
        </template>
      </Toolbar>

      <FilesTable :collectionId="collection?.id" :refreshKey="filesRefreshKey" />
    </div>
  </article>
</template>
