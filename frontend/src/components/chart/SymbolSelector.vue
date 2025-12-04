<template>
  <div class="symbol-selector">
    <label class="symbol-label">币对</label>
    <select 
      :value="modelValue"
      @change="$emit('update:modelValue', ($event.target as HTMLSelectElement).value)"
      class="symbol-select"
    >
      <option v-for="sym in symbols" :key="sym" :value="sym">
        {{ sym }}
      </option>
    </select>
  </div>
</template>

<script setup lang="ts">
interface Props {
  modelValue: string
  symbols: string[]
}

defineProps<Props>()
defineEmits<{
  'update:modelValue': [value: string]
}>()
</script>

<style scoped>
.symbol-selector {
  display: flex;
  align-items: center;
  gap: 8px;
}

.symbol-label {
  color: var(--text-secondary);
  font-size: 13px;
}

.symbol-select {
  padding: 6px 12px;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  background: var(--bg-primary);
  color: var(--text-primary);
  font-size: 14px;
  cursor: pointer;
  outline: none;
  min-width: 120px;
  transition: all 0.2s;
}

.symbol-select:hover {
  border-color: var(--blue-accent);
}

.symbol-select:focus {
  border-color: var(--blue-accent);
  box-shadow: 0 0 0 2px rgba(41, 98, 255, 0.2);
}
</style>
