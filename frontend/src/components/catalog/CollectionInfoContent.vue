<!-- InfoContent -->

<script setup lang="ts">
import Panel from 'primevue/panel'
import Chip from 'primevue/chip'
import Button from 'primevue/button'
import Toolbar from 'primevue/toolbar'

import FilesTable from '@/components/catalog/FilesTable.vue'
import UploadFileContent from './UploadFileContent.vue'

import { useCatalogStore } from '@/stores/catalogStore'

import type { CatalogCollectionRecord } from '@/shared/interfaces/http/CatalogCollectionResponse'
import type { DynamicDialogInstance } from 'primevue/dynamicdialogoptions'
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
  const dialogSpecs = {
    props: { ...dialogDefaultProps, header: 'Upload File' },
    templates: {},
    data: data,
    onClose: () => {},
  }

  const dialogRef = dialog.open(UploadFileContent, dialogSpecs)
  // const dialogRef = dialog.open(UploadFileDialogContent, dialogSpecs)
}
</script>

<template>
  <Panel class="mt-1 mb-5 bg-gray-200 border-0 shadow-sm">
    <div v-if="collection">
      <div class="col-12"><strong>Collection Name:</strong> {{ collection?.collection_name }}</div>

      <div class="col-12 md:col-8"><strong>Created By:</strong> {{ collection?.inserted_by }}</div>
      <div class="col-12 md:col-4">
        <strong>Created At:</strong> {{ new Date(collection?.inserted_at).toLocaleString() }}
      </div>

      <div class="col-12 sm:col-6 md:col-3">
        <strong>Public:</strong> {{ collection?.public ? 'Yes' : 'No' }}
      </div>
      <div class="col-12 sm:col-6 md:col-3">
        <strong>Storage:</strong> {{ collection?.storage_type.toUpperCase() }}
      </div>
      <div class="col-12 md:col-6"><strong>Bucket Name:</strong> {{ collection?.bucket }}</div>

      <div class="col-12">
        <p v-if="collection?.collection_description">
          <strong>Description:</strong> {{ collection?.collection_description }}
        </p>
        <p v-else><strong>Description:</strong> No description.</p>
      </div>
    </div>

    <p v-else class="mx-2">
      {{ 'No Details provided for this collection.' }}
    </p>
  </Panel>
  <Panel>
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
      <Toolbar class="mb-4 py-3 px-5">
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

      <!-- <div class="flex justify-between mb-3">
        <strong class="my-3">List of Files</strong>
        <Button
          size="small"
          v-tooltip.bottom="'Add file'"
          class="my-3"
          @click="openUploadFileDialog(collection)"
        >
          <i class="pi pi-upload mr-2"></i>
          <span class="hidden sm:inline">Upload File</span>
        </Button>
      </div> -->
      <FilesTable :collectionId="collection?.id" />
    </div>
  </Panel>
</template>
