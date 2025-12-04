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
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { usePreferencesStore, type ColorScheme } from '@/stores/preferences'

const emit = defineEmits<{
  close: []
  'update:colorScheme': [scheme: string]
  'update:currency': [currency: string]
}>()

const preferences = usePreferencesStore()
const { colorScheme, currency } = storeToRefs(preferences)

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
</style>
