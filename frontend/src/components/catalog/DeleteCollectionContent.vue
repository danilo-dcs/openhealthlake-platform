<!-- RequestAccessContent -->

<script setup lang="ts">
import Button from 'primevue/button'
import Toast from 'primevue/toast'
import InputText from 'primevue/inputtext';
import { useToast } from 'primevue'


import type { DynamicDialogInstance } from 'primevue/dynamicdialogoptions'
import { onMounted, ref, inject, type Ref, computed } from 'vue'

import type { CatalogCollectionRecord } from '@/shared/interfaces/http/CatalogCollectionResponse'
import { apiRequestHandler } from '@/shared/api/apiRequestHandler'

const toast = useToast()

const dialogRef = inject('dialogRef') as Ref<DynamicDialogInstance>

const collectionRef = ref<CatalogCollectionRecord>()

const collectionNameField = ref<string|null>(null)

const loading = ref<boolean>(false)

const btnDisabled = computed(() => !(collectionRef.value?.collection_name === collectionNameField.value))

// LIFECYCLE
onMounted(() => {
  const param = dialogRef.value.data
  collectionRef.value = param as CatalogCollectionRecord
})

// ACTIONS

const deleteAction = async () => {
  if (!collectionRef.value?.id) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Missing Collection Reference',
      life: 4000,
    })
    return
  }

  loading.value = true

  try {
    await deleteCollectionRequest()
    toast.add({
      severity: 'success',
      summary: 'Deleted',
      detail: 'Collection deleted successfully.',
      life: 4000,
    })

    dialogRef.value.close({ refresh: true })
  } catch (error) {
    console.error('Unable to delete collection:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Unable to delete the collection.',
      life: 4000,
    })
  } finally {
    loading.value = false
  }
}

// API REQUESTS

const deleteCollectionRequest = (): Promise<void> => {
  return apiRequestHandler<void>(
    `/catalog/collections/delete/${collectionRef.value?.id}`,
    'DELETE'
  )
}

const closeDialog = () => {
  dialogRef.value.close()
}

</script>

<template>
  <Toast />
  <div class="mt-5 flex w-full flex-col justify-center">
    <div class="flex w-full flex-col items-center gap-5">

      <i class="pi pi-exclamation-triangle text-5xl mb-3 text-red-500"></i>

      <span class="mb-4 text-center">
        The collection <b>'{{ collectionRef?.collection_name }}'</b> and all of its files will be deleted permanently. To confirm, type the collection name below. This action cannot be undone.
      </span>

      <InputText
        type="text"
        v-model="collectionNameField"
        placeholder="Collection name"
        variant="filled"
        :invalid="btnDisabled"
      />

      <div class="mt-10 flex w-full justify-end gap-2">
        <Button
          :severity="btnDisabled ? 'secondary' : 'primary'"
          label="Confirm"
          @click="deleteAction()"
          :loading="loading"
          :disabled="btnDisabled"
          class="border-slate-300 text-slate-700 hover:border-slate-400 hover:bg-slate-100 active:bg-slate-200 focus:ring-0 focus:shadow-none"
        />
        <Button
          severity="danger"
          outlined
          label="Cancel"
          @click="closeDialog()"
          :disabled="loading"
        />
      </div>
    </div>
  </div>
</template>
