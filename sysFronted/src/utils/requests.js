import axios from 'axios'
import { useUserStore } from '@/store/user'

const service = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 20000,
})

service.interceptors.request.use((config) => {
  const token = useUserStore().token
  if (token) {
    config.headers.Authorization = `Token ${token}`
  }
  return config
})

service.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (error.response?.status === 401 && !error.config?.url?.includes('/users/login/')) {
      useUserStore().logout()
      const loginPath = `${import.meta.env.BASE_URL}admin/login`
      if (!window.location.pathname.endsWith('/admin/login')) {
        window.location.replace(`${loginPath}?reason=expired`)
      }
    }
    return Promise.reject(error)
  },
)

export function getApiErrorMessage(error, fallback = '请求失败，请稍后重试') {
  const responseData = error?.response?.data
  if (typeof responseData?.detail === 'string') return responseData.detail
  if (typeof responseData?.error === 'string') return responseData.error
  if (typeof responseData === 'string') return responseData
  return fallback
}

export default service
