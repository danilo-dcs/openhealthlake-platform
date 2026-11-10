import type { HttpMethod } from '@/shared/interfaces/types'
import { unauthorizedRequestHandler } from './unauthorizedRequestHandler'
import { useUserStore } from '@/stores/userStore'
import router from '@/router'

export async function apiRequestHandler<T>(
  endpoint: string,
  method: HttpMethod = 'GET',
  body?: any,
  headers?: any,
  responseType: 'json' | 'blob' = 'json',
): Promise<T> {

const lakehouseApiUrl = import.meta.env.DEV
  ? '/api/lakehouse'
  : import.meta.env.VITE_APP_MAIN_LAKEHOUSE_API_URL

  const finalUrl = `${lakehouseApiUrl}${endpoint}`

  const userStore = useUserStore()

  const redirectToLogin = async () => {
    if (router.currentRoute.value.name !== 'login') {
      await router.replace({ name: 'login' })
    }
  }

  const finalHeaders: Record<string, string> = {
    ...(headers || {}),
    ...(userStore.accessToken ? { Authorization: `Bearer ${userStore.accessToken}` } : {}),
  }

  const isFormData = typeof FormData !== 'undefined' && body instanceof FormData

  if (['POST', 'PUT', 'PATCH'].includes(method) && !isFormData) {
    finalHeaders['Content-Type'] = 'application/json'
  }

  // The browser must set the multipart boundary for FormData requests.
  const requestBody = body == null ? undefined : isFormData ? body : JSON.stringify(body)

  try {
    let response = await fetch(finalUrl, {
      method,
      headers: finalHeaders,
      body: requestBody,
      credentials: 'include',
    })

    if (response.status === 401) {
      const refreshed = await unauthorizedRequestHandler(lakehouseApiUrl)

      if (refreshed) {
        // Retry request with the new token
        const retryHeaders = {
          ...finalHeaders,
          Authorization: `Bearer ${userStore.accessToken}`,
        }

        response = await fetch(finalUrl, {
          method,
          headers: retryHeaders,
          body: requestBody,
          credentials: 'include',
        })

        if (response.status === 401) {
          userStore.clearUser()
          await redirectToLogin()
        }

      } else {
        await redirectToLogin()
      }
    }

    if (!response.ok) {
      const errorText = await response.text()
      throw new Error(
        `API request failed: ${response.status} ${response.statusText} — ${errorText}`,
      )
    }

    if (response.status === 204) {
      return {} as T
    }

    const data: T = responseType === 'blob' ? ((await response.blob()) as T) : await response.json()
    return data
  } catch (error) {
    console.error('Fetch error:', error)
    throw error
  }
}
