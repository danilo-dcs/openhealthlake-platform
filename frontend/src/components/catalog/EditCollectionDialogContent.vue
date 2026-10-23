<script setup lang="ts">
import { inject, onMounted, ref, type Ref } from 'vue'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import Chip from 'primevue/chip'
import Divider from 'primevue/divider'
import InputText from 'primevue/inputtext'
import RadioButton from 'primevue/radiobutton'
import Textarea from 'primevue/textarea'
import Select from 'primevue/select'
import Toast from 'primevue/toast'
import type { DynamicDialogInstance } from 'primevue/dynamicdialogoptions'

import { apiRequestHandler } from '@/shared/api/apiRequestHandler'
import type { CatalogCollectionRecord } from '@/shared/interfaces/http/CatalogCollectionResponse'
import type { Label } from '@/shared/interfaces/http/CreateCollectionPayload'
import { defaultColors } from '@/shared/interfaces/types'

interface UpdateCollectionPayload {
  collection_name: string
  collection_description: string
  public: boolean
  secret: boolean
  labels: Label[]
}

const dialogRef = inject('dialogRef') as Ref<DynamicDialogInstance>

const toast = useToast()

const collectionId = ref('')

const saving = ref(false)

const submitted = ref(false)

const newLabel = ref<Label>({ value: '', color: '' })

const collection = ref<UpdateCollectionPayload>({
  collection_name: '',
  collection_description: '',
  public: false,
  secret: false,
  labels: [],
})

onMounted(() => {
  const data = dialogRef.value.data as CatalogCollectionRecord
  collectionId.value = data.id
  collection.value = {
    collection_name: data.collection_name ?? '',
    collection_description: data.collection_description ?? '',
    public: Boolean(data.public),
    secret: Boolean(data.secret),
    labels: Array.isArray(data.labels) ? (data.labels as unknown as Label[]).map((label) => ({ ...label })) : [],
  }
})


// ACTIONS
const addLabel = () => {
  const value = newLabel.value.value.trim()
  if (!value || !newLabel.value.color) return
  collection.value.labels.push({ value, color: newLabel.value.color })
  newLabel.value = { value: '', color: '' }
}

const removeLabel = (index: number) => {
  collection.value.labels.splice(index, 1)
}

const closeDialog = () => dialogRef.value.close({ refresh: false })


// REQUESTS
const saveCollection = async () => {
  submitted.value = true
  if (!collection.value.collection_name.trim() || !collectionId.value) return

  saving.value = true
  try {
    await apiRequestHandler(
      `/storage/collections/${encodeURIComponent(collectionId.value)}`,
      'PATCH',
      collection.value,
    )
    toast.add({
      severity: 'success',
      summary: 'Updated',
      detail: 'Collection updated successfully.',
      life: 4000,
    })
    dialogRef.value.close({ refresh: true })
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Unable to update collection',
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
      Update the collection details, visibility, and labels. Storage type and bucket cannot be changed.
    </p>

    <div>
      <label for="edit-collection-name" class="mb-2 block font-bold">Name</label>
      <InputText
        id="edit-collection-name"
        v-model.trim="collection.collection_name"
        autofocus
        fluid
        :invalid="submitted && !collection.collection_name.trim()"
      />
      <small v-if="submitted && !collection.collection_name.trim()" class="text-red-500">
        Name is required.
      </small>
    </div>

    <div>
      <label for="edit-collection-description" class="mb-2 block font-bold">Description</label>
      <Textarea
        id="edit-collection-description"
        v-model="collection.collection_description"
        rows="3"
        fluid
      />
    </div>

    <Divider />

    <div>
      <span class="mb-3 block font-bold">Labels</span>
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
            <span v-if="value" class="rounded px-2 py-1 text-white" :style="{ backgroundColor: defaultColors[value] }">
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
          v-for="(label, index) in collection.labels"
          :key="`${label.value}-${index}`"
          :label="label.value"
          removable
          class="text-white"
          :style="{ backgroundColor: defaultColors[label.color] ?? label.color }"
          @remove="removeLabel(index)"
        />
        <Chip v-if="!collection.labels.length" label="No labels" />
      </div>
    </div>

    <Divider />

    <div>
      <span class="mb-3 block font-bold">Public access</span>
      <div class="flex gap-6">
        <div class="flex items-center gap-2">
          <RadioButton v-model="collection.public" input-id="edit-public-yes" name="edit-public" :value="true" />
          <label for="edit-public-yes">Yes</label>
        </div>
        <div class="flex items-center gap-2">
          <RadioButton v-model="collection.public" input-id="edit-public-no" name="edit-public" :value="false" />
          <label for="edit-public-no">No</label>
        </div>
      </div>
    </div>

    <div>
      <span class="mb-3 block font-bold">Hidden from the public catalog</span>
      <div class="flex gap-6">
        <div class="flex items-center gap-2">
          <RadioButton v-model="collection.secret" input-id="edit-secret-yes" name="edit-secret" :value="true" />
          <label for="edit-secret-yes">Yes</label>
        </div>
        <div class="flex items-center gap-2">
          <RadioButton v-model="collection.secret" input-id="edit-secret-no" name="edit-secret" :value="false" />
          <label for="edit-secret-no">No</label>
        </div>
      </div>
    </div>

    <div class="mt-3 flex justify-end gap-2">
      <Button label="Save Changes" icon="pi pi-check" :loading="saving" @click="saveCollection" />
      <Button label="Cancel" icon="pi pi-times" text :disabled="saving" @click="closeDialog" />
    </div>
  </div>
</template>
