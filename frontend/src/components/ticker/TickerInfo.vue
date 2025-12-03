<template>
  <div class="ticker-info">
    <div class="ticker-item">
      <span class="ticker-label">最新价</span>
      <span 
        class="ticker-value" 
        :class="{ up: ticker.isUp, down: !ticker.isUp }"
      >
        {{ displayPrice(ticker.last) }}
      </span>
    </div>
    <div class="ticker-item">
      <span class="ticker-label">24h涨跌</span>
      <span 
        class="ticker-value" 
        :class="{ up: ticker.isUp, down: !ticker.isUp }"
      >
        {{ ticker.isUp ? '+' : '' }}{{ ticker.changePercent }}%
      </span>
    </div>
    <div class="ticker-item">
      <span class="ticker-label">24h最高</span>
      <span class="ticker-value">{{ displayPrice(ticker.high24h) }}</span>
    </div>
    <div class="ticker-item">
      <span class="ticker-label">24h最低</span>
      <span class="ticker-value">{{ displayPrice(ticker.low24h) }}</span>
    </div>
    <div class="ticker-item">
      <span class="ticker-label">24h成交量</span>
      <span class="ticker-value">{{ formatVolume(ticker.vol24h) }}</span>
    </div>
    <div class="ticker-item ticker-currency">
      <span class="ticker-label">计价</span>
      <span class="ticker-value">{{ currency }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
interface TickerData {
  last: string
  high24h: string
  low24h: string
  vol24h: string
  changePercent: string
  isUp: boolean
}

interface Props {
  ticker: TickerData
  currency?: string
}

withDefaults(defineProps<Props>(), {
  currency: 'USDT'
})

const displayPrice = (price: string): string => {
  if (price === '--') return '--'
  return price
}

const formatVolume = (vol: string): string => {
  if (vol === '--') return '--'
  const num = parseFloat(vol.replace(/,/g, ''))
  if (isNaN(num)) return vol
  
  if (num >= 1e9) {
    return (num / 1e9).toFixed(2) + 'B'
  } else if (num >= 1e6) {
    return (num / 1e6).toFixed(2) + 'M'
  } else if (num >= 1e3) {
    return (num / 1e3).toFixed(2) + 'K'
  }
  return num.toFixed(2)
}
</script>

<style scoped>
.ticker-info {
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 12px 20px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
  overflow-x: auto;
}

.ticker-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 100px;
}

.ticker-currency {
  margin-left: auto;
  min-width: auto;
}

.ticker-label {
  font-size: 12px;
  color: #808080;
}

.ticker-value {
  font-size: 14px;
  font-weight: 500;
  color: #d1d4dc;
}

.ticker-value.up {
  color: #26a69a;
}

.ticker-value.down {
  color: #ef5350;
}

@media (max-width: 768px) {
  .ticker-info {
    gap: 16px;
    padding: 10px 16px;
  }
  
  .ticker-item {
    min-width: 80px;
  }
}
</style>
