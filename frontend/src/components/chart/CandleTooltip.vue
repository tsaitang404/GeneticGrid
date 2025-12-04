<template>
  <div
    v-if="data"
    class="candle-tooltip"
    :class="{ locked: locked }"
  >
    <div class="tooltip-header">
      <div class="tooltip-time">{{ formatTime(data.time) }}</div>
      <span
        v-if="locked"
        class="locked-tag"
        aria-label="已锁定"
        title="已锁定"
      >
        🔒
      </span>
    </div>
    
    <template v-if="bar !== 'tick'">
      <div class="tooltip-row">
        <span class="label">开盘</span>
        <span class="value">{{ formatPrice(data.open) }}</span>
      </div>
      <div class="tooltip-row">
        <span class="label">最高</span>
        <span class="value">{{ formatPrice(data.high) }}</span>
      </div>
      <div class="tooltip-row">
        <span class="label">最低</span>
        <span class="value">{{ formatPrice(data.low) }}</span>
      </div>
    </template>
    
    <div class="tooltip-row">
      <span class="label">{{ bar === 'tick' ? '价格' : '收盘' }}</span>
      <span class="value" :class="data.isUp ? 'up' : 'down'">
        {{ formatPrice(data.close) }}
      </span>
    </div>
    
    <div v-if="bar !== 'tick'" class="tooltip-row">
      <span class="label">涨跌</span>
      <span class="value" :class="data.isUp ? 'up' : 'down'">
        {{ data.changePercent }}%
      </span>
    </div>
    
    <div class="tooltip-row">
      <span class="label">成交量</span>
      <span class="value">{{ formatVolume(data.volume) }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { toRefs } from 'vue'
import type { TooltipData } from '@/types'

interface Props {
  data: TooltipData | null
  bar: string
  locked?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  locked: false
})

const { data, bar, locked } = toRefs(props)

const formatTime = (timestamp: number): string => {
  const date = new Date(timestamp * 1000)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const formatPrice = (price: number | undefined): string => {
  if (price === undefined || price === null) return '--'
  return price >= 1000
    ? price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
    : price >= 1
    ? price.toFixed(4)
    : price.toPrecision(4)
}

const formatVolume = (vol: number): string => {
  if (vol === undefined || vol === null) return '--'
  return vol >= 1e9
    ? (vol / 1e9).toFixed(2) + 'B'
    : vol >= 1e6
    ? (vol / 1e6).toFixed(2) + 'M'
    : vol >= 1e3
    ? (vol / 1e3).toFixed(2) + 'K'
    : vol.toFixed(2)
}
</script>

<style scoped>
.candle-tooltip {
  position: absolute;
  top: 12px;
  left: 12px;
  z-index: 20;
  background: rgba(30, 34, 45, 0.9);
  border: 1px solid #2a2e39;
  padding: 8px;
  border-radius: 4px;
  pointer-events: none;
  min-width: 170px;
}

.candle-tooltip.locked {
  border-color: rgba(255, 255, 255, 0.8);
  box-shadow: 0 0 8px rgba(255, 255, 255, 0.15);
}

.tooltip-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 4px;
}

.tooltip-time {
  color: #d1d4dc;
  font-size: 12px;
}

.locked-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 6px;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.1);
  color: #ffffff;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.5px;
}

.tooltip-row {
  display: flex;
  justify-content: space-between;
  margin-bottom: 2px;
}

.tooltip-row .label {
  color: #787b86;
  font-size: 12px;
  margin-right: 12px;
}

.tooltip-row .value {
  color: #d1d4dc;
  font-size: 12px;
  font-weight: bold;
}

.tooltip-row .value.up {
  color: #26a69a;
}

.tooltip-row .value.down {
  color: #ef5350;
}
</style>
