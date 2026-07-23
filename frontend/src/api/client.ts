import axios, { AxiosError } from 'axios'
import type {
  ApiError,
  Category,
  CategoryInput,
  LoginRequest,
  LoginResponse,
  Summary,
  Transaction,
  TransactionInput,
} from './types'

const TOKEN_KEY = 'livro_caixa_token'

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}

// Base URL is intentionally relative (`/api`) — never hardcode the backend
// host. In dev, vite.config.ts proxies `/api` to http://localhost:8000; in
// production the app is served behind the same origin as the API.
const api = axios.create({
  baseURL: '/api',
})

api.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      clearToken()
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  },
)

export async function login(payload: LoginRequest): Promise<LoginResponse> {
  const { data } = await api.post<LoginResponse>('/auth/login', payload)
  return data
}

export async function getTransactions(
  month: number,
  year: number,
): Promise<Transaction[]> {
  const { data } = await api.get<Transaction[]>('/transactions', {
    params: { month, year },
  })
  return data
}

export async function createTransaction(
  payload: TransactionInput,
): Promise<Transaction> {
  const { data } = await api.post<Transaction>('/transactions', payload)
  return data
}

export async function updateTransaction(
  id: number,
  payload: TransactionInput,
): Promise<Transaction> {
  const { data } = await api.put<Transaction>(`/transactions/${id}`, payload)
  return data
}

export async function deleteTransaction(id: number): Promise<void> {
  await api.delete(`/transactions/${id}`)
}

export async function getCategories(): Promise<Category[]> {
  const { data } = await api.get<Category[]>('/categories')
  return data
}

export async function createCategory(
  payload: CategoryInput,
): Promise<Category> {
  const { data } = await api.post<Category>('/categories', payload)
  return data
}

export async function updateCategory(
  id: number,
  payload: CategoryInput,
): Promise<Category> {
  const { data } = await api.put<Category>(`/categories/${id}`, payload)
  return data
}

export async function deleteCategory(id: number): Promise<void> {
  await api.delete(`/categories/${id}`)
}

export async function getSummary(
  month: number,
  year: number,
): Promise<Summary> {
  const { data } = await api.get<Summary>('/summary', {
    params: { month, year },
  })
  return data
}

export async function getHealth(): Promise<{ status: string }> {
  const { data } = await api.get<{ status: string }>('/health')
  return data
}

export function getApiErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = (error.response?.data as ApiError | undefined)?.detail
    // The backend is expected to normalize 422s to a plain string, but don't
    // assume that always lands cleanly: FastAPI's default validation-error
    // shape is an array of { type, loc, msg, input } objects, so handle both
    // to avoid ever rendering "[object Object]" or throwing while formatting.
    if (typeof detail === 'string' && detail) return detail
    if (Array.isArray(detail) && detail.length > 0) {
      const message = detail
        .map((item) => item?.msg)
        .filter((msg): msg is string => Boolean(msg))
        .join('; ')
      if (message) return message
    }
    if (error.message) return error.message
  }
  return 'Ocorreu um erro inesperado. Tente novamente.'
}

export default api
