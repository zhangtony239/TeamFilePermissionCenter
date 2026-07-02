import axios, { type AxiosError, type AxiosRequestConfig, type InternalAxiosRequestConfig } from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://127.0.0.1:8000/api/v1'

export const api = axios.create({
  baseURL: API_BASE
})

// 标记是否正在刷新 token，避免并发请求重复刷新
let isRefreshing = false
// 等待 token 刷新完成的请求队列
let refreshQueue: Array<(token: string) => void> = []

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('tfpc_token')
  if (token) {
    config.headers = config.headers ?? {}
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截器：access token 过期（401）时自动用 refresh token 换新，并重发原请求
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retried?: boolean }
    const status = error.response?.status

    // 非 401、或已是重试请求、或无 refresh token：直接失败
    if (status !== 401 || originalRequest._retried || !localStorage.getItem('tfpc_refresh')) {
      return Promise.reject(error)
    }

    // 登录/刷新接口本身 401：不处理，交给调用方
    if (originalRequest.url?.includes('/auth/login/') || originalRequest.url?.includes('/auth/refresh/')) {
      return Promise.reject(error)
    }

    // 已有刷新在进行中：排队等待新 token
    if (isRefreshing) {
      return new Promise((resolve) => {
        refreshQueue.push((token: string) => {
          originalRequest.headers = originalRequest.headers ?? {}
          originalRequest.headers.Authorization = `Bearer ${token}`
          originalRequest._retried = true
          resolve(api(originalRequest))
        })
      })
    }

    isRefreshing = true
    try {
      const refreshToken = localStorage.getItem('tfpc_refresh')
      const resp = await axios.post(`${API_BASE}/auth/refresh/`, { refresh: refreshToken })
      const newAccess: string = resp.data?.access
      if (!newAccess) throw new Error('no access in refresh response')
      localStorage.setItem('tfpc_token', newAccess)
      // 部分返回可能含新 refresh，有则更新
      if (resp.data?.refresh) {
        localStorage.setItem('tfpc_refresh', resp.data.refresh)
      }

      // 唤醒队列中的请求
      refreshQueue.forEach((cb) => cb(newAccess))
      refreshQueue = []

      // 重发当前请求
      originalRequest.headers = originalRequest.headers ?? {}
      originalRequest.headers.Authorization = `Bearer ${newAccess}`
      originalRequest._retried = true
      return api(originalRequest)
    } catch (refreshError) {
      // 刷新失败：清空 token，跳转登录
      refreshQueue = []
      localStorage.removeItem('tfpc_token')
      localStorage.removeItem('tfpc_refresh')
      // 避免硬编码路由，触发路由守卫自然跳转
      if (location.pathname !== '/login') {
        location.href = '/login'
      }
      return Promise.reject(refreshError)
    } finally {
      isRefreshing = false
    }
  }
)

export type ApiOk<T> = { ok: true; data: T }
export type ApiErr = { ok: false; error: { code: string; message: string; details?: unknown } }
