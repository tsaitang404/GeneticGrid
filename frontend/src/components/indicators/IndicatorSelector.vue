<template>
  <div class="indicator-selector">
    <button
      v-for="(config, key) in indicators"
      :key="key"
      :class="{ active: config.enabled }"
      @click="$emit('toggle', key)"
      class="indicator-btn"
    >
      {{ config.name }}
    </button>
  </div>
</template>

<script setup lang="ts">
import type { Indicators } from '@/types'

interface Props {
  indicators: Indicators
}

defineProps<Props>()
defineEmits<{
  toggle: [key: keyof Indicators]
}>()
</script>

<style scoped>
.indicator-selector {
  display: flex;
  gap: 4px;
}

.indicator-btn {
  background: #2a2e39;
  color: #d1d4dc;
  border: 1px solid #363a45;
  border-radius: 4px;
  padding: 6px 12px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.indicator-btn:hover {
  background: #363a45;
}

.indicator-btn.active {
  background: #363a45;
  color: #fff;
  border-color: #434651;
}
</style>
