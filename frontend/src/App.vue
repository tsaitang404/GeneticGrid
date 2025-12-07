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
            :initial-mode="initialMode"
            :ticker="ticker"
            :currency="currency"
            @symbol-change="handleSymbolChange"
            @source-change="handleSourceChange"
            @mode-change="handleModeChange"
          />
        </section>
        <aside class="market-column">
          <!-- 合约模式下的标签切换 -->
          <div v-if="currentMode === 'contract'" class="panel-tabs">
            <button 
              :class="['tab-btn', { active: activeTab === 'market' }]"
              @click="activeTab = 'market'"
            >
              市场信息
            </button>
            <button 
              :class="['tab-btn', { active: activeTab === 'funding' }]"
              @click="activeTab = 'funding'"
            >
              资金费率
            </button>
            <button 
              :class="['tab-btn', { active: activeTab === 'basis' }]"
              @click="activeTab = 'basis'"
            >
              合约基差
            </button>
          </div>

          <MarketInfoPanel
            v-show="currentMode === 'spot' || activeTab === 'market'"
            :symbol="currentSymbol"
            :source="currentSource"
            :ticker="ticker"
            :currency="currency"
          />
          
          <FundingRatePanel
            v-if="currentMode === 'contract' && activeTab === 'funding'"
            :symbol="currentSymbol"
            :source="currentSource"
            :funding-data="fundingRate"
            :loading="fundingLoading"
            :error="fundingError"
            @retry="loadFundingRate"
          />
          
          <ContractBasisPanel
            v-if="currentMode === 'contract' && activeTab === 'basis'"
            :symbol="currentSymbol"
            :source="currentSource"
            :basis-data="contractBasis"
            :loading="basisLoading"
            :error="basisError"
            @retry="loadContractBasis"
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
import { ref, onMounted, watch } from 'vue'
import { storeToRefs } from 'pinia'
import KlineChart from './components/chart/KlineChart.vue'
import SettingsModal from './components/settings/SettingsModal.vue'
import MarketInfoPanel from './components/market/MarketInfoPanel.vue'
import FundingRatePanel from './components/market/FundingRatePanel.vue'
import ContractBasisPanel from './components/market/ContractBasisPanel.vue'
import { useTicker } from './composables/useTicker'
import { usePreferencesStore } from './stores/preferences'
import type { SymbolMode } from '@/types'

const initialSymbol = ref<string>('BTCUSDT')
const initialBar = ref<string>('1h')
const initialSource = ref<string>('okx')
const initialMode = ref<SymbolMode>('spot')
const showSettings = ref<boolean>(false)
const activeTab = ref<'market' | 'funding' | 'basis'>('market')

const preferences = usePreferencesStore()
const { currency } = storeToRefs(preferences)

// Symbol and source for ticker
const currentSymbol = ref<string>(initialSymbol.value)
const currentSource = ref<string>(initialSource.value)
const currentMode = ref<SymbolMode>(initialMode.value)

const { ticker, loadTicker } = useTicker(currentSymbol, currentSource, currency, currentMode)

// Funding rate data
const fundingRate = ref<any>({})
const fundingLoading = ref<boolean>(false)
const fundingError = ref<string>('')

// Contract basis data
const contractBasis = ref<any>({})
const basisLoading = ref<boolean>(false)
const basisError = ref<string>('')

const toggleSettings = (): void => {
  showSettings.value = !showSettings.value
}

const handleSymbolChange = (symbol: string): void => {
  currentSymbol.value = symbol
}

const handleSourceChange = (source: string): void => {
  currentSource.value = source
}

const handleModeChange = (mode: SymbolMode): void => {
  currentMode.value = mode
  // 模式切换时重置标签为市场信息
  activeTab.value = 'market'
}

const loadFundingRate = async (): Promise<void> => {
  if (currentMode.value !== 'contract') return
  
  fundingLoading.value = true
  fundingError.value = ''
  
  try {
    const response = await fetch(
      `/api/funding-rate/?symbol=${currentSymbol.value}&source=${currentSource.value}`
    )
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }
    
    const result = await response.json()
    
    if (result.code === 0 && result.data) {
      fundingRate.value = result.data
    } else {
      fundingError.value = result.error || '获取资金费率失败'
    }
  } catch (error: any) {
    console.error('Failed to load funding rate:', error)
    fundingError.value = error.message || '网络错误'
  } finally {
    fundingLoading.value = false
  }
}

const loadContractBasis = async (): Promise<void> => {
  if (currentMode.value !== 'contract') return
  
  basisLoading.value = true
  basisError.value = ''
  
  try {
    const response = await fetch(
      `/api/contract-basis/?symbol=${currentSymbol.value}&source=${currentSource.value}&contract_type=perpetual`
    )
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }
    
    const result = await response.json()
    
    if (result.code === 0 && result.data) {
      contractBasis.value = result.data
    } else {
      basisError.value = result.error || '获取合约基差失败'
    }
  } catch (error: any) {
    console.error('Failed to load contract basis:', error)
    basisError.value = error.message || '网络错误'
  } finally {
    basisLoading.value = false
  }
}

// 监听模式、交易对或数据源变化
watch([currentMode, currentSymbol, currentSource], () => {
  if (currentMode.value === 'contract') {
    loadFundingRate()
    loadContractBasis()
  }
})

onMounted(() => {
  loadTicker()
  
  // 如果初始模式是合约，加载资金费率和基差
  if (currentMode.value === 'contract') {
    loadFundingRate()
    loadContractBasis()
  }
  
  // Refresh ticker every 5 seconds
  setInterval(() => {
    loadTicker()
  }, 5000)
  
  // Refresh funding rate and basis every 30 seconds in contract mode
  setInterval(() => {
    if (currentMode.value === 'contract') {
      if (activeTab.value === 'funding') {
        loadFundingRate()
      } else if (activeTab.value === 'basis') {
        loadContractBasis()
      }
    }
  }, 30000)
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

.panel-tabs {
  display: flex;
  background-color: #1e222d;
  border-bottom: 1px solid #2a2e39;
  padding: 0 12px;
  gap: 4px;
}

.tab-btn {
  padding: 12px 16px;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  color: #787b86;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
  white-space: nowrap;
}

.tab-btn:hover {
  color: #d1d4dc;
  background-color: rgba(255, 255, 255, 0.03);
}

.tab-btn.active {
  color: #2962ff;
  border-bottom-color: #2962ff;
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
