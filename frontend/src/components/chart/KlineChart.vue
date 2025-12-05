<template>
  <div class="kline-chart-container">
    <!-- 顶部工具栏 -->
    <div class="chart-toolbar">
      <!-- 行情信息行 -->
      <div class="toolbar-info-row">
        <div class="info-item">
          <span class="label">交易对</span>
          <span class="value pair-value">
            <span class="pair-base">{{ symbolParts.base }}</span>
            <span class="divider">/</span>
            <span class="pair-quote">{{ symbolParts.quote }}</span>
          </span>
        </div>
        <div class="info-item">
          <span class="label">最新价 ({{ currencyLabel }})</span>
          <span class="value" :class="displayTicker.isUp ? 'up' : 'down'">{{ displayTicker.last }}</span>
        </div>
        <div class="info-item">
          <span class="label">24h涨跌幅</span>
          <span class="value" :class="displayTicker.isUp ? 'up' : 'down'">{{ displayTicker.changePercent }}</span>
        </div>
        <div class="info-item">
          <span class="label">24h最高</span>
          <span class="value">{{ displayTicker.high24h }}</span>
        </div>
        <div class="info-item">
          <span class="label">24h最低</span>
          <span class="value">{{ displayTicker.low24h }}</span>
        </div>
        <div class="info-item">
          <span class="label">24h成交量</span>
          <span class="value">{{ displayTicker.vol24h }}</span>
        </div>
      </div>

      <!-- 控制工具行 -->
      <div class="toolbar-controls-row">
        <div class="controls-group market-group">
          <div class="group-label">市场</div>
          <SourceSelector
            v-model="source"
            @sourceChanged="handleSourceChange"
          />
          <div class="divider-vertical"></div>
          <SymbolSelector
            v-model="symbol"
            :symbols="availableSymbols"
            :source="source"
          />
        </div>

        <div class="controls-group chart-group">
          <div class="group-label">图表</div>
          <TimeframeSelector
            v-model="bar"
            :timeframes="availableTimeframes"
          />
          <div class="divider-vertical"></div>
          <IndicatorSelector
            :indicators="indicators"
            @toggle="toggleIndicator"
          />
        </div>

        <div class="controls-group actions-group">
          <button 
            @click="toggleAutoRefresh" 
            :class="['action-btn', 'refresh-btn', { active: autoRefreshEnabled }]"
            :title="autoRefreshEnabled ? '关闭自动刷新' : '开启自动刷新'"
          >
            <svg class="icon" width="16" height="16" viewBox="0 0 16 16">
              <path d="M13.65 2.35A7.5 7.5 0 0 0 3.5 4.5M2.35 13.65A7.5 7.5 0 0 0 12.5 11.5" stroke="currentColor" stroke-width="1.5" fill="none" stroke-linecap="round"/>
              <path d="M12.5 4.5v-2h2M3.5 11.5v2h-2" stroke="currentColor" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <span>{{ autoRefreshEnabled ? '自动刷新' : '手动刷新' }}</span>
          </button>
        </div>
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
        <!-- 跳转到最新按钮 -->
        <button 
          class="jump-to-latest-btn"
          @click="jumpToLatest"
          title="跳转到最新K线"
        >
          ▶
        </button>

        <DrawingToolbar
          :modelValue="currentTool"
          :expanded="toolbarExpanded"
          @update:tool="handleToolbarToolUpdate"
          @update:expanded="toolbarExpanded = $event"
          @clear="handleToolbarClear"
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

        <!-- 主图指标图例 -->
        <div v-if="mainChartLegends.length > 0" class="main-chart-legends">
          <div
            v-for="(group, index) in mainChartLegends"
            :key="group.indicator + index"
            class="legend-group"
          >
            <span
              v-for="line in group.lines"
              :key="line.name"
              class="legend-item"
              :style="{ color: line.color }"
            >
              {{ line.name }}
            </span>
          </div>
        </div>

        <CandleTooltip
          v-if="tooltipData"
          :data="tooltipData"
          :bar="bar"
          :locked="isTooltipLocked"
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
import { ref, onMounted, onUnmounted, watch, computed } from 'vue'
import { storeToRefs } from 'pinia'
import type { MouseEventParams, Time, UTCTimestamp, ISeriesApi, IChartApi, CandlestickData } from 'lightweight-charts'
import SymbolSelector from './SymbolSelector.vue'
import TimeframeSelector from './TimeframeSelector.vue'
import SourceSelector from './SourceSelector.vue'
import IndicatorSelector from '../indicators/IndicatorSelector.vue'
import DrawingToolbar from '../tools/DrawingToolbar.vue'
import CandleTooltip from './CandleTooltip.vue'
import ResizeHandle from './ResizeHandle.vue'
import { useChart } from '@/composables/useChart'
import { useIndicators } from '@/composables/useIndicators'
import { useDrawingTools } from '@/composables/useDrawingTools'
import { useChartResize } from '@/composables/useChartResize'
import type { Candle, ChartError, TooltipData, TickerData, DrawingType } from '@/types'
import { usePreferencesStore } from '@/stores/preferences'

interface Props {
  initialSymbol?: string
  initialBar?: string
  initialSource?: string
  ticker?: TickerData | null
  currency?: string
}

const props = withDefaults(defineProps<Props>(), {
  initialSymbol: 'BTCUSDT',
  initialBar: '1h',
  initialSource: 'okx',
  ticker: null,
  currency: 'USDT'
})

const emit = defineEmits<{
  'symbol-change': [symbol: string]
  'bar-change': [bar: string]
}>()

const preferences = usePreferencesStore()
const { upColor, downColor, volumeUpColor, volumeDownColor } = storeToRefs(preferences)

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
const latestPrice = ref<string>('--')
const priceChange = ref<string>('--')
const priceChangeClass = ref<'up' | 'down'>('up')
const chartError = ref<ChartError>({ show: false, message: '' })
const tooltipData = ref<TooltipData | null>(null)
const hoveredCandle = ref<Candle | null>(null)
const lockedCandle = ref<Candle | null>(null)
const noDataWidth = ref<string>('0px')
const autoRefreshEnabled = ref<boolean>(true)
const autoRefreshTimer = ref<number | null>(null)

// Available options
const availableSymbols = ref<string[]>(['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'ADAUSDT'])
const availableTimeframes = ref<string[]>(['tick', '1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w'])

// Handle source change to update available symbols and timeframes
const handleSourceChange = (sourceData: any) => {
  console.log('Source changed:', sourceData)
  
  // Update available symbols
  if (sourceData.supported_symbols && sourceData.supported_symbols.length > 0) {
    availableSymbols.value = sourceData.supported_symbols
    // If current symbol is not available in new source, select the first one
    if (!availableSymbols.value.includes(symbol.value)) {
      symbol.value = availableSymbols.value[0]
    }
  }
  
  // Update available timeframes
  if (sourceData.candlestick_granularities && sourceData.candlestick_granularities.length > 0) {
    availableTimeframes.value = sourceData.candlestick_granularities
    // If current bar is not available in new source, select the first one
    if (!availableTimeframes.value.includes(bar.value)) {
      // Try to find a similar timeframe or fall back to first available
      const fallback = availableTimeframes.value.find(tf => ['1h', '1d', '15m', '5m', '1m'].includes(tf)) 
                      || availableTimeframes.value[0]
      bar.value = fallback
    }
  }
}

const quoteCandidates = ['USDT', 'USDC', 'USD', 'BTC', 'ETH', 'BNB', 'EUR', 'CNY', 'JPY', 'KRW', 'GBP']

const symbolParts = computed(() => {
  const upper = symbol.value?.toUpperCase() || '--'
  if (upper.includes('-')) {
    const [base, quote] = upper.split('-')
    return { base: base || '--', quote: quote || '--' }
  }
  for (const quote of quoteCandidates) {
    if (upper.endsWith(quote)) {
      return {
        base: upper.slice(0, Math.max(upper.length - quote.length, 1)) || '--',
        quote
      }
    }
  }
  return { base: upper || '--', quote: '--' }
})

const currencyLabel = computed(() => props.currency?.toUpperCase() || 'USDT')

const displayTicker = computed(() => {
  const t = props.ticker
  return {
    last: t?.last ?? latestPrice.value,
    changePercent: t ? `${t.isUp ? '+' : ''}${t.changePercent}%` : `${priceChange.value}${priceChange.value === '--' ? '' : '%'}`,
    isUp: t?.isUp ?? (priceChangeClass.value === 'up'),
    high24h: t?.high24h ?? '--',
    low24h: t?.low24h ?? '--',
    vol24h: t?.vol24h ?? '--'
  }
})

const isTooltipLocked = computed(() => lockedCandle.value !== null)

const toTooltipData = (candle: Candle): TooltipData => {
  let changePercent = '--'
  if (candle.open) {
    const change = ((candle.close - candle.open) / candle.open) * 100
    const formatted = Math.abs(change) >= 0.01 ? change.toFixed(2) : change.toFixed(4)
    changePercent = `${change >= 0 ? '+' : ''}${formatted}`
  }

  return {
    time: candle.time,
    open: candle.open,
    high: candle.high,
    low: candle.low,
    close: candle.close,
    volume: candle.volume,
    changePercent,
    isUp: candle.close >= candle.open
  }
}

const refreshTooltipData = (): void => {
  const active = lockedCandle.value ?? hoveredCandle.value
  tooltipData.value = active ? toTooltipData(active) : null
}

watch([lockedCandle, hoveredCandle], () => {
  refreshTooltipData()
})

// Use composables
const {
  chart,
  subCharts,
  candleSeries,
  lineSeries,
  allCandles,
  hasMoreData,
  isTimelineMode,
  initialize,
  initChart,
  loadCandlesticks,
  updateLatestData,
  updateNoDataOverlay,
  retryLoad: chartRetryLoad
} = useChart(mainChartRef, {
  symbol,
  bar,
  source,
  colors: {
    up: upColor,
    down: downColor,
    volumeUp: volumeUpColor,
    volumeDown: volumeDownColor
  },
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
  mainChartLegends,
  setSubChartRef,
  triggerWorkerCalculation,
  cleanup: cleanupIndicators
} = useIndicators(chart, subCharts, allCandles)

const {
  currentTool,
  toolbarExpanded,
  clearDrawings,
  handleCanvasMouseDown
} = useDrawingTools(drawingCanvasRef, chart, candleSeries, lineSeries, isTimelineMode)

const {
  mainChartHeight,
  subChartHeights,
  startResize
} = useChartResize(chart, subCharts)

const handleToolbarToolUpdate = (tool: DrawingType): void => {
  if (tool === 'delete') {
    currentTool.value = 'delete'
    return
  }
  currentTool.value = tool
}

const handleToolbarClear = (): void => {
  clearDrawings()
  currentTool.value = 'cursor'
}

// 根据K线周期确定刷新间隔（毫秒）
const getRefreshInterval = computed(() => {
  const barValue = bar.value.toLowerCase()
  
  // 分时每秒刷新
  if (barValue === 'tick') return 1000
  
  // 解析时间单位
  const match = barValue.match(/^(\d+)([smhdwM])$/)
  if (!match) return 5000 // 默认5秒
  
  const [, numStr, unit] = match
  const num = parseInt(numStr, 10)
  
  // 根据周期计算刷新间隔，通常为周期的 1/10 或最小1秒
  switch (unit) {
    case 's': return Math.max(1000, num * 100) // 秒，每 1/10 周期刷新
    case 'm': return Math.max(1000, num * 60 * 100) // 分钟
    case 'h': return Math.max(5000, num * 60 * 60 * 100) // 小时
    case 'd': return Math.max(60000, num * 24 * 60 * 60 * 100) // 天
    case 'w': return 5 * 60 * 1000 // 周，每5分钟
    case 'M': return 10 * 60 * 1000 // 月，每10分钟
    default: return 5000
  }
})

const normalizeTime = (time: Time | undefined): number | null => {
  if (time === undefined || time === null) return null
  if (typeof time === 'number') return time
  if (typeof time === 'string') {
    const parsed = Date.parse(time)
    return Number.isNaN(parsed) ? null : Math.floor(parsed / 1000)
  }
  if (typeof time === 'object' && 'year' in time && 'month' in time && 'day' in time) {
    return Math.floor(Date.UTC(time.year, time.month - 1, time.day) / 1000)
  }
  return null
}

const findCandleByTime = (timestamp: number | null): Candle | null => {
  if (timestamp === null) return null
  const target = allCandles.value.find(item => Math.trunc(item.time) === Math.trunc(timestamp))
  return target ?? null
}

let highlightSeries: ISeriesApi<'Candlestick'> | null = null
let highlightSeriesChart: IChartApi | null = null

const disposeHighlightSeries = (): void => {
  if (highlightSeries && highlightSeriesChart) {
    try {
      highlightSeriesChart.removeSeries(highlightSeries)
    // eslint-disable-next-line no-empty
    } catch {}
  }
  highlightSeries = null
  highlightSeriesChart = null
}

const ensureHighlightSeries = (): ISeriesApi<'Candlestick'> | null => {
  if (!chart.value || isTimelineMode.value) return null

  if (highlightSeries && highlightSeriesChart === chart.value) {
    return highlightSeries
  }

  if (highlightSeries && highlightSeriesChart !== chart.value) {
    disposeHighlightSeries()
  }

  const series = chart.value.addCandlestickSeries({
    upColor: 'rgba(255, 255, 255, 0.22)',
    downColor: 'rgba(255, 255, 255, 0.22)',
    borderUpColor: '#ffffff',
    borderDownColor: '#ffffff',
    wickUpColor: '#ffffff',
    wickDownColor: '#ffffff',
    lastValueVisible: false,
    priceLineVisible: false,
    priceScaleId: 'right'
  })

  highlightSeries = series
  highlightSeriesChart = chart.value

  return series
}

const clearHighlightData = (): void => {
  if (highlightSeries) {
    try {
      highlightSeries.setData([])
    // eslint-disable-next-line no-empty
    } catch {}
  }
}

const applyHighlight = (): void => {
  if (!lockedCandle.value || !candleSeries.value || isTimelineMode.value || !chart.value) {
    clearHighlightData()
    return
  }

  const series = ensureHighlightSeries()
  if (!series) return

  const candle = lockedCandle.value
  const data: CandlestickData = {
    time: candle.time as UTCTimestamp,
    open: candle.open,
    high: candle.high,
    low: candle.low,
    close: candle.close
  }

  series.setData([data])
}

const resetSelection = (): void => {
  hoveredCandle.value = null
  lockedCandle.value = null
  tooltipData.value = null
  clearHighlightData()
}

watch(allCandles, () => {
  if (!lockedCandle.value) return
  const candidate = findCandleByTime(lockedCandle.value.time)
  if (!candidate) {
    resetSelection()
  } else if (candidate !== lockedCandle.value) {
    lockedCandle.value = candidate
  } else {
    applyHighlight()
  }
})

watch(lockedCandle, () => {
  applyHighlight()
})

const handleCrosshairMove = (param: MouseEventParams | undefined): void => {
  if (!param || isTimelineMode.value || !candleSeries.value) {
    if (!lockedCandle.value) {
      hoveredCandle.value = null
      refreshTooltipData()
    }
    return
  }

  if (!param.time || param.point === undefined) {
    hoveredCandle.value = null
    if (!lockedCandle.value) refreshTooltipData()
    return
  }

  const timestamp = normalizeTime(param.time as Time | undefined)
  const candle = findCandleByTime(timestamp)
  hoveredCandle.value = candle
  if (!lockedCandle.value) {
    refreshTooltipData()
  }
}

const handleChartClick = (param: MouseEventParams): void => {
  if (!param || isTimelineMode.value || currentTool.value !== 'cursor' || !candleSeries.value) return

  const timestamp = normalizeTime(param.time as Time | undefined)
  const candle = findCandleByTime(timestamp)

  if (!candle) {
    if (lockedCandle.value) {
      lockedCandle.value = null
    }
    return
  }

  if (lockedCandle.value && lockedCandle.value.time === candle.time) {
    lockedCandle.value = null
  } else {
    lockedCandle.value = candle
  }
}

let interactionsCleanup: (() => void) | null = null

const setupChartInteractions = (): void => {
  if (interactionsCleanup) {
    interactionsCleanup()
    interactionsCleanup = null
  }

  if (!chart.value) return

  const chartInstance = chart.value
  chartInstance.subscribeCrosshairMove(handleCrosshairMove as any)
  chartInstance.subscribeClick(handleChartClick)
  interactionsCleanup = () => {
    chartInstance.unsubscribeCrosshairMove(handleCrosshairMove as any)
    chartInstance.unsubscribeClick(handleChartClick)
  }
}

watch(chart, () => {
  disposeHighlightSeries()
  setupChartInteractions()
  applyHighlight()
}, { immediate: true })

watch(isTimelineMode, (value) => {
  if (value) {
    resetSelection()
    disposeHighlightSeries()
  } else {
    applyHighlight()
  }
})

// Methods
const retryLoad = (): void => {
  chartError.value.show = false
  chartRetryLoad()
}

const toggleAutoRefresh = (): void => {
  autoRefreshEnabled.value = !autoRefreshEnabled.value
}

const startAutoRefresh = (): void => {
  if (autoRefreshTimer.value) {
    clearInterval(autoRefreshTimer.value)
  }
  
  if (autoRefreshEnabled.value) {
    autoRefreshTimer.value = window.setInterval(async () => {
      if (autoRefreshEnabled.value && !isLoading.value) {
        await updateLatestData()
      }
    }, getRefreshInterval.value)
  }
}

const stopAutoRefresh = (): void => {
  if (autoRefreshTimer.value) {
    clearInterval(autoRefreshTimer.value)
    autoRefreshTimer.value = null
  }
}

const jumpToLatest = (): void => {
  if (chart.value) {
    chart.value.timeScale().scrollToRealTime()
  }
}

// Watch for symbol and bar changes to emit events
watch(symbol, (newSymbol) => {
  resetSelection()
  emit('symbol-change', newSymbol)
  // 切换币对时停止自动刷新，重新初始化图表并加载数据
  stopAutoRefresh()
  initChart()
  loadCandlesticks().then(() => {
    // 数据加载完成后重新启动自动刷新
    if (autoRefreshEnabled.value) {
      startAutoRefresh()
    }
  })
})

watch(bar, (newBar) => {
  resetSelection()
  emit('bar-change', newBar)
  // 切换周期时停止自动刷新，重新初始化图表并加载数据
  stopAutoRefresh()
  initChart()
  loadCandlesticks().then(() => {
    // 数据加载完成后重新启动自动刷新
    if (autoRefreshEnabled.value) {
      startAutoRefresh()
    }
  })
})

// Watch for source changes to reload data
watch(source, () => {
  resetSelection()
  stopAutoRefresh()
  initChart()
  loadCandlesticks().then(() => {
    if (autoRefreshEnabled.value) {
      startAutoRefresh()
    }
  })
})

// Watch for auto refresh toggle
watch(autoRefreshEnabled, (enabled) => {
  if (enabled) {
    startAutoRefresh()
  } else {
    stopAutoRefresh()
  }
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
  // Load initial source data to set available timeframes and symbols
  try {
    const response = await fetch('/api/sources/')
    const data = await response.json()
    if (data.code === 0 && data.data && data.data[source.value]) {
      const sourceInfo = data.data[source.value]
      if (sourceInfo.capability.candlestick_granularities) {
        availableTimeframes.value = sourceInfo.capability.candlestick_granularities
      }
      if (sourceInfo.capability.supported_symbols && sourceInfo.capability.supported_symbols.length > 0) {
        availableSymbols.value = sourceInfo.capability.supported_symbols
      }
    }
  } catch (e) {
    console.error('Failed to load initial source data:', e)
  }
  
  // Initialize chart with auto-refresh
  await initialize()
  loadCandlesticks()
  startAutoRefresh()
  
  // Trigger indicator calculations after data is loaded
  if (allCandles.value.length > 0) {
    triggerWorkerCalculation()
  }
})

onUnmounted(() => {
  cleanupIndicators()
  stopAutoRefresh()
  resetSelection()
  if (interactionsCleanup) {
    interactionsCleanup()
    interactionsCleanup = null
  }
  disposeHighlightSeries()
})
</script>

<style scoped>
.kline-chart-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--bg-primary);
}

.chart-toolbar {
  display: flex;
  flex-direction: column;
  padding: 0;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
}

.toolbar-info-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 16px 24px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-color);
}

.toolbar-controls-row {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 10px 16px;
  flex-wrap: wrap;
}

.controls-group {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 12px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  transition: all 0.2s;
}

.controls-group:hover {
  border-color: rgba(41, 98, 255, 0.3);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.group-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  padding-right: 4px;
}

.divider-vertical {
  width: 1px;
  height: 20px;
  background: var(--border-color);
}

.actions-group {
  margin-left: auto;
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: transparent;
  border: none;
  border-radius: 4px;
  color: var(--text-primary);
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  transition: all 0.2s;
}

.action-btn .icon {
  flex-shrink: 0;
}

.action-btn:hover {
  background: rgba(41, 98, 255, 0.1);
  color: var(--blue-accent);
}

.action-btn.active {
  background: rgba(38, 166, 154, 0.15);
  color: #26a69a;
}

.action-btn.refresh-btn.active:hover {
  background: rgba(38, 166, 154, 0.25);
}

.toolbar-info-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 16px 24px;
  width: 100%;
}

.toolbar-info-row .info-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 100px;
  flex: 0 0 auto;
}

.toolbar-info-row .value.pair-value {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.pair-base {
  color: var(--text-primary);
  font-size: 18px;
  font-weight: 700;
}

.pair-quote {
  color: var(--text-secondary);
  font-size: 18px;
  font-weight: 700;
}

.divider {
  color: var(--text-secondary);
  font-size: 18px;
}

.source-tag {
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(41, 98, 255, 0.15);
  color: var(--blue-accent);
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
}

.toolbar-info-row .label {
  color: var(--text-secondary);
  font-size: 13px;
}

.toolbar-info-row .value {
  font-weight: 700;
  font-size: 18px;
  color: var(--text-primary);
}

.toolbar-info-row .value.up {
  color: var(--up-color);
}

.toolbar-info-row .value.down {
  color: var(--down-color);
}

.toolbar-controls {
  display: none; /* Hide old controls */
}

.refresh-btn {
  /* Keep old styles for backward compatibility but they won't be used */
  padding: 6px 12px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  color: var(--text-primary);
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
  height: 36px;
}

.refresh-btn:hover {
  background: rgba(41, 98, 255, 0.15);
  border-color: var(--blue-accent);
}

.refresh-btn.active {
  background: rgba(41, 98, 255, 0.2);
  border-color: var(--blue-accent);
  color: var(--blue-accent);
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
  overflow: visible; /* Ensure axis labels are not clipped */
}

.jump-to-latest-btn {
  position: absolute;
  top: 10px;
  right: 70px;
  z-index: 10;
  width: 32px;
  height: 32px;
  padding: 0;
  background: rgba(42, 46, 57, 0.9);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  color: var(--text-primary);
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.jump-to-latest-btn:hover {
  background: rgba(41, 98, 255, 0.2);
  border-color: var(--blue-accent);
  color: var(--blue-accent);
  transform: translateX(2px);
}

.drawing-canvas {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 5;
  pointer-events: none;
}

.chart-wrapper {
  width: 100%;
  height: 100%;
  position: relative;
  z-index: 2; /* Put chart canvas above overlay canvases */
  overflow: visible; /* Allow price axis labels to render fully */
}

.main-chart-legends {
  position: absolute;
  top: 8px;
  left: 200px;
  z-index: 15;
  display: flex;
  flex-direction: row;
  gap: 20px;
  max-width: calc(100% - 220px);
  background: rgba(19, 23, 34, 0.75);
  padding: 8px 14px;
  border-radius: 4px;
  backdrop-filter: blur(4px);
  font-size: 12px;
  font-weight: 500;
  pointer-events: none;
  user-select: none;
}

.legend-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.legend-item {
  display: block;
  font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
  text-shadow: 0 0 2px rgba(0, 0, 0, 0.8);
  white-space: nowrap;
  line-height: 1.4;
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
