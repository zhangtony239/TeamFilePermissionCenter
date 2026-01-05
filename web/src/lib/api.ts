import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://127.0.0.1:8000/api/v1'

export const api = axios.create({
  baseURL: API_BASE
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('tfpc_token')
  if (token) {
    config.headers = config.headers ?? {}
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export type ApiOk<T> = { ok: true; data: T }
export type ApiErr = { ok: false; error: { code: string; message: string; details?: unknown } }
