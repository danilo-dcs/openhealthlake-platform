<!-- CreateCredentialsForm -->

<script setup lang="ts">
import Select from 'primevue/select'
import Textarea from 'primevue/textarea'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'
import Toast from 'primevue/toast'

import { computed, inject, onMounted, ref, type Ref } from 'vue'
import { useToast } from 'primevue/usetoast'
import { useRouter } from 'vue-router'

import type {
  CreateCredentialpayload,
  GoogleCredential,
  HdfsCredential,
  S3Credential,
  MinioCredential
} from '@/shared/interfaces/http/CreateCredentialPayload'
import { StorageOptions, type StorageType } from '@/shared/interfaces/types'

import type { DynamicDialogInstance } from 'primevue/dynamicdialogoptions'

import { useUserStore } from '@/stores/userStore'
import { apiRequestHandler } from '@/shared/api/apiRequestHandler'


const userStore = useUserStore()

const dialogRef = inject('dialogRef') as Ref<DynamicDialogInstance>

const toast = useToast()
const router = useRouter()

const credentialOptions = ref<string[]>(StorageOptions)

const formValues = ref({
  storage_type: '',
  bucket_name: '',
  credential: '',
})

const formPlaceHolder = ref<string>('')

const loading = ref<boolean>(false)

const submitted = ref<boolean>(false)

// LIFECYCLE

onMounted(() => {})

// ACTIONS

const getCredentialTemplateText = (): void => {
  if (formValues.value.storage_type === 'gcs') {
    formPlaceHolder.value = `{
      "type": "string",
      "project_id": "string",
      "private_key_id": "string",
      "private_key": "string",
      "client_email": "string",
      "client_id": "string",
      "auth_uri": "string",
      "token_uri": "string",
      "auth_provider_x509_cert_url": "string",
      "client_x509_cert_url": "string",
      "universe_domain": "string"
  }`
  } else if (formValues.value.storage_type === 's3') {
    formPlaceHolder.value = `{
      "access_key": "string",
      "secret_access_key": "string",
      "region": "string"
    }`
  } else if (formValues.value.storage_type === 'minio') {
    formPlaceHolder.value = `{
      "url": "string"
      "accessKey": "string"
      "secretKey": "string"
      "api": "string"
      "path": "string"
      }`
  } else {
    formPlaceHolder.value = `{
      "user": "string",
      "password": "string"
    }`
  }
}

const sendCredential = async () => {
  loading.value = true

  await postCredential()

  toast.add({
    severity: 'info',
    summary: 'Submitted',
    detail: 'Credential Submitted',
    life: 4000,
  })
  loading.value = false

  dialogRef.value.close({
    updateView: true,
  })
}

// API REQUESTS

const postCredential = async (): Promise<void> => {
  const url = '/credentials/create'

  const body: CreateCredentialpayload = {
    visa_uuids: [],
    bucket_names: [formValues.value.bucket_name],
    storage_type: formValues.value.storage_type as StorageType,
    credential: JSON.parse(formValues.value.credential) as
      | GoogleCredential
      | S3Credential
      | HdfsCredential
      | MinioCredential
  }

  await apiRequestHandler<any>(url, 'POST', body)
}
</script>

<template>
  <div class="flex flex-col gap-5 justify-center">
    <Toast />

    <div>
      <label for="storage_type" class="block font-bold mb-3">Storage Environment</label>
      <Select
        id="storage_type"
        v-model="formValues.storage_type"
        :options="credentialOptions"
        placeholder="Choose the environment type"
        @change="getCredentialTemplateText()"
        fluid
      ></Select>
    </div>

    <div>
      <label for="bucket_name" class="block font-bold mb-3"
        >Bucket Name (or Self-hosted storage location)</label
      >
      <InputText
        v-model.trim="formValues.bucket_name"
        required
        autofocus
        :invalid="submitted && !formValues.bucket_name"
        fluid
      ></InputText>
    </div>

    <div>
      <label for="credential" class="block font-bold mb-3">Access Keys (JSON)</label>
      <Textarea
        v-model="formValues.credential"
        rows="11"
        cols="30"
        autoResize
        fluid
        required
        :placeholder="formPlaceHolder"
        :invalid="submitted && !formValues.bucket_name"
      ></Textarea>
    </div>

    <Button
      label="Add Credential"
      @click="sendCredential()"
      :disabled="loading"
      :loading="loading"
      severity="primary-500"
    ></Button>
  </div>
</template>
