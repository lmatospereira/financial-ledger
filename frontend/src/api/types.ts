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
  name: string
  is_admin: boolean
  dashboard_hidden_widgets?: string[]
}

export type UserInput = {
  username: string
  name: string
  password: string
  is_admin: boolean
}

export type UserUpdateInput = {
  username: string
  name: string
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
  closing_day: number | null
  due_day: number | null
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
  // Set when transaction was generated from a recurring transaction rule.
  recurring_transaction_id?: number | null
  // Set when transaction is part of an installment purchase.
  installment_number?: number | null
  installment_total?: number | null
  // Transaction status: 'confirmed' or 'pending' (omitted defaults to 'confirmed')
  status?: 'confirmed' | 'pending'
}

export type TransactionInput = Omit<
  Transaction,
  'id' | 'category' | 'account' | 'to_account' | 'to_account_id' | 'type'
> & {
  // Transfers are never submitted through this shape — see POST /api/transfers.
  type: Exclude<TransactionType, 'transfer'>
  // Optional status: omit to default to 'confirmed' server-side
  status?: 'confirmed' | 'pending'
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

// ---------- Budget ----------
export interface Budget {
  id: number
  category_id: number
  amount: number
  created_at: string
}

export type BudgetInput = Omit<Budget, 'id' | 'created_at'>

export interface BudgetStatus {
  category_id: number
  category_name: string
  category_color: string
  budget_amount: number
  spent_amount: number
  percentage: number
  over_budget: boolean
}

// ---------- Recurring Transaction ----------
export interface RecurringTransaction {
  id: number
  account_id: number
  category_id: number | null
  description: string
  amount: number
  type: Exclude<TransactionType, 'transfer'>
  day_of_month: number // 1-31
  start_date: string // ISO date
  end_date: string | null // ISO date
  active: boolean
  created_at: string
}

export type RecurringTransactionInput = Omit<
  RecurringTransaction,
  'id' | 'active' | 'created_at'
>

export type RecurringTransactionUpdate = Omit<
  RecurringTransaction,
  'id' | 'created_at'
>

// ---------- Bill ----------
export interface Bill {
  id: number
  account_id: number | null
  category_id: number | null
  description: string
  amount: number
  due_date: string // ISO date
  paid: boolean
  paid_transaction_id: number | null
  created_at: string
}

export type BillInput = Omit<Bill, 'id' | 'paid' | 'paid_transaction_id' | 'created_at'>

export interface BillPayRequest {
  account_id: number
}

// ---------- Upcoming Alerts ----------
export interface UpcomingAlert {
  kind: 'bill' | 'recurring' | 'installment'
  id: number
  description: string
  amount: number
  due_date: string // ISO date
  is_overdue: boolean
  account: AccountRef | null
  category: Category | null
}

// ---------- Goals ----------
export interface Goal {
  id: number
  name: string
  target_amount: number
  target_date: string | null // ISO date
  color: string
  created_at: string
  account: AccountRef | null
  current_amount: number
  progress_percent: number
}

export type GoalInput = {
  name: string
  target_amount: number
  account_id: number
  target_date: string | null
  color: string
}

// ---------- Credit Card Invoice ----------
export interface CreditCardInvoice {
  period_start: string // ISO date
  period_end: string // ISO date
  due_date: string | null // ISO date
  total: number
  transactions: Transaction[]
}
