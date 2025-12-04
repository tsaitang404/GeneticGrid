<template>
  <div class="indicator-selector">
    <button
      v-for="item in primaryIndicatorEntries"
      :key="item.key"
      :class="{ active: item.config.enabled }"
      @click="emitToggle(item.key)"
      class="indicator-btn"
    >
      {{ item.config.name }}
    </button>

    <select
      v-model="moreIndicator"
      @change="handleMoreIndicator"
      class="more-indicators"
    >
      <option value="">更多指标...</option>
      <option
        v-for="opt in extraIndicatorOptions"
        :key="opt.key"
        :value="opt.key"
      >
        {{ opt.label }}
      </option>
    </select>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { IndicatorConfig, Indicators } from '@/types'

interface Props {
  indicators: Indicators
}

const props = defineProps<Props>()
const emit = defineEmits<{
  toggle: [key: keyof Indicators]
}>()

const defaultPrimaryKeys: (keyof Indicators)[] = ['ma', 'ema', 'boll', 'macd', 'rsi']
const primaryIndicatorKeys = computed<(keyof Indicators)[]>(() => defaultPrimaryKeys.filter(key => props.indicators[key]))

const primaryIndicatorEntries = computed(() => primaryIndicatorKeys.value
  .map((key) => {
    const config = props.indicators[key]
    if (!config) return null
    return { key, config }
  })
  .filter((item): item is { key: keyof Indicators, config: IndicatorConfig } => item !== null)
)

const moreIndicator = ref('')

const extraIndicatorOptions = computed(() => {
  const primarySet = new Set(primaryIndicatorKeys.value)
  return (Object.entries(props.indicators) as [keyof Indicators, Indicators[keyof Indicators]][])
    .filter(([key]) => !primarySet.has(key))
    .map(([key, config]) => ({ key, label: config.name }))
})

const emitToggle = (key: keyof Indicators): void => {
  emit('toggle', key)
}

const handleMoreIndicator = (): void => {
  if (moreIndicator.value) {
    emitToggle(moreIndicator.value as keyof Indicators)
    moreIndicator.value = ''
  }
}
</script>

<style scoped>
.indicator-selector {
  display: flex;
  gap: 4px;
  align-items: center;
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

.more-indicators {
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

.more-indicators:hover {
  background: #363a45;
  border-color: var(--blue-accent);
}

.more-indicators:focus {
  border-color: var(--blue-accent);
}
</style>
