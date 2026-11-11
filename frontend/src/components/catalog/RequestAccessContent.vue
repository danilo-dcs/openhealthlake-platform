<!-- RequestAccessContent -->

<script setup lang="ts">
import Button from 'primevue/button'
import Toast from 'primevue/toast'
import { useToast } from 'primevue'

import type { CatalogCollectionRecord } from '@/shared/interfaces/http/CatalogCollectionResponse'
import type { DynamicDialogInstance } from 'primevue/dynamicdialogoptions'
import { onMounted, onBeforeUnmount, ref, inject, type Ref, computed } from 'vue'
import type {
  AccessRequestModel,
  AccessRequestSearchResponse,
} from '@/shared/interfaces/http/AccessRequestSearchResponse'
import type { AccessRequestSearchPayload } from '@/shared/interfaces/http/AccessRequestSearchPayload'
import type { AccessRequestCreateResponse } from '@/shared/interfaces/http/AccessRequestCreateResponse'

import { useUserStore } from '@/stores/userStore'
import { apiRequestHandler } from '@/shared/api/apiRequestHandler'

const userStore = useUserStore()

const toast = useToast()

const dialogRef = inject('dialogRef') as Ref<DynamicDialogInstance>

const collection = ref<CatalogCollectionRecord>()

const user_id = computed(() => userStore.userId)
const isCollectionOwner = computed(() => {
  const collectionOwnerId = collection.value?.inserted_by?.split(':', 1)[0]
  return Boolean(user_id.value && collectionOwnerId === user_id.value)
})

const userAccessRequests = ref<AccessRequestSearchResponse>()
const latestOwnerRequests = computed(() => {
  const requests = userAccessRequests.value?.access_requests ?? []
  const latestByUser = new Map<string, AccessRequestModel>()

  for (const request of requests) {
    if (request.requested_by === user_id.value) continue
    const previous = latestByUser.get(request.requested_by)
    if (!previous || request.requested_at > previous.requested_at) {
      latestByUser.set(request.requested_by, request)
    }
  }

  return [...latestByUser.values()].sort((a, b) => b.requested_at - a.requested_at)
})
const inviteEmail = ref('')
const inviteButtonLoading = ref(false)

const sendButtonLoading = ref<boolean>(false)
const duaExpanded = ref(false)
const duaAcknowledged = ref(false)
const duaPdfUrl = ref('')
const duaPdfLoading = ref(false)
const duaPdfError = ref('')
const hasDua = computed(() => Boolean(collection.value?.dua))

// LIFECYCLE
onMounted(() => {
  const param = dialogRef.value.data
  collection.value = param as CatalogCollectionRecord
  duaExpanded.value = hasDua.value

  fetchAccessRequestData()
  if (hasDua.value) fetchCollectionDua()
})

onBeforeUnmount(() => {
  if (duaPdfUrl.value) URL.revokeObjectURL(duaPdfUrl.value)
})

// ACTIONS

const wasRequested = (): boolean => {
  const lastRequest = userAccessRequests.value?.access_requests[0] ?? ({} as AccessRequestModel)

  if (!lastRequest || Object.keys(lastRequest).length === 0) {
    return false
  }

  if (lastRequest && lastRequest.status !== 'requested') {
    return false
  }

  return true
}

const hasDeclinedRequests = (): boolean => {
  const lastRequest = userAccessRequests.value?.access_requests ?? ([] as AccessRequestModel[])

  if (!lastRequest || lastRequest.length === 0) {
    return false
  }

  const declinedRequests = lastRequest.some((item) => item.status === 'revoked')

  return declinedRequests
}

const sendReequest = async () => {
  if (hasDua.value && !duaAcknowledged.value) return

  sendButtonLoading.value = true
  try {
    await createAccessRequest()
    toast.add({
      severity: 'success',
      summary: 'Success',
      detail: 'Access request successfully sent',
      life: 4000,
    })
    await fetchAccessRequestData()
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Unable to send access request',
      detail: error instanceof Error ? error.message : String(error),
      life: 5000,
    })
  } finally {
    sendButtonLoading.value = false
  }
}

const inviteCollaborator = async () => {
  const email = inviteEmail.value.trim()
  if (!email || !collection.value?.id) return

  inviteButtonLoading.value = true
  try {
    const response = await apiRequestHandler<{ message: string }>(
      '/access-request/invite',
      'POST',
      { collection_id: collection.value.id, email },
    )
    toast.add({ severity: 'success', summary: 'Collaborator added', detail: response.message, life: 4000 })
    inviteEmail.value = ''
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Unable to add collaborator',
      detail: error instanceof Error ? error.message : String(error),
      life: 5000,
    })
  } finally {
    inviteButtonLoading.value = false
  }
}

const fetchCollectionDua = async () => {
  if (!collection.value?.id || !collection.value.dua) return
  duaPdfLoading.value = true
  duaPdfError.value = ''
  try {
    const pdf = await apiRequestHandler<Blob>(
      `/storage/collections/${encodeURIComponent(collection.value.id)}/dua`,
      'GET',
      undefined,
      undefined,
      'blob',
    )
    if (duaPdfUrl.value) URL.revokeObjectURL(duaPdfUrl.value)
    duaPdfUrl.value = URL.createObjectURL(new Blob([pdf], { type: 'application/pdf' }))
  } catch (error) {
    duaPdfError.value = error instanceof Error ? error.message : String(error)
  } finally {
    duaPdfLoading.value = false
  }
}

const toggleDuaViewer = () => {
  duaExpanded.value = !duaExpanded.value
}

// API REQUESTS

const createAccessRequest = async (): Promise<AccessRequestCreateResponse> => {
  const url = '/access-request/create'

  const [owner_id, ...rest] = collection.value?.inserted_by.split(':')!

  const body = {
    collection_id: collection.value?.id,
    requested_by: user_id.value,
    owner_id: owner_id,
  }

  const responseData = await apiRequestHandler<AccessRequestCreateResponse>(url, 'POST', body)

  return responseData
}

const fetchAccessRequestData = async () => {
  const url = '/access-request/search'

  const body: AccessRequestSearchPayload = isCollectionOwner.value
    ? { collection_id: collection.value?.id, owner_id: user_id.value || undefined }
    : { collection_id: collection.value?.id, requested_by: user_id.value || undefined }

  const responseData = await apiRequestHandler<AccessRequestSearchResponse>(url, 'POST', body)

  userAccessRequests.value = responseData
}

</script>

<template>
  <Toast />
  <div v-if="isCollectionOwner" class="flex flex-col gap-5">
    <article class="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm sm:p-6">
      <h2 class="text-lg font-semibold text-gray-900">Add a collaborator</h2>
      <p class="mt-1 text-sm text-gray-500">Add an existing OpenHealthLake user to this collection.</p>
      <form class="mt-4 flex flex-col gap-3 sm:flex-row" @submit.prevent="inviteCollaborator">
        <input
          v-model="inviteEmail"
          type="email"
          required
          autocomplete="email"
          placeholder="user@example.com"
          aria-label="User email"
          class="min-w-0 flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-200"
        />
        <Button
          type="submit"
          label="Add"
          icon="pi pi-user-plus"
          :loading="inviteButtonLoading"
          :disabled="inviteButtonLoading || !inviteEmail.trim()"
        />
      </form>
    </article>

    <article class="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm sm:p-6">
      <div class="mb-4">
        <h2 class="text-lg font-semibold text-gray-900">Access requests</h2>
        <p class="mt-1 text-sm text-gray-500">Requests from users asking to access this collection.</p>
      </div>
      <ul v-if="latestOwnerRequests.length" class="divide-y divide-gray-100">
        <li
          v-for="request in latestOwnerRequests"
          :key="request.id"
          class="flex flex-col gap-2 py-4 first:pt-0 last:pb-0 sm:flex-row sm:items-center sm:justify-between"
        >
          <div class="min-w-0">
            <p class="break-all text-sm font-medium text-gray-900">{{ request.requestor_email }}</p>
            <p class="mt-1 text-xs text-gray-500">{{ new Date(request.requested_at * 1000).toLocaleString() }}</p>
          </div>
          <span
            class="inline-flex w-fit rounded-full px-2.5 py-1 text-xs font-semibold capitalize"
            :class="request.status === 'granted' ? 'bg-emerald-50 text-emerald-700' : request.status === 'revoked' ? 'bg-red-50 text-red-700' : 'bg-amber-50 text-amber-700'"
          >{{ request.status }}</span>
        </li>
      </ul>
      <p v-else class="rounded-lg bg-gray-50 px-4 py-6 text-center text-sm text-gray-500">
        No access requests yet.
      </p>
    </article>
  </div>
  <div class="flex flex-column justify-center" v-else-if="wasRequested()">
    <span>
      <i class="pi pi-lock-open text-green-500 mr-4"></i>
      <b>You have already requested access to this collection. Please wait for approval</b>
    </span>
  </div>
  <div class="flex flex-column justify-center mt-5" v-else>
    <div class="flex flex-col items-center">
      <p class="mb-4 text-center">Request access by sending an email to the collection's owner</p>
      <section v-if="hasDua" class="w-full rounded-lg border border-surface-300 p-4">
        <button
          type="button"
          class="flex w-full items-center justify-between text-left font-semibold"
          :aria-expanded="duaExpanded"
          @click="toggleDuaViewer"
        >
          <span>Data Usage Agreement</span>
          <i :class="duaExpanded ? 'pi pi-chevron-up' : 'pi pi-chevron-down'" aria-hidden="true" />
        </button>
        <div v-if="duaExpanded" class="mt-4">
          <div v-if="duaPdfLoading" class="py-8 text-center" role="status">Loading agreement…</div>
          <div v-else-if="duaPdfError" class="flex flex-col items-center gap-3 py-4 text-center">
            <p class="text-red-500">Unable to load the Data Usage Agreement.</p>
            <Button label="Try again" icon="pi pi-refresh" text @click="fetchCollectionDua" />
          </div>
          <iframe
            v-else-if="duaPdfUrl"
            :src="duaPdfUrl"
            title="Data Usage Agreement PDF"
            class="h-[55vh] min-h-80 w-full rounded border"
          />
        </div>
      </section>
      <div v-if="hasDua" class="mt-4 flex w-full items-start gap-3">
        <input
          id="dua-acknowledgment"
          v-model="duaAcknowledged"
          type="checkbox"
          class="mt-1 h-4 w-4"
          :disabled="!duaPdfUrl"
        />
        <label for="dua-acknowledgment" class="text-sm">
          I acknowledge the usage terms and take legal responsibility for any misconduct.
        </label>
      </div>
      <Button
        class="mt-5"
        icon="pi pi-envelope"
        severity="bg-primary-500"
        label="Send"
        @click="sendReequest()"
        :loading="sendButtonLoading"
        :disabled="sendButtonLoading || (hasDua && !duaAcknowledged)"
      />
    </div>
  </div>
  <div v-if="!isCollectionOwner && hasDeclinedRequests()" class="mt-10 bg-orange-200 rounded-lg p-4 flex items-center">
    <i class="pi pi-exclamation-circle text-orange-400 mr-2"></i>
    <b>Your previous access was declined</b>
  </div>
</template>
