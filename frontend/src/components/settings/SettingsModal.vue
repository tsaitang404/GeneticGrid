<template>
  <div class="settings-modal-overlay" @click.self="handleOverlayClick" @keydown.esc="handleEscKey">
    <div class="settings-modal" :class="{ 'closing': isClosing }">
      <div class="modal-header">
        <h2>偏好设置</h2>
        <button @click="handleCloseClick" class="close-btn">✕</button>
      </div>
      
      <div class="modal-body">
        <div class="setting-group">
          <label class="setting-label">涨跌颜色</label>
          <div class="color-scheme-options">
            <label class="radio-label">
              <input 
                type="radio" 
                name="color-scheme" 
                value="green-up" 
                v-model="localColorScheme"
              >
              <span class="radio-text">
                <span class="color-preview" style="background:#26a69a"></span>
                绿涨
                <span class="color-preview" style="background:#ef5350; margin-left:4px"></span>
                红跌
              </span>
            </label>
            <label class="radio-label">
              <input 
                type="radio" 
                name="color-scheme" 
                value="red-up" 
                v-model="localColorScheme"
              >
              <span class="radio-text">
                <span class="color-preview" style="background:#ef5350"></span>
                红涨
                <span class="color-preview" style="background:#26a69a; margin-left:4px"></span>
                绿跌
              </span>
            </label>
          </div>
        </div>
        
        <div class="setting-group">
          <label class="setting-label">计价货币</label>
          <select v-model="localCurrency" class="currency-select">
            <option value="USDT">USDT</option>
            <option value="USDC">USDC</option>
            <option value="USD">USD (美元)</option>
            <option value="CNY">CNY (人民币)</option>
            <option value="EUR">EUR (欧元)</option>
            <option value="GBP">GBP (英镑)</option>
            <option value="JPY">JPY (日元)</option>
            <option value="KRW">KRW (韩元)</option>
            <option value="HKD">HKD (港币)</option>
            <option value="AUD">AUD (澳元)</option>
            <option value="CAD">CAD (加元)</option>
            <option value="CHF">CHF (瑞郎)</option>
            <option value="SGD">SGD (新币)</option>
            <option value="INR">INR (卢比)</option>
            <option value="RUB">RUB (卢布)</option>
          </select>
        </div>

        <div class="setting-group">
          <label class="setting-label">代理配置</label>

          <label class="checkbox-label" style="margin-bottom: 14px">
            <input type="checkbox" v-model="localEnabled" />
            <span>启用代理</span>
          </label>

          <template v-if="localEnabled">
            <div class="field" style="margin-bottom: 12px">
              <span>代理地址</span>
              <div class="proxy-input-row">
                <input v-model="localProxyUrl" class="text-input" placeholder="socks5://127.0.0.1:1080 或 http://127.0.0.1:8080" />
                <button class="btn ghost" :disabled="proxyTesting || proxySaving" @click="testProxy">测试代理</button>
              </div>
            </div>

            <label class="checkbox-label" style="margin-bottom: 4px">
              <input type="checkbox" v-model="localContainerAutoHost" />
              <span>容器中自动将 <code>127.0.0.1</code> 映射为宿主机（host.docker.internal）</span>
            </label>
          </template>

          <p v-if="proxyMessage" :class="['proxy-message', proxyMessageType]">{{ proxyMessage }}</p>
        </div>
      </div>

      <div class="modal-footer">
        <button class="btn ghost" :disabled="isSaving" @click="handleCloseClick">取消</button>
        <button class="btn primary" :disabled="isSaving" @click="handleSaveAll">保存</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import {
  usePreferencesStore,
  type ColorScheme,
} from '@/stores/preferences'

const emit = defineEmits<{
  close: []
  'update:colorScheme': [scheme: string]
  'update:currency': [currency: string]
}>()

const preferences = usePreferencesStore()
const { colorScheme, currency, proxySettings } = storeToRefs(preferences)
const proxyMessage = ref<string>('')
const proxyMessageType = ref<'ok' | 'error'>('ok')
const proxySaving = ref<boolean>(false)
const proxyTesting = ref<boolean>(false)
const isClosing = ref<boolean>(false)
const isSaving = ref<boolean>(false)

// 本地表单状态（颜色、货币、代理都需要保存时才生效）
const localColorScheme = ref<ColorScheme>('green-up')
const localCurrency = ref<string>('USDT')
const localEnabled = ref<boolean>(true)
const localProxyUrl = ref<string>('socks5://127.0.0.1:1080')
const localContainerAutoHost = ref<boolean>(true)

// 初始状态快照（用于检测是否有未保存改动）
const initialState = ref<{
  colorScheme: string
  currency: string
  enabled: boolean
  proxyUrl: string
  containerAutoHost: boolean
}>({
  colorScheme: 'green-up',
  currency: 'USDT',
  enabled: true,
  proxyUrl: 'socks5://127.0.0.1:1080',
  containerAutoHost: true,
})

// 检测是否有未保存改动
const hasUnsavedChanges = computed(() => {
  return (
    localColorScheme.value !== initialState.value.colorScheme ||
    localCurrency.value !== initialState.value.currency ||
    localEnabled.value !== initialState.value.enabled ||
    localProxyUrl.value !== initialState.value.proxyUrl ||
    localContainerAutoHost.value !== initialState.value.containerAutoHost
  )
})

function initializeSettings(): void {
  // 从 store 读取当前保存的设置
  localColorScheme.value = colorScheme.value
  localCurrency.value = currency.value
  localEnabled.value = proxySettings.value.enabled
  localProxyUrl.value = proxySettings.value.proxyUrl
  localContainerAutoHost.value = proxySettings.value.containerAutoHost
  
  // 保存初始状态快照
  initialState.value = {
    colorScheme: colorScheme.value,
    currency: currency.value,
    enabled: proxySettings.value.enabled,
    proxyUrl: proxySettings.value.proxyUrl,
    containerAutoHost: proxySettings.value.containerAutoHost,
  }
}

// 关闭抽屉前的检查
function shouldClose(): boolean {
  if (!hasUnsavedChanges.value) {
    return true
  }
  
  // 有未保存改动，提示用户
  const confirmed = window.confirm('您有未保存的改动，确定要放弃吗？')
  return confirmed
}

async function performClose(): Promise<void> {
  isClosing.value = true
  // 等待反向滑出动画完成（220ms）
  await new Promise(resolve => setTimeout(resolve, 220))
  emit('close')
}

function handleCloseClick(): void {
  if (shouldClose()) {
    performClose()
  }
}

function handleOverlayClick(): void {
  if (shouldClose()) {
    performClose()
  }
}

function handleEscKey(): void {
  if (shouldClose()) {
    performClose()
  }
}

const testProxy = async (): Promise<void> => {
  const url = localProxyUrl.value.trim()
  if (!url.startsWith('http://') && !url.startsWith('socks5://')) {
    proxyMessageType.value = 'error'
    proxyMessage.value = '代理地址需以 http:// 或 socks5:// 开头'
    return
  }

  proxyTesting.value = true
  proxyMessage.value = ''
  try {
    const response = await fetch('/api/proxy-test/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ proxy_url: url })
    })
    const payload = await response.json()
    if (payload.code === 0) {
      const d = payload.data
      const typeLabel = String(d.type || '').toLowerCase() === 'socks5' ? 'SOCKS5' : 'HTTP'
      const available = Boolean(d.available)
      const latencyMs = Number.isFinite(Number(d.latency_ms)) ? Number(d.latency_ms) : null
      proxyMessageType.value = available ? 'ok' : 'error'
      proxyMessage.value = `${typeLabel} ${available ? '✓' : '✗'} (${d.effective_host}:${d.port}${latencyMs !== null ? `, ${latencyMs}ms` : ''})`
    } else {
      proxyMessageType.value = 'error'
      proxyMessage.value = payload.error || '测试失败'
    }
  } catch {
    proxyMessageType.value = 'error'
    proxyMessage.value = '请求失败'
  } finally {
    proxyTesting.value = false
  }
}

const handleSaveAll = async (): Promise<void> => {
  // 验证代理地址格式
  const url = localProxyUrl.value.trim()
  if (localEnabled.value && !url.startsWith('http://') && !url.startsWith('socks5://')) {
    proxyMessageType.value = 'error'
    proxyMessage.value = '代理地址需以 http:// 或 socks5:// 开头'
    return
  }

  isSaving.value = true
  
  // 更新初始状态快照（表示数据已"提交"）
  initialState.value = {
    colorScheme: localColorScheme.value,
    currency: localCurrency.value,
    enabled: localEnabled.value,
    proxyUrl: url,
    containerAutoHost: localContainerAutoHost.value,
  }
  
  // 立即关闭抽屉（不等待保存完成）
  performClose()
  
  // 在后台异步执行保存
  setTimeout(async () => {
    try {
      // 保存颜色方案
      preferences.setColorScheme(localColorScheme.value as ColorScheme)
      
      // 保存货币
      preferences.setCurrency(localCurrency.value)
      
      // 保存代理配置
      const proxySettings = {
        enabled: localEnabled.value,
        proxyUrl: url,
        containerAutoHost: localContainerAutoHost.value
      }
      await preferences.saveProxySettings(proxySettings)
    } catch (error: unknown) {
      console.error('保存设置失败:', error)
    } finally {
      isSaving.value = false
    }
  }, 0)
}

onMounted(async () => {
  await preferences.loadProxySettings()
  initializeSettings()
})

</script>

<style scoped>
.settings-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.48);
  display: flex;
  align-items: stretch;
  justify-content: flex-end;
  z-index: 2000;
}

.settings-modal {
  background: var(--bg-secondary);
  border-left: 1px solid var(--border-color);
  width: min(520px, 100vw);
  height: 100vh;
  overflow: hidden;
  box-shadow: -12px 0 40px rgba(0, 0, 0, 0.35);
  animation: drawer-in 0.22s ease-out;
  display: flex;
  flex-direction: column;
}

.settings-modal.closing {
  animation: drawer-out 0.22s ease-out forwards;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color);
  flex-shrink: 0;
}

.modal-header h2 {
  margin: 0;
  color: var(--text-primary);
  font-size: 18px;
}

.close-btn {
  background: transparent;
  border: none;
  color: var(--text-primary);
  font-size: 20px;
  cursor: pointer;
  padding: 4px 8px;
}

.close-btn:hover {
  background: var(--border-color);
  border-radius: 4px;
}

.modal-body {
  padding: 20px;
  overflow: auto;
  flex: 1;
}

.modal-footer {
  display: flex;
  gap: 10px;
  padding: 16px 20px;
  border-top: 1px solid var(--border-color);
  flex-shrink: 0;
  justify-content: flex-end;
}

.setting-group {
  margin-bottom: 24px;
}

.setting-group:last-child {
  margin-bottom: 0;
}

.setting-label {
  display: block;
  margin-bottom: 12px;
  color: var(--text-primary);
  font-weight: 500;
  font-size: 14px;
}

.color-scheme-options {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.radio-label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 10px 12px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  transition: all 0.2s;
}

.radio-label:hover {
  background: #1e222d;
  border-color: #363a45;
}

.radio-label input[type="radio"] {
  cursor: pointer;
}

.radio-text {
  display: flex;
  align-items: center;
  gap: 4px;
  color: var(--text-primary);
  font-size: 14px;
}

.color-preview {
  display: inline-block;
  width: 16px;
  height: 16px;
  border-radius: 3px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.currency-select {
  width: 100%;
  background: var(--bg-primary);
  color: var(--text-primary);
  border: 1px solid var(--border-color);
  padding: 10px 12px;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.currency-select:hover {
  border-color: #363a45;
}

.currency-select:focus {
  outline: none;
  border-color: #2962ff;
}

.currency-select option {
  background: var(--bg-secondary);
  color: var(--text-primary);
}

.proxy-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.full-row {
  grid-column: 1 / -1;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-primary);
  font-size: 14px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  color: var(--text-secondary);
  font-size: 13px;
}

.text-input {
  width: 100%;
  background: var(--bg-primary);
  color: var(--text-primary);
  border: 1px solid var(--border-color);
  padding: 8px 10px;
  border-radius: 6px;
  font-size: 14px;
}

.text-input:focus {
  outline: none;
  border-color: #2962ff;
}

.proxy-input-row {
  display: flex;
  gap: 8px;
}

.proxy-input-row .text-input {
  flex: 1;
}

.btn {
  border: 1px solid var(--border-color);
  border-radius: 6px;
  padding: 8px 12px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn.ghost {
  background: transparent;
  color: var(--text-primary);
}

.btn.primary {
  background: #2962ff;
  border-color: #2962ff;
  color: #fff;
}

.proxy-message {
  margin-top: 10px;
  margin-bottom: 0;
  font-size: 13px;
}

.proxy-message.ok {
  color: #26a69a;
}

.proxy-message.error {
  color: #ef5350;
}

@media (max-width: 640px) {
  .settings-modal {
    width: 100vw;
    border-left: none;
    box-shadow: none;
  }
}

@keyframes drawer-in {
  from {
    transform: translateX(28px);
    opacity: 0.6;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

@keyframes drawer-out {
  from {
    transform: translateX(0);
    opacity: 1;
  }
  to {
    transform: translateX(28px);
    opacity: 0.6;
  }
}
</style>
