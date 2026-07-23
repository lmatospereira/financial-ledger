import AccountBalanceIcon from '@mui/icons-material/AccountBalance'
import CreditCardIcon from '@mui/icons-material/CreditCard'
import PaidIcon from '@mui/icons-material/Paid'
import SavingsIcon from '@mui/icons-material/Savings'
import WalletIcon from '@mui/icons-material/Wallet'
import type { AccountType } from '../api/types'

export const ACCOUNT_TYPE_LABELS: Record<AccountType, string> = {
  checking: 'Conta corrente',
  savings: 'Poupança',
  wallet: 'Carteira',
  credit_card: 'Cartão de crédito',
  other: 'Outra',
}

export const ACCOUNT_TYPE_ICONS: Record<AccountType, typeof AccountBalanceIcon> = {
  checking: AccountBalanceIcon,
  savings: SavingsIcon,
  wallet: WalletIcon,
  credit_card: CreditCardIcon,
  other: PaidIcon,
}

export const ACCOUNT_TYPE_OPTIONS: { value: AccountType; label: string }[] = (
  Object.keys(ACCOUNT_TYPE_LABELS) as AccountType[]
).map((value) => ({ value, label: ACCOUNT_TYPE_LABELS[value] }))
