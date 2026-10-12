import { useUserStore } from '@/stores/userStore'
import type { LoginResponse } from '../interfaces/http/LoginResponse'

export const unauthorizedRequestHandler = async (apiBaseUrl: string): Promise<boolean> => {
  const userStore = useUserStore()

  const response = await fetch(`${apiBaseUrl}/auth/refresh`, {
    method: 'POST',
    credentials: 'include',
  })

  if (response.status === 401) {
    userStore.clearUser()
    return false
  }

  if (!response.ok) {
    userStore.clearUser()
    return false
  }

  const data = (await response.json()) as LoginResponse

  userStore.setUser({
    email: data.user_email,
    role: data.user_role,
    userId: data.user_id,
    accessToken: data.access_token,
    tokenType: data.token_type,
  })

  return true
}
