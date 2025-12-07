<template>
  <div class="mode-selector">
    <span class="mode-label">模式</span>
    <div class="mode-toggle" :class="{ 'single-mode': normalizedModes.length === 1 }">
      <button
        v-for="modeOption in normalizedModes"
        :key="modeOption.value"
        class="mode-btn"
        :class="{ active: modeOption.value === modelValue }"
        :disabled="normalizedModes.length === 1 && modeOption.value === modelValue"
        type="button"
        @click="selectMode(modeOption.value)"
      >
        {{ modeOption.label }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { SymbolMode } from '@/types'

interface Props {
  modelValue: SymbolMode
  modes: string[]
}

const props = defineProps<Props>()
const emit = defineEmits<{ 'update:modelValue': [value: SymbolMode] }>()

const modeLabels: Record<string, string> = {
  spot: '现货',
  contract: '永续'
}

const normalizedModes = computed(() => {
  const uniqueModes = Array.from(new Set(props.modes?.length ? props.modes : ['spot']))
  return uniqueModes.map(mode => ({
    value: (mode as SymbolMode) ?? 'spot',
    label: modeLabels[mode] ?? mode.toUpperCase()
  }))
})

const selectMode = (mode: SymbolMode) => {
  if (mode === props.modelValue) return
  emit('update:modelValue', mode)
}
</script>

<style scoped>
.mode-selector {
  display: flex;
  align-items: center;
  gap: 8px;
}

.mode-label {
  font-size: 12px;
  color: var(--text-secondary);
}

.mode-toggle {
  display: inline-flex;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.04);
}

.mode-toggle.single-mode {
  opacity: 0.7;
}

.mode-btn {
  border: none;
  background: transparent;
  color: var(--text-secondary);
  padding: 4px 10px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.mode-btn:not(:last-child) {
  border-right: 1px solid var(--border-color);
}

.mode-btn.active {
  background: rgba(41, 98, 255, 0.2);
  color: #fff;
}

.mode-btn:disabled {
  cursor: default;
}
</style>
