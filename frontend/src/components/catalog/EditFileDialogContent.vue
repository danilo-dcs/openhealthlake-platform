<script setup lang="ts">
import { inject, onMounted, ref, type Ref } from 'vue'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import Chip from 'primevue/chip'
import Divider from 'primevue/divider'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Textarea from 'primevue/textarea'
import Toast from 'primevue/toast'
import type { DynamicDialogInstance } from 'primevue/dynamicdialogoptions'

import { apiRequestHandler } from '@/shared/api/apiRequestHandler'
import type { CatalogFileRecord } from '@/shared/interfaces/http/CatalogFileResponse'
import type { Label } from '@/shared/interfaces/http/CreateCollectionPayload'
import { defaultColors, type FileCategory } from '@/shared/interfaces/types'
import type { UpdateFilePayload } from '@/shared/interfaces/http/UpdateFilePayload'


const dialogRef = inject('dialogRef') as Ref<DynamicDialogInstance>
const toast = useToast()
const fileId = ref('')
const saving = ref(false)
const submitted = ref(false)
const newLabel = ref<Label>({ value: '', color: '' })
const file = ref<UpdateFilePayload>({
  file_category: 'unstructured',
  file_description: '',
  labels: [],
})

const fileCategories: FileCategory[] = ['structured', 'unstructured']

onMounted(() => {
  const data = dialogRef.value.data as CatalogFileRecord
  fileId.value = data.id
  file.value = {
    file_category: data.file_category ?? 'unstructured',
    file_description: data.file_description ?? '',
    labels: Array.isArray(data.labels) ? data.labels.map((label) => ({ ...label })) : [],
  }
})

//ACTIONS
const addLabel = () => {
  const value = newLabel.value.value.trim()
  if (!value || !newLabel.value.color) return

  file.value.labels.push({ value, color: newLabel.value.color })
  newLabel.value = { value: '', color: '' }
}

const removeLabel = (index: number) => {
  file.value.labels.splice(index, 1)
}

const closeDialog = () => dialogRef.value.close({ refresh: false })


// REQUESTS
const saveFile = async () => {
  submitted.value = true
  if (!fileId.value || !fileCategories.includes(file.value.file_category)) return

  saving.value = true
  try {
    await apiRequestHandler(
      `/storage/files/${encodeURIComponent(fileId.value)}`,
      'PATCH',
      file.value,
    )
    toast.add({
      severity: 'success',
      summary: 'Updated',
      detail: 'File details updated successfully.',
      life: 4000,
    })
    dialogRef.value.close({ refresh: true })
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Unable to update file',
      detail: error instanceof Error ? error.message : 'The update request failed.',
      life: 5000,
    })
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <Toast />
  <div class="flex flex-col gap-5">
    <p class="text-sm text-gray-600">
      Edit the file category, description, and labels. The uploaded file itself will not be changed.
    </p>

    <div>
      <label for="edit-file-category" class="mb-2 block font-bold">File category</label>
      <Select
        id="edit-file-category"
        v-model="file.file_category"
        :options="fileCategories"
        placeholder="Select a file category"
        fluid
        :invalid="submitted && !fileCategories.includes(file.file_category)"
      />
      <small v-if="submitted && !fileCategories.includes(file.file_category)" class="text-red-500">
        Select a valid file category.
      </small>
    </div>

    <div>
      <label for="edit-file-description" class="mb-2 block font-bold">Description (optional)</label>
      <Textarea id="edit-file-description" v-model="file.file_description" rows="3" fluid />
    </div>

    <Divider />

    <div>
      <span class="mb-3 block font-bold">Labels (optional)</span>
      <div class="grid grid-cols-12 gap-3">
        <InputText
          v-model="newLabel.value"
          class="col-span-5"
          placeholder="Label value"
          @keydown.enter.prevent="addLabel"
        />
        <Select
          v-model="newLabel.color"
          class="col-span-5"
          :options="Object.keys(defaultColors)"
          placeholder="Label color"
        >
          <template #value="{ value }">
            <span
              v-if="value"
              class="rounded px-2 py-1 text-white"
              :style="{ backgroundColor: defaultColors[value] }"
            >
              {{ value }}
            </span>
            <span v-else class="text-gray-500">Label color</span>
          </template>
          <template #option="{ option }">
            <span class="rounded px-2 py-1 text-white" :style="{ backgroundColor: defaultColors[option] }">
              {{ option }}
            </span>
          </template>
        </Select>
        <Button class="col-span-2" type="button" icon="pi pi-plus" aria-label="Add label" @click="addLabel" />
      </div>

      <div class="mt-3 flex flex-wrap gap-2">
        <Chip
          v-for="(label, index) in file.labels"
          :key="`${label.value}-${index}`"
          :label="label.value"
          removable
          class="text-white"
          :style="{ backgroundColor: defaultColors[label.color] ?? label.color }"
          @remove="removeLabel(index)"
        />
        <Chip v-if="!file.labels.length" label="No labels" />
      </div>
    </div>

    <div class="mt-3 flex justify-end gap-2">
      <Button label="Save Changes" icon="pi pi-check" :loading="saving" @click="saveFile" />
      <Button label="Cancel" icon="pi pi-times" text :disabled="saving" @click="closeDialog" />
    </div>
  </div>
</template>
