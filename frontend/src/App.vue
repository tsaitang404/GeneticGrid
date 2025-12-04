<template>
  <div id="app" class="app-container">
    <header class="app-header">
      <div class="header-left">
        <h1 class="logo">GeneticGrid</h1>
      </div>
      <div class="header-right">
        <button @click="toggleSettings" class="settings-btn">⚙️ 设置</button>
      </div>
    </header>

    <main class="app-main">
      <KlineChart
        :initial-symbol="initialSymbol"
        :initial-bar="initialBar"
        :initial-source="initialSource"
        :ticker="ticker"
        :currency="currency"
        @symbol-change="handleSymbolChange"
      />
    </main>

    <SettingsModal
      v-if="showSettings"
      @close="toggleSettings"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import KlineChart from './components/chart/KlineChart.vue'
import SettingsModal from './components/settings/SettingsModal.vue'
import { useTicker } from './composables/useTicker'

const initialSymbol = ref<string>('BTCUSDT')
const initialBar = ref<string>('1h')
const initialSource = ref<string>('tradingview')
const showSettings = ref<boolean>(false)
const currency = ref<string>(localStorage.getItem('geneticgrid_currency') || 'USDT')

// Symbol and source for ticker
const currentSymbol = ref<string>(initialSymbol.value)
const currentSource = ref<string>(initialSource.value)

const { ticker, loadTicker } = useTicker(currentSymbol, currentSource, currency)

const toggleSettings = (): void => {
  showSettings.value = !showSettings.value
}

const handleSymbolChange = (symbol: string): void => {
  currentSymbol.value = symbol
}

onMounted(() => {
  loadTicker()
  // Refresh ticker every 5 seconds
  setInterval(() => {
    loadTicker()
  }, 5000)
})

</script>

<style>
/* Hide TradingView watermark and logo globally */
.tv-lightweight-charts [class*="watermark"],
.tv-lightweight-charts > div > canvas + div,
.tv-lightweight-charts table tbody tr:last-child td:last-child,
.tv-lightweight-charts svg[class*="logo"],
.tv-lightweight-charts a[href*="tradingview"],
.tv-lightweight-charts div[class*="branding"],
.tv-lightweight-charts div[class*="logo"] {
  display: none !important;
  visibility: hidden !important;
  opacity: 0 !important;
  width: 0 !important;
  height: 0 !important;
  pointer-events: none !important;
}

/* Hide any SVG that might be a logo */
.tv-lightweight-charts svg path[d*="M2 0H0v10h6v9h21"],
.tv-lightweight-charts svg path[fill*="stroke"] {
  display: none !important;
  opacity: 0 !important;
}
</style>

<style scoped>
.app-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #0d0d0d;
  color: #d1d4dc;
}

.app-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 20px;
  background: #1e222d;
  border-bottom: 1px solid #2a2e39;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 20px;
}

.logo {
  font-size: 20px;
  font-weight: bold;
  margin: 0;
  color: #2962ff;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.settings-btn {
  background: transparent;
  border: 1px solid #2a2e39;
  color: #d1d4dc;
  padding: 6px 12px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 16px;
  transition: all 0.2s;
}

.settings-btn:hover {
  background: #2a2e39;
}

.app-main {
  flex: 1;
  overflow: hidden;
}
</style>
