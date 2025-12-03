<template>
  <div class="timeframe-selector">
    <button
      v-for="tf in timeframes"
      :key="tf"
      :class="{ active: modelValue === tf }"
      @click="handleSelect(tf)"
      class="timeframe-btn"
    >
      {{ tf }}
    </button>
    
    <select
      v-model="moreTimeframe"
      @change="handleMoreChange"
      class="more-timeframes"
    >
      <option value="">更多周期...</option>
      <option value="tick">分时</option>
      <option value="1s">1秒</option>
      <option value="5s">5秒</option>
      <option value="15s">15秒</option>
      <option value="30s">30秒</option>
      <option value="1m">1分</option>
      <option value="3m">3分</option>
      <option value="5m">5分</option>
      <option value="15m">15分</option>
      <option value="30m">30分</option>
      <option value="1h">1时</option>
      <option value="3h">3时</option>
      <option value="6h">6时</option>
      <option value="12h">12时</option>
      <option value="1d">1日</option>
      <option value="3d">3日</option>
      <option value="5d">5日</option>
      <option value="1w">1周</option>
      <option value="1M">1月</option>
      <option value="3M">3月</option>
      <option value="custom">自定义...</option>
    </select>
    
    <input
      v-show="showCustomInput"
      v-model="customValue"
      @keydown.enter="applyCustom"
      @blur="cancelCustom"
      ref="customInputRef"
      type="text"
      class="custom-input"
      placeholder="如: 2h, 7d"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick } from 'vue'

interface Props {
  modelValue: string
  timeframes: string[]
}

defineProps<Props>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const moreTimeframe = ref('')
const customValue = ref('')
const showCustomInput = ref(false)
const customInputRef = ref<HTMLInputElement | null>(null)

const handleSelect = (tf: string): void => {
  moreTimeframe.value = ''
  showCustomInput.value = false
  emit('update:modelValue', tf)
}

const handleMoreChange = (): void => {
  if (moreTimeframe.value === 'custom') {
    showCustomInput.value = true
    nextTick(() => {
      customInputRef.value?.focus()
    })
  } else if (moreTimeframe.value) {
    showCustomInput.value = false
    emit('update:modelValue', moreTimeframe.value)
    moreTimeframe.value = ''
  }
}

const applyCustom = (): void => {
  const val = customValue.value.trim().toLowerCase()
  if (val && /^(\d+)([smhdw]|M)$/i.test(val)) {
    emit('update:modelValue', val)
    showCustomInput.value = false
    moreTimeframe.value = ''
    customValue.value = ''
  } else {
    alert('格式错误！请使用格式如: 2h, 7d, 3M')
  }
}

const cancelCustom = (): void => {
  setTimeout(() => {
    if (!customValue.value.trim()) {
      showCustomInput.value = false
      moreTimeframe.value = ''
    }
  }, 200)
}
</script>

<style scoped>
.timeframe-selector {
  display: flex;
  gap: 4px;
  align-items: center;
}

.timeframe-btn {
  background: #2a2e39;
  color: #d1d4dc;
  border: 1px solid #363a45;
  border-radius: 4px;
  padding: 6px 12px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.timeframe-btn:hover {
  background: #363a45;
}

.timeframe-btn.active {
  background: #363a45;
  color: #fff;
  border-color: #434651;
}

.more-timeframes {
  background: #2a2e39;
  color: #d1d4dc;
  border: 1px solid #363a45;
  border-radius: 4px;
  padding: 6px 8px;
  font-size: 12px;
  cursor: pointer;
  outline: none;
  transition: all 0.2s;
}

.more-timeframes:hover {
  background: #363a45;
  border-color: var(--blue-accent);
}

.more-timeframes:focus {
  border-color: var(--blue-accent);
}

.custom-input {
  background: #2a2e39;
  color: #d1d4dc;
  border: 1px solid var(--blue-accent);
  border-radius: 4px;
  padding: 6px 10px;
  font-size: 12px;
  width: 100px;
  outline: none;
  transition: all 0.2s;
}

.custom-input:focus {
  border-color: var(--blue-accent);
  box-shadow: 0 0 0 2px rgba(33, 150, 243, 0.1);
}

.custom-input::placeholder {
  color: #5a5e6b;
}
</style>
