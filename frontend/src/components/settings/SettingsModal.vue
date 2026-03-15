<template>
  <div class="settings-modal-overlay" @click.self="$emit('close')">
    <div class="settings-modal">
      <div class="modal-header">
        <h2>偏好设置</h2>
        <button @click="$emit('close')" class="close-btn">✕</button>
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
                v-model="colorSchemeModel"
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
                v-model="colorSchemeModel"
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
          <select v-model="currencyModel" class="currency-select">
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
          <div class="proxy-grid">
            <label class="checkbox-label full-row">
              <input type="checkbox" v-model="proxyEnabledModel" />
              <span>启用代理</span>
            </label>

            <label class="checkbox-label full-row">
              <input type="checkbox" v-model="containerAutoHostModel" />
              <span>容器环境自动将 localhost 映射为宿主机</span>
            </label>

            <div class="field">
              <span>容器宿主机别名</span>
              <input v-model="containerHostModel" class="text-input" placeholder="host.docker.internal" />
            </div>

            <div class="field">
              <span>HTTP 主机</span>
              <input v-model="httpHostModel" class="text-input" placeholder="127.0.0.1" />
            </div>

            <div class="field">
              <span>HTTP 端口</span>
              <input v-model.number="httpPortModel" type="number" class="text-input" min="1" max="65535" />
            </div>

            <div class="field">
              <span>SOCKS5 主机</span>
              <input v-model="socks5HostModel" class="text-input" placeholder="127.0.0.1" />
            </div>

            <div class="field">
              <span>SOCKS5 端口</span>
              <input v-model.number="socks5PortModel" type="number" class="text-input" min="1" max="65535" />
            </div>
          </div>

          <p v-if="proxyMessage" :class="['proxy-message', proxyMessageType]">{{ proxyMessage }}</p>

          <div class="proxy-actions">
            <button class="btn ghost" :disabled="proxySaving" @click="reloadProxy">刷新代理状态</button>
            <button class="btn primary" :disabled="proxySaving" @click="saveProxy">保存代理设置</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import {
  usePreferencesStore,
  type ColorScheme,
  type ProxySettings
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

const colorSchemeModel = computed({
  get: () => colorScheme.value,
  set: (scheme: ColorScheme) => {
    preferences.setColorScheme(scheme)
    emit('update:colorScheme', scheme)
  }
})

const currencyModel = computed({
  get: () => currency.value,
  set: (value: string) => {
    preferences.setCurrency(value)
    emit('update:currency', value)
  }
})

const proxyEnabledModel = computed({
  get: () => proxySettings.value.enabled,
  set: (value: boolean) => {
    preferences.setProxySettings({
      ...proxySettings.value,
      enabled: value
    })
  }
})

const containerAutoHostModel = computed({
  get: () => proxySettings.value.containerAutoHost,
  set: (value: boolean) => {
    preferences.setProxySettings({
      ...proxySettings.value,
      containerAutoHost: value
    })
  }
})

const containerHostModel = computed({
  get: () => proxySettings.value.containerHost,
  set: (value: string) => {
    preferences.setProxySettings({
      ...proxySettings.value,
      containerHost: value
    })
  }
})

const httpHostModel = computed({
  get: () => proxySettings.value.httpHost,
  set: (value: string) => {
    preferences.setProxySettings({
      ...proxySettings.value,
      httpHost: value
    })
  }
})

const httpPortModel = computed({
  get: () => proxySettings.value.httpPort,
  set: (value: number) => {
    preferences.setProxySettings({
      ...proxySettings.value,
      httpPort: Number.isFinite(value) ? value : 8080
    })
  }
})

const socks5HostModel = computed({
  get: () => proxySettings.value.socks5Host,
  set: (value: string) => {
    preferences.setProxySettings({
      ...proxySettings.value,
      socks5Host: value
    })
  }
})

const socks5PortModel = computed({
  get: () => proxySettings.value.socks5Port,
  set: (value: number) => {
    preferences.setProxySettings({
      ...proxySettings.value,
      socks5Port: Number.isFinite(value) ? value : 1080
    })
  }
})

const normalizeProxySettings = (settings: ProxySettings): ProxySettings => {
  const clampPort = (value: number, fallback: number): number => {
    const parsed = Number(value)
    if (!Number.isInteger(parsed) || parsed < 1 || parsed > 65535) {
      return fallback
    }
    return parsed
  }

  return {
    enabled: settings.enabled,
    containerAutoHost: settings.containerAutoHost,
    containerHost: settings.containerHost.trim() || 'host.docker.internal',
    httpHost: settings.httpHost.trim() || '127.0.0.1',
    httpPort: clampPort(settings.httpPort, 8080),
    socks5Host: settings.socks5Host.trim() || '127.0.0.1',
    socks5Port: clampPort(settings.socks5Port, 1080)
  }
}

const reloadProxy = async (): Promise<void> => {
  proxyMessage.value = ''
  await preferences.loadProxySettings()
  proxyMessageType.value = 'ok'
  proxyMessage.value = '已从后端刷新代理配置'
}

const saveProxy = async (): Promise<void> => {
  proxySaving.value = true
  proxyMessage.value = ''

  const normalized = normalizeProxySettings(proxySettings.value)
  preferences.setProxySettings(normalized)

  try {
    const error = await preferences.saveProxySettings(normalized)
    if (error) {
      proxyMessageType.value = 'error'
      proxyMessage.value = error
      return
    }
    proxyMessageType.value = 'ok'
    proxyMessage.value = '代理设置已保存并生效（当前后端进程）'
  } catch (error: unknown) {
    proxyMessageType.value = 'error'
    proxyMessage.value = error instanceof Error ? error.message : '保存代理配置失败'
  } finally {
    proxySaving.value = false
  }
}

onMounted(async () => {
  await preferences.loadProxySettings()
})

</script>

<style scoped>
.settings-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
}

.settings-modal {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  width: 90%;
  max-width: 500px;
  max-height: 80vh;
  overflow: auto;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color);
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

.proxy-actions {
  margin-top: 12px;
  display: flex;
  gap: 10px;
}

.btn {
  border: 1px solid var(--border-color);
  border-radius: 6px;
  padding: 8px 12px;
  font-size: 13px;
  cursor: pointer;
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
  .proxy-grid {
    grid-template-columns: 1fr;
  }
}
</style>
