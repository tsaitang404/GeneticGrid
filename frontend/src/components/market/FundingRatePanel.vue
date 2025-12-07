<template>
  <div class="funding-rate-panel">
    <!-- 当前费率信息 -->
    <div class="current-rate-section">
      <div class="rate-header">
        <h3>当前资金费率</h3>
        <span class="update-time" v-if="fundingData?.timestamp">
          {{ formatTime(fundingData.timestamp) }}
        </span>
      </div>

      <div class="rate-display">
        <div class="main-rate" :class="rateClass">
          {{ formattedRate }}
        </div>
        <div class="rate-info">
          <div class="info-item">
            <span class="label">下次结算</span>
            <span class="value">{{ nextSettlement }}</span>
          </div>
          <div class="info-item">
            <span class="label">周期</span>
            <span class="value">{{ fundingInterval }}小时</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 粒度选择器 -->
    <div class="chart-controls">
      <div class="granularity-tabs">
        <button
          v-for="g in granularities"
          :key="g.value"
          :class="['granularity-btn', { active: selectedGranularity === g.value }]"
          @click="changeGranularity(g.value)"
        >
          {{ g.label }}
        </button>
      </div>
    </div>

    <!-- 历史费率图表 -->
    <div class="chart-container">
      <div v-if="chartLoading" class="chart-loading">
        <div class="spinner"></div>
      </div>
      <div v-else-if="chartError" class="chart-error">
        <p>{{ chartError }}</p>
        <button @click="loadHistory" class="retry-btn">重试</button>
      </div>
      <canvas v-else ref="chartCanvas" class="rate-chart"></canvas>
    </div>

    <!-- 市场情绪 -->
    <div class="sentiment-section" v-if="fundingData">
      <h4>市场情绪</h4>
      <div class="sentiment-indicator" :class="sentimentClass">
        {{ sentimentText }}
      </div>
      <p class="sentiment-desc">{{ sentimentDescription }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { Chart, ChartConfiguration } from 'chart.js/auto'

interface FundingRateData {
  funding_rate: number
  predicted_funding_rate?: number | null
  funding_interval_hours: number
  next_funding_time: number
  timestamp: number
}

interface Props {
  symbol: string
  source: string
  fundingData: FundingRateData | null
  loading: boolean
  error: string
}

const props = defineProps<Props>()

const selectedGranularity = ref('1h')
const chartLoading = ref(false)
const chartError = ref('')
const historyData = ref<any[]>([])
const chartCanvas = ref<HTMLCanvasElement | null>(null)
let chartInstance: Chart | null = null

const granularities = [
  { value: '1m', label: '1分钟', interval: 60 },
  { value: '5m', label: '5分钟', interval: 300 },
  { value: '1h', label: '1小时', interval: 3600 },
  { value: '1d', label: '1天', interval: 86400 }
]

const formattedRate = computed(() => {
  if (!props.fundingData) return '--'
  const rate = props.fundingData.funding_rate * 100
  return rate >= 0 ? `+${rate.toFixed(4)}%` : `${rate.toFixed(4)}%`
})

const rateClass = computed(() => {
  if (!props.fundingData) return ''
  return props.fundingData.funding_rate > 0 ? 'positive' : 'negative'
})

const fundingInterval = computed(() => {
  return props.fundingData?.funding_interval_hours || 8
})

const nextSettlement = computed(() => {
  if (!props.fundingData?.next_funding_time) return '--'
  const now = Date.now() / 1000
  const diff = props.fundingData.next_funding_time - now
  if (diff <= 0) return '即将结算'
  
  const hours = Math.floor(diff / 3600)
  const minutes = Math.floor((diff % 3600) / 60)
  return `${hours}小时${minutes}分`
})

const sentimentClass = computed(() => {
  if (!props.fundingData) return ''
  const rate = props.fundingData.funding_rate
  if (rate > 0.0001) return 'bullish'
  if (rate < -0.0001) return 'bearish'
  return 'neutral'
})

const sentimentText = computed(() => {
  if (!props.fundingData) return '数据加载中'
  const rate = props.fundingData.funding_rate
  if (rate > 0.0001) return '多头强势'
  if (rate < -0.0001) return '空头强势'
  return '市场平衡'
})

const sentimentDescription = computed(() => {
  if (!props.fundingData) return ''
  const rate = props.fundingData.funding_rate
  if (rate > 0.0001) return '多头需支付费用给空头，市场偏多'
  if (rate < -0.0001) return '空头需支付费用给多头，市场偏空'
  return '多空力量相对均衡'
})

function formatTime(timestamp: number): string {
  const date = new Date(timestamp * 1000)
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

async function loadHistory() {
  chartLoading.value = true
  chartError.value = ''
  
  try {
    const limit = selectedGranularity.value === '1m' ? 60 : 
                  selectedGranularity.value === '5m' ? 288 :
                  selectedGranularity.value === '1h' ? 168 : 30
    
    const response = await fetch(
      `/api/funding-rate/history/?symbol=${props.symbol}&source=${props.source}&limit=${limit}`
    )
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }
    
    const result = await response.json()
    
    if (result.code === 0 && result.data) {
      historyData.value = result.data
      updateChart()
    } else {
      chartError.value = result.error || '获取历史数据失败'
    }
  } catch (error: any) {
    console.error('Failed to load funding rate history:', error)
    chartError.value = error.message || '网络错误'
  } finally {
    chartLoading.value = false
  }
}

function updateChart() {
  if (!chartCanvas.value || !historyData.value.length) return
  
  // 销毁旧图表
  if (chartInstance) {
    chartInstance.destroy()
  }
  
  const ctx = chartCanvas.value.getContext('2d')
  if (!ctx) return
  
  const labels = historyData.value.map(item => {
    const date = new Date(item.timestamp * 1000)
    if (selectedGranularity.value === '1m' || selectedGranularity.value === '5m') {
      return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
    } else if (selectedGranularity.value === '1h') {
      return date.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit' })
    } else {
      return date.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
    }
  })
  
  const data = historyData.value.map(item => item.funding_rate * 100)
  
  const config: ChartConfiguration = {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: '资金费率 (%)',
        data,
        borderColor: '#2962ff',
        backgroundColor: 'rgba(41, 98, 255, 0.1)',
        borderWidth: 2,
        pointRadius: 0,
        pointHoverRadius: 4,
        fill: true,
        tension: 0.4
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: false
        },
        tooltip: {
          mode: 'index',
          intersect: false,
          callbacks: {
            label: (context) => {
              const value = context.parsed.y
              return `费率: ${value >= 0 ? '+' : ''}${value.toFixed(4)}%`
            }
          }
        }
      },
      scales: {
        x: {
          grid: {
            color: 'rgba(42, 46, 57, 0.5)'
          },
          ticks: {
            color: '#787b86',
            maxRotation: 45,
            minRotation: 0
          }
        },
        y: {
          grid: {
            color: 'rgba(42, 46, 57, 0.5)'
          },
          ticks: {
            color: '#787b86',
            callback: (value) => `${value}%`
          }
        }
      },
      interaction: {
        mode: 'nearest',
        axis: 'x',
        intersect: false
      }
    }
  }
  
  chartInstance = new Chart(ctx, config)
}

function changeGranularity(granularity: string) {
  selectedGranularity.value = granularity
  loadHistory()
}

watch(() => [props.symbol, props.source], () => {
  if (props.symbol && props.source) {
    loadHistory()
  }
}, { immediate: false })

onMounted(() => {
  if (props.symbol && props.source) {
    loadHistory()
  }
})

onUnmounted(() => {
  if (chartInstance) {
    chartInstance.destroy()
  }
})
</script>

<style scoped>
.funding-rate-panel {
  padding: 20px;
  background: #1e222d;
  color: #d1d4dc;
  overflow-y: auto;
  max-height: 100%;
}

.current-rate-section {
  margin-bottom: 20px;
}

.rate-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.rate-header h3 {
  font-size: 16px;
  font-weight: 600;
  margin: 0;
}

.update-time {
  font-size: 12px;
  color: #787b86;
}

.rate-display {
  background: #131722;
  border-radius: 8px;
  padding: 16px;
}

.main-rate {
  font-size: 32px;
  font-weight: 700;
  margin-bottom: 12px;
}

.main-rate.positive {
  color: #089981;
}

.main-rate.negative {
  color: #f23645;
}

.rate-info {
  display: flex;
  gap: 24px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-item .label {
  font-size: 12px;
  color: #787b86;
}

.info-item .value {
  font-size: 14px;
  font-weight: 500;
}

.chart-controls {
  margin: 20px 0 12px;
}

.granularity-tabs {
  display: flex;
  gap: 8px;
  background: #131722;
  padding: 4px;
  border-radius: 6px;
}

.granularity-btn {
  flex: 1;
  padding: 8px 12px;
  border: none;
  background: transparent;
  color: #787b86;
  font-size: 13px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
}

.granularity-btn:hover {
  background: #2a2e39;
  color: #d1d4dc;
}

.granularity-btn.active {
  background: #2962ff;
  color: #fff;
}

.chart-container {
  position: relative;
  height: 250px;
  background: #131722;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 20px;
}

.chart-loading,
.chart-error {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  flex-direction: column;
  gap: 12px;
}

.spinner {
  width: 24px;
  height: 24px;
  border: 3px solid #2a2e39;
  border-top-color: #2962ff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.retry-btn {
  padding: 6px 12px;
  background: #2962ff;
  border: none;
  border-radius: 4px;
  color: #fff;
  cursor: pointer;
  font-size: 13px;
}

.retry-btn:hover {
  background: #1e53e5;
}

.rate-chart {
  width: 100% !important;
  height: 100% !important;
}

.sentiment-section {
  background: #131722;
  border-radius: 8px;
  padding: 16px;
}

.sentiment-section h4 {
  font-size: 14px;
  font-weight: 600;
  margin: 0 0 12px 0;
}

.sentiment-indicator {
  display: inline-block;
  padding: 6px 12px;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 500;
  margin-bottom: 8px;
}

.sentiment-indicator.bullish {
  background: rgba(8, 153, 129, 0.1);
  color: #089981;
}

.sentiment-indicator.bearish {
  background: rgba(242, 54, 69, 0.1);
  color: #f23645;
}

.sentiment-indicator.neutral {
  background: rgba(120, 123, 134, 0.1);
  color: #787b86;
}

.sentiment-desc {
  font-size: 13px;
  color: #787b86;
  margin: 0;
  line-height: 1.5;
}
</style>
