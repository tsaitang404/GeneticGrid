import { ref, reactive, computed } from 'vue'

export interface OKXAccount {
  id: number
  label: string
  api_key_masked: string
  note: string
  is_demo: boolean
  account_info: Record<string, any> | null
  last_used_at: string | null
  created_at: string
}

export interface SessionInfo {
  authenticated: boolean
  account_id?: number
  label?: string
  api_key_masked?: string
  trade_permission?: boolean
}

export interface BalanceInfo {
  totalEq: string
  totalPnl: string
  details: Array<{
    ccy: string
    eq: string
    eqUsd: string
    availBal: string
    frozenBal: string
  }>
}

const accounts = ref<OKXAccount[]>([])
const session = ref<SessionInfo | null>(null)
const balance = ref<BalanceInfo | null>(null)
const positions = ref<any[]>([])
const loading = reactive({
  accounts: false,
  session: false,
  balance: false,
  positions: false,
  login: false,
  register: false,
})
const error = ref('')

export function useAuth() {
  const isLoggedIn = computed(() => session.value?.authenticated === true)
  const activeLabel = computed(() => session.value?.label ?? '')

  async function checkSession(): Promise<void> {
    loading.session = true
    try {
      const resp = await fetch('/api/account/session/')
      const result = await resp.json()
      if (result.code === 0) {
        session.value = result.data
      }
    } catch { /* ignore */ } finally {
      loading.session = false
    }
  }

  async function fetchAccounts(): Promise<void> {
    loading.accounts = true
    error.value = ''
    try {
      const resp = await fetch('/api/account/list/')
      const result = await resp.json()
      if (result.code === 0) {
        accounts.value = result.data
      } else {
        error.value = result.error || '获取账户列表失败'
      }
    } catch (e: any) {
      error.value = e.message || '网络错误'
    } finally {
      loading.accounts = false
    }
  }

  async function register(
    label: string,
    api_key: string,
    secret_key: string,
    passphrase: string,
    note: string,
    is_demo: boolean = false,
  ): Promise<boolean> {
    loading.register = true
    error.value = ''
    try {
      const resp = await fetch('/api/account/register/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ label, api_key, secret_key, passphrase, note, is_demo }),
      })
      const result = await resp.json()
      if (result.code === 0) {
        await fetchAccounts()
        return true
      } else {
        error.value = result.error || '注册失败'
        return false
      }
    } catch (e: any) {
      error.value = e.message || '网络错误'
      return false
    } finally {
      loading.register = false
    }
  }

  async function login(account_id: number, passphrase: string): Promise<boolean> {
    loading.login = true
    error.value = ''
    try {
      const resp = await fetch('/api/account/login/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ account_id, passphrase }),
      })
      const result = await resp.json()
      if (result.code === 0) {
        session.value = {
          authenticated: true,
          account_id: result.data.id,
          label: result.data.label,
          api_key_masked: result.data.api_key_masked,
          trade_permission: result.data.trade_permission ?? false,
        }
        return true
      } else {
        error.value = result.error || '登陆失败'
        return false
      }
    } catch (e: any) {
      error.value = e.message || '网络错误'
      return false
    } finally {
      loading.login = false
    }
  }

  async function logout(): Promise<void> {
    try {
      await fetch('/api/account/logout/', { method: 'POST' })
    } catch { /* ignore */ }
    session.value = null
    balance.value = null
    positions.value = []
  }

  async function deleteAccount(account_id: number): Promise<boolean> {
    error.value = ''
    try {
      const resp = await fetch(`/api/account/${account_id}/`, { method: 'DELETE' })
      const result = await resp.json()
      if (result.code === 0) {
        if (session.value?.account_id === account_id) {
          session.value = null
          balance.value = null
          positions.value = []
        }
        await fetchAccounts()
        return true
      } else {
        error.value = result.error || '删除失败'
        return false
      }
    } catch (e: any) {
      error.value = e.message || '网络错误'
      return false
    }
  }

  async function fetchBalance(): Promise<void> {
    if (!isLoggedIn.value) return
    loading.balance = true
    error.value = ''
    try {
      const resp = await fetch('/api/account/balance/')
      const result = await resp.json()
      if (result.code === 0) {
        balance.value = result.data
      } else {
        if (result.error?.includes('未登录')) {
          session.value = null
        }
        error.value = result.error || '获取余额失败'
      }
    } catch (e: any) {
      error.value = e.message || '网络错误'
    } finally {
      loading.balance = false
    }
  }

  async function fetchPositions(): Promise<void> {
    if (!isLoggedIn.value) return
    loading.positions = true
    error.value = ''
    try {
      const resp = await fetch('/api/account/positions/')
      const result = await resp.json()
      if (result.code === 0) {
        positions.value = result.data.positions || []
      } else {
        if (result.error?.includes('未登录')) {
          session.value = null
        }
        error.value = result.error || '获取持仓失败'
      }
    } catch (e: any) {
      error.value = e.message || '网络错误'
    } finally {
      loading.positions = false
    }
  }

  function clearError(): void {
    error.value = ''
  }

  return {
    accounts,
    session,
    balance,
    positions,
    loading,
    error,
    isLoggedIn,
    activeLabel,
    checkSession,
    fetchAccounts,
    register,
    login,
    logout,
    deleteAccount,
    fetchBalance,
    fetchPositions,
    clearError,
  }
}
