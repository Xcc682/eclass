import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { userApi, type UserInfo } from '@/api/user'

export const useUserStore = defineStore('user', () => {
  const user = ref<UserInfo | null>(null)
  const token = ref<string>('')

  const isLoggedIn = computed(() => !!token.value)
  const isTeacher = computed(() => user.value?.role === 'teacher')

  async function fetchProfile() {
    const profile = await userApi.getProfile()
    user.value = profile
    return profile
  }

  async function login(params: { phone: string; password: string }) {
    const result = await userApi.login(params)
    token.value = result.token
    user.value = result.user
    uni.setStorageSync('token', result.token)
    return result
  }

  async function yibanLogin(params: { auth_code: string }) {
    const result = await userApi.yibanLogin(params)
    token.value = result.token
    user.value = result.user
    uni.setStorageSync('token', result.token)
    return result
  }

  function logout() {
    user.value = null
    token.value = ''
    uni.removeStorageSync('token')
    uni.navigateTo({ url: '/pages/login/login' })
  }

  function checkLogin(): boolean {
    const saved = uni.getStorageSync('token')
    if (saved) {
      token.value = saved
      return true
    }
    return false
  }

  return {
    user, token, isLoggedIn, isTeacher,
    fetchProfile, login, yibanLogin, logout, checkLogin
  }
})
