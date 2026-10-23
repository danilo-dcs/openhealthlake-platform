<!-- UploadFileContent -->

<script setup lang="ts">
import Toast from 'primevue/toast'
import Select from 'primevue/select'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Chip from 'primevue/chip'
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
import { defaultColors, type FileCategory, type ProcessingLevel } from '@/shared/interfaces/types'

import { apiRequestHandler } from '@/shared/api/apiRequestHandler'
import type { CatalogFileRecord } from '@/shared/interfaces/http/CatalogFileResponse'
import type { Label } from '@/shared/interfaces/http/CreateCollectionPayload'

const toast = useToast()

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
  labels: [] as Label[]
})

const newLabel = ref<Label>({
  value: "",
  color: ""
})

const colorOptions = ref<Record<string, string>>(defaultColors)


// LIFECYCLE
onMounted(() => {
  const param = dialogRef.value.data
  collection.value = param as CatalogCollectionRecord
})

// ACTIONS

const closeDialog = () => {
  dialogRef.value.close()
}

const addLabel = () => {
  formValues.value.labels?.push(newLabel.value)

  newLabel.value = {
    value: "",
    color: ""
  }
}

const removeLabel = (index: number) => {
  formValues.value.labels?.splice(index, 1);
}

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
    const uploadFileResponse = await uploadRequest(collectionId, file)

    if (!uploadFileResponse.upload_url || !uploadFileResponse.method) {
      throw new Error('The storage API returned an incomplete upload request.')
    }

    await uploadFile(file, uploadFileResponse.upload_url, uploadFileResponse.method)

    const file_record = await completeUploadRequest(uploadFileResponse.catalog_record_id)

    if(!file_record){
      toast.add({
        severity: 'warning',
        summary: 'Warning',
        detail: 'File was successfully uploaded but it\'s not ready to be used. Please contact admin!',
        life: 6000,
      })
    } else {
      toast.add({
        severity: 'success',
        summary: 'Success',
        detail: 'File was successfully uploaded and it\'s now ready to be used!',
        life: 6000,
      })
    }

    dialogRef.value.close({ refresh: true })

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

const completeUploadRequest = async (catalog_file_id: string): Promise<CatalogFileRecord> => {
  const url = `/storage/files/${catalog_file_id}/complete`

  const responseData = await apiRequestHandler<CatalogFileRecord>(url, 'GET')

    return responseData
}

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
    labels: formValues.value.labels,
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

    <Divider />

    <span class="mb-4 block font-bold">Add Labels</span>

    <div class="grid grid-cols-12 gap-4">
      <div class="col-span-5 flex items-center">
        <InputText
          v-model="newLabel.value"
          name="name"
          placeholder="label value"
          class="w-full"
        />
      </div>

      <div class="col-span-5 flex items-center">
        <Select
          v-model="newLabel.color"
          name="color"
          :options="Object.keys(colorOptions)"
          placeholder="label color"
          class="w-full"
        >
          <template #value="{ value }">
            <span
              v-if="value"
              class="inline-block rounded px-2 py-1 text-white"
              :style="{ backgroundColor: colorOptions[value] }"
            >
              {{ value }}
            </span>
            <span v-else class="text-gray-500">label color</span>
          </template>

          <template #option="{ option }">
            <span
              class="inline-block rounded px-2 py-1 text-white"
              :style="{ backgroundColor: colorOptions[option] }"
            >
              {{ option }}
            </span>
          </template>
        </Select>
      </div>

      <div class="col-span-2 flex items-center">
        <Button
          type="button"
          icon="pi pi-plus"
          aria-label="Add label"
          @click="addLabel"
        />
      </div>
    </div>

    <div id="label-items" class="mt-4">
      <span class="mb-2 block font-bold">Labels:</span>

      <div v-if="formValues.labels?.length" class="flex flex-wrap items-start gap-2">
        <Chip
          v-for="(item, index) in formValues.labels"
          :key="`${item.value}-${index}`"
          :label="item.value"
          removable
          class="text-white"
          :style="{ backgroundColor: item.color }"
          @remove="removeLabel(index)"
        />
      </div>
      <div v-else class="flex justify-center">
        <Chip  label="No labels created" class="font" />
      </div>
    </div>

    <Divider />

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
