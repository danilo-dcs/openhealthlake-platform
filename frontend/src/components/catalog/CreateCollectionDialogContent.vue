<!-- CreateCollectionDialogButton -->

<script setup lang="ts">
import Button from 'primevue/button'
import Divider from 'primevue/divider'
import InputText from 'primevue/inputtext'
import RadioButton from 'primevue/radiobutton'
import Select from 'primevue/select'
import Textarea from 'primevue/textarea'
import { Toast } from 'primevue'

import { useToast } from 'primevue/usetoast'
import type { CreateCollectionPayload } from '@/shared/interfaces/http/CreateCollectionPayload'
import { onMounted, ref, inject, type Ref } from 'vue'
import type { GetBucketListResponse } from '@/shared/interfaces/http/GetBucketListResponse'

import type { DynamicDialogInstance } from 'primevue/dynamicdialogoptions'

import { useUserStore } from '@/stores/userStore'
import { apiRequestHandler } from '@/shared/api/apiRequestHandler'
import { StorageOptions } from '@/shared/interfaces/types'

const userStore = useUserStore()

// const emit = defineEmits(['refreshView'])
const dialogRef = inject('dialogRef') as Ref<DynamicDialogInstance>

// VARIABLES
const newCollection = ref<CreateCollectionPayload>({
  collection_name: '',
  collection_description: '',
  storage_type: '',
  namenode_address: '',
  bucket_name: '',
  public: false,
  secret: false,
})

const createCollectionLoadingBtn = ref<boolean>(false)

const submitted = ref<boolean>(false)

const storageTypes = ref<string[]>(StorageOptions)

const bucketList = ref<GetBucketListResponse>()

const toast = useToast()

// LIFECYCLE

onMounted(() => {
  fetchStorageBucketList()

  newCollection.value = {
    collection_name: '',
    collection_description: '',
    storage_type: '',
    namenode_address: '',
    bucket_name: '',
    public: false,
    secret: false,
  }
})

// ACTIONS
const closeDialog = () => {
  dialogRef.value.close({
    refresh: true,
  })
}

const hideCollectionDialog = () => {
  dialogRef.value.close({
    refresh: false,
  })
  submitted.value = false
}

const mapBucketList = (storageType: string): string[] => {
  return (
    bucketList.value?.bucket_list
      .filter((item) => item.storage_type === storageType)
      .map((item) => item.bucket_name) ?? ['Unavailable']
  )
}

const saveCollection = async () => {
  createCollectionLoadingBtn.value = !createCollectionLoadingBtn.value

  const payload: CreateCollectionPayload = {
    ...newCollection.value,
  }

  await createNewCollection(payload)
    .then()
    .catch((err) => {
      let message = ''
      if (err instanceof Error) {
        message = err.message
      } else {
        message = 'Failed attempt to create collection'
      }

      toast.add({
        severity: 'danger',
        summary: 'Failed',
        detail: message,
        life: 4000,
      })
    })

  toast.add({
    severity: 'success',
    summary: 'Successful',
    detail: 'Collection Created Successfully!',
    life: 4000,
  })

  createCollectionLoadingBtn.value = !createCollectionLoadingBtn.value

  closeDialog()

  newCollection.value = {
    collection_name: '',
    collection_description: '',
    storage_type: '',
    namenode_address: '',
    bucket_name: '',
    public: false,
    secret: false,
  }
}

// REQUESTS

const createNewCollection = async (payload: CreateCollectionPayload) => {
  const url = `/storage/collections/create`

  await apiRequestHandler<any>(url, 'POST', payload)
}

const fetchStorageBucketList = async () => {
  try {
    const url = `/storage/bucket-list`

    const responseData = await apiRequestHandler<GetBucketListResponse>(url, 'GET')

    bucketList.value = responseData
  } catch (error) {
    console.error('Fetch error:', error)
    toast.add({
      severity: 'error',
      summary: 'Unable to fetch storage buckets',
      detail: String(error),
      life: 4000,
    })
  }
}
</script>

<template>
  <div class="flex flex-col gap-6">
    <Toast />
    <div>
      <label for="name" class="block font-bold mb-3">Name</label>
      <InputText
        id="name"
        v-model.trim="newCollection.collection_name"
        required
        autofocus
        :invalid="submitted && !newCollection.collection_name"
        fluid
      />
      <small v-if="submitted && !newCollection.collection_name" class="text-red-500"
        >Name is required.</small
      >
    </div>
    <div>
      <label for="description" class="block font-bold mb-3">Description</label>
      <Textarea
        id="description"
        v-model="newCollection.collection_description"
        required
        rows="3"
        cols="20"
        fluid
      />
    </div>

    <Divider />

    <div>
      <label for="storage_type" class="block font-bold mb-3">Storage Env.</label>
      <Select
        id="storage_type"
        v-model="newCollection.storage_type"
        :options="storageTypes"
        placeholder="Select a Storage Environment"
        fluid
      ></Select>
      <small v-if="submitted && !newCollection.storage_type" class="text-red-500"
        >Storage Env. is required.</small
      >
    </div>

    <div v-if="newCollection.storage_type === 'hdfs' && !!newCollection.storage_type">
      <label for="location" class="block font-bold mb-3">Storage Bucket</label>
      <Select
        id="location"
        v-model.trim="newCollection.namenode_address"
        required
        autofocus
        :invalid="submitted && !newCollection.namenode_address"
        :options="mapBucketList(newCollection.storage_type)"
        placeholder="Select a Storage Bucket"
        fluid
      />
      <small v-if="submitted && !newCollection.namenode_address" class="text-red-500"
        >Storage Bucket is required.</small
      >
    </div>

    <div v-else-if="!!newCollection.storage_type">
      <label for="location" class="block font-bold mb-3">Storage Bucket</label>
      <Select
        id="location"
        v-model.trim="newCollection.bucket_name"
        required
        autofocus
        :invalid="submitted && !newCollection.bucket_name"
        :options="mapBucketList(newCollection.storage_type)"
        placeholder="Select a Storage Bucket"
        fluid
      />
      <small v-if="submitted && !newCollection.bucket_name" class="text-red-500"
        >Storage Bucket is required.</small
      >
    </div>

    <Divider />

    <div>
      <span class="block font-bold mb-4">Public</span>
      <div class="grid grid-cols-12 gap-4">
        <div class="flex items-center gap-2 col-span-6">
          <RadioButton id="public1" v-model="newCollection.public" name="public" :value="true" />
          <label for="public1">Yes</label>
        </div>
        <div class="flex items-center gap-2 col-span-6">
          <RadioButton id="public2" v-model="newCollection.public" name="public" :value="false" />
          <label for="public2">No</label>
        </div>
      </div>
    </div>

    <div>
      <div class="flex items-baseline gap-2">
        <span class="block font-bold mb-4">Publicly Visible</span>
        <small class="text-gray-500"
          >(yes to publicly list this collection in the catalog, otherwise it will be hidden)</small
        >
      </div>
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
    </div>
  </div>
  <div class="flex items-center justify-end mt-10 gap-2">
    <Button
      label="Create"
      severity="primary-500"
      icon="pi pi-check"
      @click="saveCollection"
      :loading="createCollectionLoadingBtn"
    />
    <Button label="Cancel" icon="pi pi-times" text @click="hideCollectionDialog" />
  </div>
</template>
