<template>
  <div class="kline-chart-container">
    <!-- 顶部控制栏 -->
    <div class="control-bar">
      <SymbolSelector
        v-model="symbol"
        :symbols="availableSymbols"
      />
      
      <TimeframeSelector
        v-model="bar"
        :timeframes="availableTimeframes"
      />
      
      <IndicatorSelector
        :indicators="indicators"
        @toggle="toggleIndicator"
      />
      
      <SourceSelector
        v-model="source"
      />
      
      <RefreshControls
        :autoRefresh="autoRefresh"
        @refresh="handleManualRefresh"
        @toggle-auto-refresh="toggleAutoRefresh"
      />
      
      <div class="price-info">
        <span class="label">最新价:</span>
        <span class="value" :class="priceChangeClass">{{ latestPrice }}</span>
        <span class="label">24h涨跌:</span>
        <span class="value" :class="priceChangeClass">{{ priceChange }}</span>
      </div>
    </div>

    <!-- 图表区域 -->
    <div class="chart-area" ref="chartContainerRef">
      <div v-if="isLoading" class="loading-overlay">
        <div class="spinner">加载中...</div>
      </div>

      <!-- 主图 -->
      <div
        class="main-chart"
        :style="{ height: mainChartHeight + 'px' }"
      >
        <DrawingToolbar
          :modelValue="currentTool"
          :expanded="toolbarExpanded"
          @update:tool="currentTool = $event"
          @update:expanded="toolbarExpanded = $event"
          @clear="clearDrawings"
        />

        <canvas
          ref="drawingCanvasRef"
          class="drawing-canvas"
          @mousedown="handleCanvasMouseDown"
        />

        <div
          v-if="chartError.show"
          class="error-overlay"
        >
          <div class="error-content">
            <div class="error-icon">⚠️</div>
            <div class="error-title">图表加载失败</div>
            <div class="error-message">{{ chartError.message }}</div>
            <button @click="retryLoad" class="retry-btn">重试</button>
          </div>
        </div>

        <div ref="mainChartRef" class="chart-wrapper" />

        <CandleTooltip
          v-if="tooltipData"
          :data="tooltipData"
          :bar="bar"
        />

        <div
          ref="noDataOverlayRef"
          class="no-data-overlay"
          :style="{ width: noDataWidth }"
        >
          无数据
        </div>
      </div>

      <!-- 主图调整条 -->
      <ResizeHandle
        v-if="hasSubIndicators"
        @resize-start="startResize('main', $event)"
      />

      <!-- 副图区域 -->
      <div class="sub-charts">
        <template v-for="(config, key) in enabledSubIndicators" :key="key">
          <div
            v-show="config.enabled"
            class="sub-chart"
            :style="{ height: subChartHeights[key] + 'px' }"
          >
            <div
              :ref="el => setSubChartRef(el as HTMLElement | null, String(key))"
              class="chart-wrapper"
            />
            
            <ResizeHandle
              @resize-start="startResize(String(key), $event)"
            />
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import SymbolSelector from './SymbolSelector.vue'
import TimeframeSelector from './TimeframeSelector.vue'
import SourceSelector from './SourceSelector.vue'
import RefreshControls from './RefreshControls.vue'
import IndicatorSelector from '../indicators/IndicatorSelector.vue'
import DrawingToolbar from '../tools/DrawingToolbar.vue'
import CandleTooltip from './CandleTooltip.vue'
import ResizeHandle from './ResizeHandle.vue'
import { useChart } from '@/composables/useChart'
import { useIndicators } from '@/composables/useIndicators'
import { useDrawingTools } from '@/composables/useDrawingTools'
import { useChartResize } from '@/composables/useChartResize'
import type { ChartError, TooltipData } from '@/types'

interface Props {
  initialSymbol?: string
  initialBar?: string
  initialSource?: string
}

const props = withDefaults(defineProps<Props>(), {
  initialSymbol: 'BTCUSDT',
  initialBar: '1h',
  initialSource: 'okx'
})

const emit = defineEmits<{
  'symbol-change': [symbol: string]
  'bar-change': [bar: string]
}>()

// Refs
const chartContainerRef = ref<HTMLElement | null>(null)
const mainChartRef = ref<HTMLElement | null>(null)
const drawingCanvasRef = ref<HTMLCanvasElement | null>(null)
const noDataOverlayRef = ref<HTMLElement | null>(null)

// State
const symbol = ref<string>(props.initialSymbol)
const bar = ref<string>(props.initialBar)
const source = ref<string>(props.initialSource)
const isLoading = ref<boolean>(true)
const autoRefresh = ref<boolean>(true)
const latestPrice = ref<string>('--')
const priceChange = ref<string>('--')
const priceChangeClass = ref<'up' | 'down'>('up')
const chartError = ref<ChartError>({ show: false, message: '' })
const tooltipData = ref<TooltipData | null>(null)
const noDataWidth = ref<string>('0px')

// Available options
const availableSymbols = ref<string[]>(['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'ADAUSDT'])
const availableTimeframes = ref<string[]>(['1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w'])

// Use composables
const {
  chart,
  subCharts,
  allCandles,
  hasMoreData,
  initChart,
  loadCandlesticks,
  updateLatestData,
  updateNoDataOverlay,
  retryLoad: chartRetryLoad
} = useChart(mainChartRef, {
  symbol,
  bar,
  source,
  onLoading: (loading: boolean) => { isLoading.value = loading },
  onError: (error: ChartError) => { chartError.value = error },
  onPriceUpdate: (price: string, change: string, isUp: boolean) => {
    latestPrice.value = price
    priceChange.value = change
    priceChangeClass.value = isUp ? 'up' : 'down'
  }
})

const {
  indicators,
  toggleIndicator,
  enabledSubIndicators,
  hasSubIndicators,
  setSubChartRef,
  triggerWorkerCalculation,
  cleanup: cleanupIndicators
} = useIndicators(chart, subCharts, allCandles)

const {
  currentTool,
  toolbarExpanded,
  clearDrawings,
  handleCanvasMouseDown
} = useDrawingTools(drawingCanvasRef, chart)

const {
  mainChartHeight,
  subChartHeights,
  startResize
} = useChartResize(chart, subCharts)

// Methods
const retryLoad = (): void => {
  chartError.value.show = false
  chartRetryLoad()
}

const handleManualRefresh = async (): Promise<void> => {
  await updateLatestData()
}

const toggleAutoRefresh = (): void => {
  autoRefresh.value = !autoRefresh.value
}

// Watch for symbol and bar changes to emit events
watch(symbol, (newSymbol) => {
  emit('symbol-change', newSymbol)
})

watch(bar, (newBar) => {
  emit('bar-change', newBar)
})

// Watch for source changes to reload data
watch(source, () => {
  initChart()
  loadCandlesticks()
})

// Watch for data changes to update no-data overlay
watch([allCandles, hasMoreData], () => {
  const result = updateNoDataOverlay()
  if (result.show && noDataOverlayRef.value) {
    noDataOverlayRef.value.style.display = 'flex'
    noDataOverlayRef.value.style.width = `${result.width}px`
  } else if (noDataOverlayRef.value) {
    noDataOverlayRef.value.style.display = 'none'
  }
}, { deep: true })

// Lifecycle
onMounted(async () => {
  initChart()
  await loadCandlesticks()
  
  // Trigger indicator calculations after data is loaded
  if (allCandles.value.length > 0) {
    triggerWorkerCalculation()
  }
  
  // Auto refresh
  const refreshInterval = setInterval(() => {
    if (autoRefresh.value) {
      updateLatestData()
    }
  }, 2000)
  
  onUnmounted(() => {
    clearInterval(refreshInterval)
    cleanupIndicators()
  })
})
</script>

<style scoped>
.kline-chart-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--bg-primary);
}

.control-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
}

.price-info {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 14px;
}

.price-info .label {
  color: var(--text-secondary);
}

.price-info .value {
  font-weight: bold;
}

.price-info .value.up {
  color: var(--up-color);
}

.price-info .value.down {
  color: var(--down-color);
}

.chart-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden;
}

.loading-overlay {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 1000;
  background: rgba(30, 34, 45, 0.9);
  padding: 20px 40px;
  border-radius: 8px;
  color: var(--text-primary);
}

.main-chart {
  position: relative;
  width: 100%;
  flex-shrink: 0;
}

.drawing-canvas {
  position: absolute;
  top: 0;
  left: 0;
  z-index: 5;
  pointer-events: none;
}

.chart-wrapper {
  width: 100%;
  height: 100%;
}

.error-overlay {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 100;
  text-align: center;
}

.error-content {
  background: rgba(30, 34, 45, 0.95);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 30px;
  max-width: 400px;
}

.error-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.error-title {
  font-size: 18px;
  font-weight: bold;
  margin-bottom: 8px;
  color: var(--text-primary);
}

.error-message {
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: 16px;
}

.retry-btn {
  background: var(--blue-accent);
  color: white;
  border: none;
  border-radius: 4px;
  padding: 10px 20px;
  font-size: 14px;
  cursor: pointer;
  transition: opacity 0.2s;
}

.retry-btn:hover {
  opacity: 0.9;
}

.no-data-overlay {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 28px;
  background: rgba(255, 255, 255, 0.08);
  border-right: 1px solid rgba(255, 255, 255, 0.2);
  display: none;
  align-items: center;
  justify-content: center;
  color: rgba(255, 255, 255, 0.5);
  font-size: 13px;
  pointer-events: none;
  z-index: 5;
}

.sub-charts {
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.sub-chart {
  width: 100%;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}
</style>
