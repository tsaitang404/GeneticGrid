<template>
  <div class="source-selector">
    <label class="source-label">数据源:</label>
    <select
      :value="modelValue"
      @change="handleChange"
      class="source-select"
      title="选择数据源"
    >
      <option
        v-for="src in sources"
        :key="src.value"
        :value="src.value"
      >
        {{ src.label }}
      </option>
    </select>
  </div>
</template>

<script setup lang="ts">
interface Source {
  value: string
  label: string
}

interface Props {
  modelValue: string
  sources?: Source[]
}

withDefaults(defineProps<Props>(), {
  sources: () => [
    { value: 'tradingview', label: 'TradingView' },
    { value: 'binance', label: 'Binance' },
    { value: 'coingecko', label: 'CoinGecko' },
    { value: 'okx', label: 'OKX' }
  ]
})

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const handleChange = (event: Event): void => {
  const target = event.target as HTMLSelectElement
  emit('update:modelValue', target.value)
}
</script>

<style scoped>
.source-selector {
  display: flex;
  align-items: center;
  gap: 8px;
}

.source-label {
  font-size: 14px;
  color: var(--text-secondary);
}

.source-select {
  padding: 6px 10px;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  background: var(--bg-primary);
  color: var(--text-primary);
  font-size: 14px;
  cursor: pointer;
  outline: none;
  transition: all 0.2s;
}

.source-select:hover {
  border-color: var(--blue-accent);
}

.source-select:focus {
  border-color: var(--blue-accent);
  box-shadow: 0 0 0 2px rgba(33, 150, 243, 0.1);
}
</style>
