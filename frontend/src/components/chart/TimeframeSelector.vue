<template>
  <div class="timeframe-selector">
    <button
      v-for="tf in primaryTimeframes"
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
      <option value="">更多...</option>
      <option
        v-for="opt in moreOptions"
        :key="opt.value"
        :value="opt.value"
      >
        {{ opt.label }}
      </option>
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
import { ref, nextTick, computed } from 'vue'

interface Props {
  modelValue: string
  timeframes: string[]
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const moreTimeframe = ref('')
const customValue = ref('')
const showCustomInput = ref(false)
const customInputRef = ref<HTMLInputElement | null>(null)

interface OptionItem {
  value: string
  label: string
}

const primaryTimeframes = computed(() => props.timeframes.slice(0, 5))
const extraTimeframes = computed(() => props.timeframes.slice(5))

const defaultMoreOptions: OptionItem[] = [
  { value: 'tick', label: '分时' },
  { value: '1s', label: '1秒' },
  { value: '5s', label: '5秒' },
  { value: '15s', label: '15秒' },
  { value: '30s', label: '30秒' },
  { value: '1m', label: '1分' },
  { value: '3m', label: '3分' },
  { value: '5m', label: '5分' },
  { value: '15m', label: '15分' },
  { value: '30m', label: '30分' },
  { value: '1h', label: '1时' },
  { value: '3h', label: '3时' },
  { value: '6h', label: '6时' },
  { value: '12h', label: '12时' },
  { value: '1d', label: '1日' },
  { value: '3d', label: '3日' },
  { value: '5d', label: '5日' },
  { value: '1w', label: '1周' },
  { value: '1M', label: '1月' },
  { value: '3M', label: '3月' }
]

const moreOptions = computed<OptionItem[]>(() => {
  const seen = new Set<string>()
  const result: OptionItem[] = []
  extraTimeframes.value.forEach((tf) => {
    if (!seen.has(tf)) {
      result.push({ value: tf, label: tf })
      seen.add(tf)
    }
  })
  defaultMoreOptions.forEach((opt) => {
    if (!seen.has(opt.value)) {
      result.push(opt)
      seen.add(opt.value)
    }
  })
  return result
})

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
