import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useUserStore = defineStore('user', () => {
  const email = ref<string | null>(null)
  const role = ref<string | null>(null)
  const userId = ref<string | null>(null)
  const accessToken = ref<string | null>(null)
  const tokenType = ref<string | null>(null)

  const setUser = (data: {
    email: string
    role: string
    userId: string
    accessToken: string
    tokenType: string
  }) => {
    email.value = data.email
    role.value = data.role
    userId.value = data.userId
    accessToken.value = data.accessToken
    tokenType.value = data.tokenType
  }

  const setEmail = (value: string) => {
    email.value = value
  }

  const setAccessToken = (token: string) => {
    accessToken.value = token
  }

  const clearUser = () => {
    email.value = ''
    role.value = ''
    userId.value = ''
    accessToken.value = null
    tokenType.value = ''
  }

  // --- Getters ---
  const isAuthenticated = () => !!accessToken.value

  return {
    email,
    role,
    userId,
    accessToken,
    tokenType,
    setUser,
    setEmail,
    setAccessToken,
    clearUser,
    isAuthenticated,
  }
})
