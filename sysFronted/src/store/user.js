import { ref } from 'vue'
import { defineStore } from 'pinia'

function readUserInfo() {
  try {
    return JSON.parse(localStorage.getItem('user_info') || 'null')
  } catch {
    return null
  }
}

export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem('auth_token') || '')
  const userInfo = ref(readUserInfo())

  function login({ token: authToken, user_profile: profile }) {
    token.value = authToken
    userInfo.value = profile
    localStorage.setItem('auth_token', authToken)
    localStorage.setItem('user_info', JSON.stringify(profile))
  }

  function updateUserInfo(profile) {
    userInfo.value = { ...userInfo.value, ...profile }
    localStorage.setItem('user_info', JSON.stringify(userInfo.value))
  }

  function logout() {
    token.value = ''
    userInfo.value = null
    localStorage.removeItem('auth_token')
    localStorage.removeItem('user_info')
  }

  function getAvatarUrl(avatar) {
    if (!avatar) return ''
    if (/^https?:\/\//i.test(avatar)) return avatar

    const apiBase = import.meta.env.VITE_API_BASE_URL || '/api'
    const apiOrigin = new URL(apiBase, window.location.origin).origin
    return new URL(avatar.startsWith('/') ? avatar : `/${avatar}`, apiOrigin).toString()
  }

  function getUserAvatar() {
    return getAvatarUrl(userInfo.value?.avatar)
  }

  return {
    token,
    userInfo,
    login,
    updateUserInfo,
    logout,
    getAvatarUrl,
    getUserAvatar,
  }
})
