<script setup lang="ts">
import { inject, ref, type Ref } from 'vue'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Button from 'primevue/button'
import Calendar from 'primevue/calendar'
import Divider from 'primevue/divider'
import { useCatalogStore } from '@/stores/catalogStore'
import { useToast } from 'primevue/usetoast'
import type {
  CollectionFilter
} from '@/shared/interfaces/http/CollectionSearchRequest'
import type { OperatorKey } from '@/shared/interfaces/types'

import type { DynamicDialogInstance } from 'primevue/dynamicdialogoptions'

const dialogRef = inject('dialogRef') as Ref<DynamicDialogInstance>
const toast = useToast()
const catalogStore = useCatalogStore()

const properties = [
  { key: 'collection_id', label: 'Collection ID' },
  { key: 'collection_name', label: 'Collection Name' },
  { key: 'is_public', label: 'Is Public', type: 'boolean' },
  { key: 'inserted_at', label: 'Created At', type: 'date' },
  { key: 'inserted_by', label: 'Created By' },
  { key: 'storage_type', label: 'Storage Type' },
  { key: 'location', label: 'Location' },
  { key: 'collection_description', label: 'Description' },
  { key: 'status', label: 'Status' },
]

const operatorOptions = ref<Record<OperatorKey, string>>({
  equals: '=',
  'not equals': '!=',
  contains: '*',
  'greater than': '>',
  'lower than': '<',
})

const operators = ref<Record<string, OperatorKey>>({})

const formValues = ref<Record<string, any>>({})

properties.forEach((prop) => {
  formValues.value[prop.key] = ''
  operators.value[prop.key] = 'equals'
})

const applyFilters = () => {
  const filters = Object.entries(formValues.value)
    .filter(([_, v]) => v !== '' && v !== null && v !== 0)
    .map(([key, value]) => ({
      property_name: key as CollectionFilter['property_name'],
      property_value: key === 'inserted_at' && value instanceof Date ? value.toISOString() : value,
      operator: operatorOptions.value[operators.value[key]],
    })) as CollectionFilter[]

  if (filters.length === 0) {
    toast.add({
      severity: 'warn',
      summary: 'No filters applied',
      detail: 'Please enter at least one filter before applying.',
      life: 3000,
    })
    return
  }

  catalogStore.setCollectionFilters(filters)
  catalogStore.setIsFilterVisible(false)

  toast.add({
    severity: 'success',
    summary: 'Filters Applied',
    detail: `${filters.length} filters added successfully.`,
    life: 3000,
  })

  dialogRef.value.close()
}

const clearFilters = () => {
  for (const key in formValues.value) formValues.value[key] = ''
  for (const key in operators.value) operators.value[key] = 'equals'
}
</script>

<template>
  <div class="flex flex-col gap-4 p-4">
    <div
      v-for="prop in properties"
      :key="prop.key"
      class="grid grid-cols-1 sm:grid-cols-3 gap-2 items-center"
    >
      <label :for="prop.key" class="font-medium text-gray-700 capitalize">
        {{ prop.label }}
      </label>

      <Select
        v-model="operators[prop.key]"
        :options="Object.keys(operatorOptions)"
        class="w-full sm:w-32"
        placeholder="="
      />

      <template v-if="prop.type === 'date'">
        <Calendar v-model="formValues[prop.key]" date-format="yy-mm-dd" show-icon class="w-full" />
      </template>

      <template v-else-if="prop.type === 'boolean'">
        <Select
          v-model="formValues[prop.key]"
          :options="[
            { label: 'Yes', value: true },
            { label: 'No', value: false },
          ]"
          optionLabel="label"
          optionValue="value"
          placeholder="Select"
          class="w-full"
        />
      </template>

      <template v-else>
        <InputText
          v-model="formValues[prop.key]"
          :id="prop.key"
          placeholder="Enter value"
          class="w-full"
        />
      </template>
    </div>

    <div class="flex justify-end mt-4 gap-2">
      <Button
        label="Apply Filters"
        icon="pi pi-filter"
        class="bg-[#3986c2] border-none text-white hover:bg-[#3276ac]"
        @click="applyFilters"
      />
      <Button
        label="Clear"
        icon="pi pi-times"
        outlined
        severity="secondary"
        @click="clearFilters"
      />
    </div>
  </div>
</template>
