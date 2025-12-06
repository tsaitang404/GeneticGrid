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
      <div class="main-content">
        <section class="chart-column">
          <KlineChart
            :initial-symbol="initialSymbol"
            :initial-bar="initialBar"
            :initial-source="initialSource"
            :ticker="ticker"
            :currency="currency"
            @symbol-change="handleSymbolChange"
            @source-change="handleSourceChange"
          />
        </section>
        <aside class="market-column">
          <MarketInfoPanel
            :symbol="currentSymbol"
            :source="currentSource"
            :ticker="ticker"
            :currency="currency"
          />
        </aside>
      </div>
    </main>

    <SettingsModal
      v-if="showSettings"
      @close="toggleSettings"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import KlineChart from './components/chart/KlineChart.vue'
import SettingsModal from './components/settings/SettingsModal.vue'
import MarketInfoPanel from './components/market/MarketInfoPanel.vue'
import { useTicker } from './composables/useTicker'
import { usePreferencesStore } from './stores/preferences'

const initialSymbol = ref<string>('BTCUSDT')
const initialBar = ref<string>('1h')
const initialSource = ref<string>('okx')
const showSettings = ref<boolean>(false)

const preferences = usePreferencesStore()
const { currency } = storeToRefs(preferences)

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

const handleSourceChange = (source: string): void => {
  currentSource.value = source
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
  min-height: 100vh;
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
  overflow-x: hidden;
  overflow-y: auto;
  background: radial-gradient(circle at top, rgba(41, 98, 255, 0.07), transparent 40%);
}

.main-content {
  display: flex;
  gap: 24px;
  padding: 24px;
  max-width: 1440px;
  margin: 0 auto;
  box-sizing: border-box;
}

.chart-column {
  flex: 3;
  min-width: 0;
}

.market-column {
  flex: 1;
  min-width: 280px;
  position: sticky;
  top: 24px;
  align-self: flex-start;
}

@media (max-width: 1200px) {
  .main-content {
    flex-direction: column;
  }
  .market-column {
    position: static;
    width: 100%;
  }
}
</style>
