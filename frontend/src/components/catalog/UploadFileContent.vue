<!-- UploadFileContent -->

<script setup lang="ts">
import Toast from 'primevue/toast'
import Select from 'primevue/select'
import InputNumber from 'primevue/inputnumber'
import Divider from 'primevue/divider'
import Button from 'primevue/button'
import ButtonGroup from 'primevue/buttongroup'
import TextArea from 'primevue/textarea'
import FileUpload, { type FileUploadSelectEvent } from 'primevue/fileupload'

import type { CatalogCollectionRecord } from '@/shared/interfaces/http/CatalogCollectionResponse'
import type { DynamicDialogInstance } from 'primevue/dynamicdialogoptions'
import { useToast } from 'primevue/usetoast'
import { onMounted, ref, inject, type Ref, computed } from 'vue'
import type { UploadFileRequestPayload } from '@/shared/interfaces/http/UploadFileRequestPayload'
import type { UploadFileResponse } from '@/shared/interfaces/http/UploadFileResponse'
import { useRouter } from 'vue-router'
import type { FileCategory, ProcessingLevel } from '@/shared/interfaces/types'

import { useUserStore } from '@/stores/userStore'
import { apiRequestHandler } from '@/shared/api/apiRequestHandler'

const userStore = useUserStore()

const toast = useToast()
const router = useRouter()

const dialogRef = inject('dialogRef') as Ref<DynamicDialogInstance>

const collection = ref<CatalogCollectionRecord>()

const submitted = ref<boolean>(false)

const file_categories = ref<string[]>(['structured', 'unstructured'])

const file_processing_levels = ref<string[]>(['raw', 'processed', 'curated'])

const selectedFile = ref<File | null>(null)

const isUploading = ref<boolean>(false)

const pythonLink = ref<string>('')

const RLink = ref<string>('')

const formValues = ref<UploadFileRequestPayload>({
  collection_catalog_id: collection.value?.id || '',
  file_name: '',
  file_category: 'unstructured' as FileCategory,
  file_version: 1,
  file_size: 0,
  processing_level: 'raw' as ProcessingLevel,
  file_description: '',
})

const closeDialog = () => {
  dialogRef.value.close()
}

// LIFECYCLE
onMounted(() => {
  const param = dialogRef.value.data
  collection.value = param as CatalogCollectionRecord
})

// ACTIONS

const getFileCategoryExamples = (category: FileCategory | undefined): string => {
  return category === 'structured'
    ? '*Columnar or document files such as csv, tsv, excel, json, parquet.'
    : category === 'unstructured'
      ? '*Binary or textual files such as doc, docx, FASTA, pdf, txt, html, images, videos, zip, tar, gz, BAM, pptx, ai, eps, etc.'
      : ''
}

const onFileSelect = (event: FileUploadSelectEvent) => {
  let file = event.files

  if (Array.isArray(event.files)) {
    file = event.files[0]
  }

  selectedFile.value = file

  formValues.value.file_size = file.size || 0
  formValues.value.file_name = file.name || ''
}

const uploadFileAction = async (): Promise<void> => {
  const file = selectedFile.value
  if (!file) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Choose a file before uploading.',
      life: 4000,
    })
    return
  }

  const collectionId = collection.value?.id
  if (!collectionId) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'The collection could not be identified. Close this dialog and try again.',
      life: 4000,
    })
    return
  }

  isUploading.value = true
  try {
    const response = await uploadRequest(collectionId, file)
    if (!response.upload_url || !response.method) {
      throw new Error('The storage API returned an incomplete upload request.')
    }

    await uploadFile(file, response.upload_url, response.method)

    toast.add({
      severity: 'success',
      summary: 'Success',
      detail: 'File was successfully uploaded!',
      life: 4000,
    })
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Upload failed',
      detail: error instanceof Error ? error.message : 'An unexpected error occurred.',
      life: 6000,
    })
  } finally {
    isUploading.value = false
  }
}

// API REQUESTS
const uploadRequest = async (collectionId: string, file: File): Promise<UploadFileResponse> => {
  const url = '/storage/files/upload-request'

  const body: UploadFileRequestPayload = {
    collection_catalog_id: collectionId,
    file_name: file.name,
    file_category: formValues.value.file_category,
    file_version: formValues.value.file_version,
    file_size: file.size,
    processing_level: formValues.value.processing_level,
    file_description: formValues.value.file_description,
  }

  const responseData = await apiRequestHandler<UploadFileResponse>(url, 'POST', body)

  return responseData
}

const uploadFile = async (file: File, url: string, method: string): Promise<void> => {
  toast.add({
    severity: 'info',
    summary: 'Uploading...',
    detail: `Uploading ${file.name}…`,
    life: 3000,
  })

  const response = await fetch(url, {
    method,
    headers: {
      'Content-Type': 'application/octet-stream',
    },
    body: file,
  })

  if (!response.ok) {
    const responseDetail = await response.text()
    throw new Error(
      `Storage upload failed (${response.status}${response.statusText ? ` ${response.statusText}` : ''})${responseDetail ? `: ${responseDetail}` : '.'}`,
    )
  }

}
</script>

<template>
  <Toast />

  <div class="flex items-center justify-center gap-4 p-5">
    <p>*Use the Python and R packages to upload large files:</p>
    <ButtonGroup>
      <Button
        as="a"
        :href="pythonLink"
        label="Python"
        size="small"
        link
        target="_blank"
        rel="noopener noreferrer"
      />
      <Button
        as="a"
        :href="RLink"
        label="R"
        size="small"
        link
        target="_blank"
        rel="noopener noreferrer"
      />
    </ButtonGroup>
  </div>

  <div class="flex flex-col justify-center">
    <FileUpload
      class="mt-3"
      mode="basic"
      name="file"
      :auto="false"
      @select="onFileSelect"
      customUpload
      :maxFileSize="1000000000"
    >
      <template #empty>
        <span>Drag and drop files to here to upload.</span>
      </template>
    </FileUpload>
  </div>
  <div class="flex flex-col gap-6">
    <div>
      <label for="file_category" class="block font-bold mb-3">Type</label>
      <Select
        id="file_category"
        v-model="formValues.file_category"
        :options="file_categories"
        placeholder="Select a type"
        fluid
      ></Select>
      <small class="text-blue-500"> {{ getFileCategoryExamples(formValues.file_category) }} </small>
      <small v-if="submitted && !formValues.file_category" class="text-red-500"
        >Type is required.</small
      >
    </div>

    <div>
      <div class="flex items-baseline gap-2">
        <label for="processing_level" class="block font-bold mb-3">State</label>
        <small class="text-gray-500">(quality of data)</small>
      </div>
      <Select
        id="processing_level"
        v-model="formValues.processing_level"
        :options="file_processing_levels"
        placeholder="Select a processing lever"
        fluid
      ></Select>
      <small v-if="submitted && !formValues.processing_level" class="text-red-500"
        >Type is required.</small
      >
    </div>

    <div>
      <label for="version" class="block font-bold mb-3">File Version</label>
      <InputNumber id="version" v-model="formValues.file_version" required autofocus fluid />
    </div>

    <div>
      <label for="description" class="block font-bold mb-3">Description (Optional)</label>
      <TextArea id="description" v-model="formValues.file_description" rows="3" cols="20" fluid />
    </div>

    <Divider />

    <Button
      class="mx-auto mt-5 p-2"
      severity="bg-primary-500"
      label="Upload"
      icon="pi pi-cloud-upload"
      @click="uploadFileAction()"
      :disabled="isUploading"
      :loading="isUploading"
    />

    <!-- <div>
      <span class="block font-bold mb-4">Secret</span>
      <div class="grid grid-cols-12 gap-4">
        <div class="flex items-center gap-2 col-span-6">
          <RadioButton id="secret1" v-model="newCollection.secret" name="secret" :value="true" />
          <label for="public1">Yes</label>
        </div>
        <div class="flex items-center gap-2 col-span-6">
          <RadioButton id="secret2" v-model="newCollection.secret" name="secret" :value="false" />
          <label for="public2">No</label>
        </div>
      </div>
    </div> -->
  </div>
</template>
