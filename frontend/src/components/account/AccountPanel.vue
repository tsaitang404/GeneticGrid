<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-content">
      <div class="modal-header">
        <h2>账户管理</h2>
        <button class="close-btn" @click="$emit('close')">✕</button>
      </div>

      <!-- 已登陆状态 -->
      <div v-if="isLoggedIn" class="section">
        <div class="login-badge">已登陆: {{ activeLabel }}</div>
        <div class="session-info">
          <span class="label">API Key</span>
          <span class="value">{{ session?.api_key_masked }}</span>
        </div>

        <div class="btn-row">
          <button class="btn primary" @click="refreshBalance" :disabled="loading.balance">
            {{ loading.balance ? '加载中...' : '刷新余额' }}
          </button>
          <button class="btn danger" @click="handleLogout">登出</button>
          <button class="btn danger-outline" @click="handleDeleteCurrent">删除此账户</button>
        </div>

        <!-- 余额 -->
        <div v-if="balance" class="balance-section">
          <h3>账户余额</h3>
          <div class="balance-total">
            总权益: <strong>{{ formatEq(balance.totalEq) }}</strong>
          </div>
          <div v-if="balance.totalPnl && balance.totalPnl !== '0'" class="balance-pnl">
            总盈亏: <strong :class="+balance.totalPnl >= 0 ? 'profit' : 'loss'">{{ balance.totalPnl }}</strong>
          </div>
          <div class="balance-list">
            <div v-for="d in balance.details" :key="d.ccy" class="balance-item">
              <span class="ccy">{{ d.ccy }}</span>
              <span class="eq">{{ formatEq(d.eq) }}</span>
              <span class="usd">≈ ${{ formatEq(d.eqUsd) }}</span>
              <span class="avail">可用: {{ formatEq(d.availBal) }}</span>
              <span v-if="+d.frozenBal > 0" class="frozen">冻结: {{ formatEq(d.frozenBal) }}</span>
            </div>
          </div>
        </div>

        <!-- 持仓 -->
        <div v-if="positions.length > 0" class="positions-section">
          <h3>持仓 ({{ positions.length }})</h3>
          <div v-for="pos in positions" :key="pos.symbol" class="pos-card">
            <div class="pos-header">
              <strong>{{ pos.symbol }}</strong>
              <span :class="['side', pos.side?.toLowerCase()]">{{ pos.side }}</span>
            </div>
            <div class="pos-detail">
              <span>数量: {{ pos.positionQty }}</span>
              <span>杠杆: {{ pos.leverage }}x</span>
              <span>标记价: ${{ formatEq(pos.markPrice) }}</span>
              <span :class="+pos.unrealizedPnl >= 0 ? 'profit' : 'loss'">
                未实现盈亏: {{ formatEq(pos.unrealizedPnl) }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- 未登陆状态 -->
      <div v-else class="section">
        <!-- 错误信息 -->
        <div v-if="error" class="error-msg">{{ error }}</div>

        <!-- 登陆表单 -->
        <div v-if="accounts.length > 0" class="login-form">
          <h3>选择账户登陆</h3>
          <div class="account-list">
            <div
              v-for="acc in accounts"
              :key="acc.id"
              :class="['account-card', { selected: selectedId === acc.id }]"
              @click="selectedId = acc.id"
            >
            <div class="acc-label">
              {{ acc.label }}
              <span v-if="acc.is_demo" class="demo-badge">模拟</span>
              <span v-else class="real-badge">实盘</span>
            </div>
            <div class="acc-key">{{ acc.api_key_masked }}</div>
            <div v-if="acc.note" class="acc-note">{{ acc.note }}</div>
            <div v-if="acc.account_info" class="acc-info">
              UID: {{ acc.account_info.uid }} | 等级: {{ acc.account_info.level }}
            </div>
            </div>
          </div>
          <input
            v-model="passphraseInput"
            type="password"
            placeholder="输入 Passphrase"
            class="input"
            @keyup.enter="handleLogin"
          >
          <button class="btn primary" :disabled="loading.login || !selectedId" @click="handleLogin">
            {{ loading.login ? '登陆中...' : '登陆' }}
          </button>
        </div>

        <!-- 注册新 Key -->
        <div class="register-form">
          <h3>{{ accounts.length > 0 ? '添加新的 API Key' : '注册 API Key' }}</h3>
          <input v-model="form.label" placeholder="标签 (如 '只读Key')" class="input">
          <input v-model="form.api_key" placeholder="API Key" class="input">
          <input v-model="form.secret_key" type="password" placeholder="Secret Key" class="input">
          <input v-model="form.passphrase" type="password" placeholder="Passphrase" class="input">
          <input v-model="form.note" placeholder="备注/权限说明" class="input">
          <label class="checkbox-label">
            <input v-model="form.is_demo" type="checkbox" class="checkbox">
            <span>模拟盘 (Demo)</span>
          </label>
          <button class="btn secondary" :disabled="loading.register" @click="handleRegister">
            {{ loading.register ? '验证中...' : '注册并验证' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useAuth } from '../../composables/useAuth'

const emit = defineEmits<{ (e: 'close'): void }>()

const {
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
  fetchBalance,
  fetchPositions,
} = useAuth()

const selectedId = ref<number | null>(null)
const passphraseInput = ref('')

const form = ref({
  label: '',
  api_key: '',
  secret_key: '',
  passphrase: '',
  note: '',
  is_demo: false,
})

onMounted(async () => {
  await checkSession()
  await fetchAccounts()
  if (isLoggedIn.value) {
    fetchBalance()
    fetchPositions()
  }
})

async function handleLogin(): Promise<void> {
  if (!selectedId.value || !passphraseInput.value) return
  const ok = await login(selectedId.value, passphraseInput.value)
  if (ok) {
    passphraseInput.value = ''
    fetchBalance()
    fetchPositions()
  }
}

async function handleRegister(): Promise<void> {
  const f = form.value
  if (!f.label || !f.api_key || !f.secret_key || !f.passphrase) return
  const ok = await register(f.label, f.api_key, f.secret_key, f.passphrase, f.note, f.is_demo)
  if (ok) {
    form.value = { label: '', api_key: '', secret_key: '', passphrase: '', note: '', is_demo: false }
  }
}

async function handleDeleteCurrent(): Promise<void> {
  if (!session.value) return
  const accId = session.value.account_id
  const acc = accounts.value.find((a: any) => a.id === accId)
  if (!acc) return
  if (!confirm(`确定删除当前登录的 API Key「${acc.label}」(${acc.api_key_masked})？\n此操作不可撤销。`)) return
  try {
    const resp = await fetch(`/api/account/${accId}/`, { method: 'DELETE' })
    const result = await resp.json()
    if (result.code === 0) {
      accounts.value = accounts.value.filter((a: any) => a.id !== accId)
      await logout()
      selectedId.value = null
      passphraseInput.value = ''
    } else {
      error.value = result.error || '删除失败'
    }
  } catch (e: any) {
    error.value = e.message || '网络错误'
  }
}

async function handleLogout(): Promise<void> {
  await logout()
  selectedId.value = null
  passphraseInput.value = ''
}

async function refreshBalance(): Promise<void> {
  await fetchBalance()
  await fetchPositions()
}

function formatEq(val: string | number): string {
  const n = typeof val === 'string' ? parseFloat(val) : val
  if (isNaN(n)) return '-'
  if (Math.abs(n) >= 1e6) return (n / 1e6).toFixed(2) + 'M'
  if (Math.abs(n) >= 1e3) return (n / 1e3).toFixed(2) + 'K'
  return n.toFixed(n > 0 && n < 1 ? 8 : 2)
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: #1e222d;
  border: 1px solid #2a2e39;
  border-radius: 12px;
  width: 520px;
  max-height: 80vh;
  overflow-y: auto;
  padding: 24px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.modal-header h2 {
  margin: 0;
  font-size: 18px;
  color: #d1d4dc;
}

.close-btn {
  background: none;
  border: none;
  color: #787b86;
  font-size: 20px;
  cursor: pointer;
}

.close-btn:hover { color: #d1d4dc; }

.section { display: flex; flex-direction: column; gap: 16px; }

.login-badge {
  background: rgba(41, 98, 255, 0.15);
  color: #2962ff;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
}

.session-info {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  color: #8b90a0;
}

.btn-row { display: flex; gap: 8px; }

.btn {
  height: 36px;
  padding: 0 16px;
  border-radius: 6px;
  border: 1px solid #2a2e39;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
  color: #d1d4dc;
  background: #202534;
}

.btn:hover { background: #23283a; border-color: #2f3b52; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn.primary { background: #2962ff; border-color: #2962ff; color: #fff; }
.btn.primary:hover { background: #1e53e5; }
.btn.danger { background: #d32f2f; border-color: #d32f2f; color: #fff; }
.btn.danger:hover { background: #b71c1c; }
.btn.danger-outline { background: transparent; border-color: #e53935; color: #e53935; }
.btn.danger-outline:hover { background: #e53935; color: #fff; }
.btn.secondary { background: transparent; }

.error-msg {
  background: rgba(244, 67, 54, 0.1);
  color: #f44336;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 13px;
}

.balance-section h3,
.positions-section h3 {
  margin: 0 0 8px;
  font-size: 14px;
  color: #d1d4dc;
}

.balance-total {
  font-size: 16px;
  color: #d1d4dc;
  margin-bottom: 4px;
}

.balance-pnl { font-size: 13px; margin-bottom: 8px; }

.balance-list { display: flex; flex-direction: column; gap: 6px; }

.balance-item {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  font-size: 13px;
  padding: 6px 8px;
  background: #161a23;
  border-radius: 4px;
  align-items: center;
}

.balance-item .ccy { font-weight: 600; color: #d1d4dc; min-width: 40px; }
.balance-item .eq { color: #d1d4dc; }
.balance-item .usd { color: #8b90a0; }
.balance-item .avail { color: #8b90a0; margin-left: auto; }
.balance-item .frozen { color: #ff9800; }

.profit { color: #4caf50; }
.loss { color: #f44336; }

.positions-section { margin-top: 8px; }

.pos-card {
  background: #161a23;
  border: 1px solid #2a2e39;
  border-radius: 6px;
  padding: 10px;
  margin-bottom: 8px;
}

.pos-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
  font-size: 13px;
}

.pos-header .side {
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 4px;
}

.side.long { background: rgba(76, 175, 80, 0.2); color: #4caf50; }
.side.short { background: rgba(244, 67, 54, 0.2); color: #f44336; }

.pos-detail {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  font-size: 12px;
  color: #8b90a0;
}

.login-form,
.register-form {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.login-form h3,
.register-form h3 {
  margin: 0;
  font-size: 14px;
  color: #d1d4dc;
}

.account-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 200px;
  overflow-y: auto;
}

.account-card {
  background: #161a23;
  border: 1px solid #2a2e39;
  border-radius: 6px;
  padding: 10px;
  cursor: pointer;
  transition: all 0.2s;
}

.account-card:hover { border-color: #3a3e49; }
.account-card.selected { border-color: #2962ff; background: rgba(41, 98, 255, 0.08); }

.acc-label { font-size: 14px; font-weight: 500; color: #d1d4dc; }
.acc-key { font-size: 12px; color: #8b90a0; }
.acc-note { font-size: 11px; color: #2962ff; margin-top: 2px; }
.acc-info { font-size: 11px; color: #787b86; margin-top: 2px; }

.account-card { position: relative; }
.btn-delete {
  position: absolute;
  top: 6px;
  right: 6px;
  font-size: 11px;
  padding: 2px 8px;
  border: 1px solid #e53935;
  border-radius: 4px;
  background: transparent;
  color: #e53935;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.2s;
}
.account-card:hover .btn-delete { opacity: 1; }
.btn-delete:hover { background: #e53935; color: #fff; }

.input {
  background: #1b202b;
  border: 1px solid #2a2e39;
  color: #d1d4dc;
  height: 38px;
  border-radius: 6px;
  padding: 0 10px;
  font-size: 13px;
  outline: none;
  transition: border-color 0.2s;
}

.input:focus { border-color: #2962ff; }

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #d1d4dc;
  cursor: pointer;
}

.checkbox {
  width: 16px;
  height: 16px;
  accent-color: #2962ff;
}

.demo-badge {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 4px;
  background: rgba(255, 152, 0, 0.2);
  color: #ff9800;
  margin-left: 6px;
}

.real-badge {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 4px;
  background: rgba(41, 98, 255, 0.2);
  color: #2962ff;
  margin-left: 6px;
}
</style>
