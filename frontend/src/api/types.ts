// Types mirroring the backend API contract (see .claude/agents/frontend-dev.md
// and .claude/agents/backend-dev.md for the shared source of truth).

export type TransactionType = 'income' | 'expense' | 'transfer'

export interface LoginRequest {
  username: string
  password: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
}

export interface CurrentUser {
  id: number
  username: string
  is_admin: boolean
}

export type UserInput = {
  username: string
  password: string
  is_admin: boolean
}

export type UserUpdateInput = {
  username: string
  is_admin: boolean
}

export interface ChangePasswordRequest {
  current_password: string
  new_password: string
}

export type AccountType = 'checking' | 'savings' | 'wallet' | 'credit_card' | 'other'

export interface Account {
  id: number
  name: string
  type: AccountType
  color: string
  created_at: string
  balance: number
}

export type AccountInput = Omit<Account, 'id' | 'created_at' | 'balance'>

// Lightweight embed used for Transaction.account/to_account — the backend
// deliberately omits `balance`/`created_at` here (they're not recomputed
// per-transaction-row), so don't widen this to the full Account type.
export type AccountRef = Pick<Account, 'id' | 'name' | 'type' | 'color'>

export interface Category {
  id: number
  name: string
  color: string
  // Categories are only ever income/expense — transfers are never
  // categorized (see TransactionType, which is broader because it also
  // covers Transaction.type).
  type: Exclude<TransactionType, 'transfer'>
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
  account_id: number
  account?: AccountRef | null
  // Populated on `type: 'transfer'` rows returned by POST /api/transfers.
  // Nullable/omitted for income & expense rows.
  to_account_id?: number | null
  to_account?: AccountRef | null
}

export type TransactionInput = Omit<
  Transaction,
  'id' | 'category' | 'account' | 'to_account' | 'to_account_id' | 'type'
> & {
  // Transfers are never submitted through this shape — see POST /api/transfers.
  type: Exclude<TransactionType, 'transfer'>
}

export interface TransferInput {
  from_account_id: number
  to_account_id: number
  amount: number
  date: string
  description: string
}

export interface Summary {
  income_total: number
  expense_total: number
  balance: number
  previous_balance: number
}

export interface MonthlyTrendEntry {
  month: number // 1-12
  income_total: number
  expense_total: number
}

export interface CategoryBreakdownEntry {
  category_id: number | null
  name: string
  color: string
  total: number
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
