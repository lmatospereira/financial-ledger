// Types mirroring the backend API contract (see .claude/agents/frontend-dev.md
// and .claude/agents/backend-dev.md for the shared source of truth).

export type TransactionType = 'income' | 'expense'

export interface LoginRequest {
  username: string
  password: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
}

export interface Category {
  id: number
  name: string
  color: string
  type: TransactionType
}

export type CategoryInput = Omit<Category, 'id'>

export interface Transaction {
  id: number
  description: string
  amount: number
  type: TransactionType
  date: string // ISO date string, e.g. "2026-07-21"
  // Kept nullable on purpose: TransactionForm exposes a "Sem categoria" option
  // that submits category_id: null (see TransactionForm.tsx / Dashboard.tsx
  // uncategorized filter), even though the backend column is nullable=False —
  // flagged for the orchestrator to reconcile with backend-dev rather than
  // silently dropping the feature here.
  category_id: number | null
  category?: Category | null
}

export type TransactionInput = Omit<Transaction, 'id' | 'category'>

export interface Summary {
  income_total: number
  expense_total: number
  balance: number
  previous_balance: number
}

// FastAPI validation errors (422) send `detail` as an array of these objects
// instead of a plain string.
export interface ApiValidationErrorItem {
  type: string
  loc: (string | number)[]
  msg: string
  input?: unknown
}

export interface ApiError {
  detail: string | ApiValidationErrorItem[]
}
