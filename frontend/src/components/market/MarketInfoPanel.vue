<template>
  <div class="market-info-panel">
    <header class="panel-header">
      <div class="title-block">
        <p class="panel-label">市场信息</p>
        <h2 class="symbol-title">
          <span class="symbol-base">{{ symbolParts.base }}</span>
          <span class="divider">/</span>
          <span class="symbol-quote">{{ symbolParts.quote }}</span>
        </h2>
        <p class="source-note">来自 {{ sourceLabel }}</p>
      </div>
      <div class="change-chip" :class="{ up: tickerData.isUp, down: !tickerData.isUp }">
        <span>{{ signedChange }}</span>
      </div>
    </header>

    <section class="price-card">
      <div class="price-row">
        <span class="price">{{ tickerData.last }}</span>
        <span class="currency-tag">{{ currencyLabel }}</span>
      </div>
      <p class="meta-line">开盘 {{ tickerData.open24h }}</p>
    </section>

    <div class="stat-grid">
      <div class="stat-card">
        <p class="label">24h 涨跌幅</p>
        <p class="value" :class="tickerData.isUp ? 'up' : 'down'">{{ signedChange }}</p>
      </div>
      <div class="stat-card">
        <p class="label">24h 成交量</p>
        <p class="value">{{ tickerData.vol24h }}</p>
      </div>
      <div class="stat-card">
        <p class="label">24h 最高</p>
        <p class="value">{{ tickerData.high24h }}</p>
      </div>
      <div class="stat-card">
        <p class="label">24h 最低</p>
        <p class="value">{{ tickerData.low24h }}</p>
      </div>
    </div>

    <section class="insight-section">
      <div class="section-header">
        <h3>市场脉搏</h3>
        <span class="pulse-dot"></span>
      </div>
      <ul>
        <li v-for="item in insights" :key="item.label" class="insight-row">
          <span class="item-label">{{ item.label }}</span>
          <span class="item-value">{{ item.value }}</span>
        </li>
      </ul>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { TickerData } from '@/types'

interface Props {
  symbol: string
  source: string
  currency: string
  ticker?: TickerData
}

const defaultTicker: TickerData = {
  last: '--',
  open24h: '--',
  high24h: '--',
  low24h: '--',
  vol24h: '--',
  changePercent: '--',
  isUp: true
}

const props = defineProps<Props>()

const tickerData = computed(() => props.ticker ?? defaultTicker)

const symbolParts = computed(() => {
  const symbol = props.symbol?.toUpperCase() || '--'
  if (symbol.includes('-')) {
    const [base, quote] = symbol.split('-')
    return { base: base || '--', quote: quote || '--' }
  }
  const quoteCandidates = ['USDT', 'USDC', 'USD', 'BTC', 'ETH', 'EUR', 'JPY']
  for (const quote of quoteCandidates) {
    if (symbol.endsWith(quote)) {
      return {
        base: symbol.slice(0, Math.max(symbol.length - quote.length, 1)) || '--',
        quote
      }
    }
  }
  return { base: symbol || '--', quote: '--' }
})

const currencyLabel = computed(() => props.currency?.toUpperCase() || 'USDT')

const SOURCE_MAP: Record<string, string> = {
  okx: 'OKX 交易所',
  binance: 'Binance',
  bybit: 'Bybit',
  coinbase: 'Coinbase',
  kraken: 'Kraken',
  coingecko: 'CoinGecko'
}

const sourceLabel = computed(() => {
  const key = props.source?.toLowerCase()
  return SOURCE_MAP[key] || (props.source ? props.source.toUpperCase() : 'MARKET')
})

const signedChange = computed(() => {
  const raw = tickerData.value.changePercent
  if (!raw || raw === '--') return '--'
  const num = Number(raw)
  if (Number.isNaN(num)) {
    return `${raw}%`
  }
  const prefix = num >= 0 ? '+' : ''
  return `${prefix}${num.toFixed(2)}%`
})

const insights = computed(() => {
  const change = Number(tickerData.value.changePercent)
  let mood = '等待更新'
  if (!Number.isNaN(change)) {
    if (change >= 2) mood = '多头主导'
    else if (change <= -2) mood = '空头压制'
    else mood = '区间波动'
  }

  return [
    { label: '市场情绪', value: mood },
    { label: '波动幅度', value: signedChange.value },
    { label: '数据源', value: sourceLabel.value }
  ]
})
</script>

<style scoped>
.market-info-panel {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 16px;
  padding: 20px;
  color: var(--text-primary);
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.35);
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.panel-label {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--text-secondary);
  margin-bottom: 4px;
}

.symbol-title {
  margin: 0;
  font-size: 26px;
  line-height: 1.2;
}

.symbol-base {
  color: #ffffff;
}

.symbol-quote {
  color: var(--text-secondary);
}

.divider {
  margin: 0 4px;
  color: var(--text-secondary);
}

.source-note {
  margin: 6px 0 0;
  font-size: 13px;
  color: var(--text-secondary);
}

.change-chip {
  padding: 6px 12px;
  border-radius: 999px;
  font-weight: 600;
  font-size: 14px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.12);
}

.change-chip.up {
  color: var(--up-color);
  border-color: rgba(38, 166, 154, 0.4);
}

.change-chip.down {
  color: var(--down-color);
  border-color: rgba(239, 83, 80, 0.4);
}

.price-card {
  background: linear-gradient(120deg, rgba(41, 98, 255, 0.25), rgba(41, 98, 255, 0.05));
  border: 1px solid rgba(41, 98, 255, 0.3);
  border-radius: 14px;
  padding: 16px;
}

.price-row {
  display: flex;
  align-items: baseline;
  gap: 10px;
}

.price {
  font-size: 32px;
  font-weight: 600;
}

.currency-tag {
  padding: 3px 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  font-size: 12px;
  letter-spacing: 0.08em;
}

.meta-line {
  margin-top: 8px;
  font-size: 12px;
  color: var(--text-secondary);
}

.stat-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.stat-card {
  padding: 12px;
  border: 1px solid var(--border-color);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.02);
}

.stat-card .label {
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 4px;
}

.stat-card .value {
  font-size: 18px;
  font-weight: 600;
}

.stat-card .hint {
  font-size: 11px;
  color: var(--text-secondary);
  margin-top: 2px;
}

.insight-section {
  border: 1px solid var(--border-color);
  border-radius: 14px;
  padding: 16px;
  background: rgba(255, 255, 255, 0.02);
}

.section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.section-header h3 {
  margin: 0;
  font-size: 14px;
  letter-spacing: 0.08em;
  color: var(--text-secondary);
}

.pulse-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--up-color);
  box-shadow: 0 0 8px var(--up-color);
}

.insight-section ul {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.insight-row {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
}

.item-label {
  color: var(--text-secondary);
}

.item-value {
  font-weight: 600;
}

@media (max-width: 600px) {
  .stat-grid {
    grid-template-columns: 1fr;
  }
}
</style>
