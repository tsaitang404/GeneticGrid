<template>
  <div class="contract-basis-panel">
    <!-- 当前基差信息 -->
    <div class="current-basis-section">
      <div class="basis-header">
        <h3>当前合约基差</h3>
        <span class="update-time" v-if="basisData?.timestamp">
          {{ formatTime(basisData.timestamp) }}
        </span>
      </div>

      <div class="basis-display">
        <div class="main-basis" :class="basisClass">
          {{ formattedBasis }}
        </div>
        <div class="basis-rate" :class="basisClass">
          {{ formattedBasisRate }}
        </div>
        <div class="price-info">
          <div class="price-item">
            <span class="label">合约价格</span>
            <span class="value">{{ formatPrice(basisData?.contract_price) }}</span>
          </div>
          <div class="price-item">
            <span class="label">现货价格</span>
            <span class="value">{{ formatPrice(basisData?.reference_price) }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 历史基差图表 -->
    <div class="chart-section">
      <div class="chart-header">
        <h3>历史基差走势</h3>
        <div class="granularity-selector">
          <button 
            v-for="gran in granularities" 
            :key="gran.value"
            :class="['granularity-btn', { active: selectedGranularity === gran.value }]"
            @click="selectedGranularity = gran.value"
          >
            {{ gran.label }}
          </button>
        </div>
      </div>
      
      <div class="chart-container">
        <div v-if="chartLoading" class="chart-loading">
          <div class="spinner"></div>
        </div>
        <div v-else-if="chartError" class="chart-error">
          <p>{{ chartError }}</p>
          <button @click="loadHistory" class="retry-btn">重试</button>
        </div>
        <canvas v-else ref="chartCanvas" class="basis-chart"></canvas>
      </div>
    </div>

    <!-- 市场分析 -->
    <div class="analysis-section" v-if="basisData">
      <h4>市场状态</h4>
      <div class="market-state" :class="marketStateClass">
        {{ marketStateText }}
      </div>
      <p class="analysis-desc">{{ analysisDescription }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { Chart, ChartConfiguration } from 'chart.js/auto'

interface ContractBasisData {
  basis: number
  basis_rate: number
  contract_price: number
  reference_price: number
  timestamp: number
}

interface Props {
  symbol: string
  source: string
  basisData: ContractBasisData | null
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

const formattedBasis = computed(() => {
  if (!props.basisData) return '--'
  const basis = props.basisData.basis
  return basis >= 0 ? `+${basis.toFixed(2)}` : `${basis.toFixed(2)}`
})

const formattedBasisRate = computed(() => {
  if (!props.basisData) return '--'
  const rate = props.basisData.basis_rate
  return rate >= 0 ? `+${rate.toFixed(3)}%` : `${rate.toFixed(3)}%`
})

const basisClass = computed(() => {
  if (!props.basisData) return ''
  return props.basisData.basis > 0 ? 'premium' : 'discount'
})

const marketStateClass = computed(() => {
  if (!props.basisData) return ''
  return props.basisData.basis > 0 ? 'premium' : 'discount'
})

const marketStateText = computed(() => {
  if (!props.basisData) return '数据加载中'
  const basis = props.basisData.basis
  if (Math.abs(basis) < 1) return '价差极小'
  return basis > 0 ? '合约溢价' : '合约折价'
})

const analysisDescription = computed(() => {
  if (!props.basisData) return ''
  const basis = props.basisData.basis
  const rate = Math.abs(props.basisData.basis_rate)
  
  if (Math.abs(basis) < 1) {
    return '合约价格与现货价格接近，市场较为均衡'
  } else if (basis > 0) {
    if (rate > 0.5) {
      return '合约显著溢价，市场情绪偏乐观，可能存在反向套利机会'
    } else {
      return '合约轻微溢价，属于正常市场状态'
    }
  } else {
    if (rate > 0.5) {
      return '合约显著折价，市场情绪偏悲观，可能存在正向套利机会'
    } else {
      return '合约轻微折价，属于正常市场波动'
    }
  }
})

function formatTime(timestamp: number): string {
  const date = new Date(timestamp * 1000)
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

function formatPrice(price: number | undefined): string {
  if (!price) return '--'
  return price.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

async function loadHistory() {
  chartLoading.value = true
  chartError.value = ''
  
  try {
    // 根据粒度计算limit：1m=1440条(1天), 5m=8640条(30天), 1h=720条(30天), 1d=30条(30天)
    const limit = selectedGranularity.value === '1m' ? 1440 : 
                  selectedGranularity.value === '5m' ? 8640 :
                  selectedGranularity.value === '1h' ? 720 : 30
    
    const response = await fetch(
      `/api/contract-basis/history/?symbol=${props.symbol}&source=${props.source}&contract_type=perpetual&limit=${limit}&granularity=${selectedGranularity.value}`
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
    console.error('Failed to load basis history:', error)
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
    return date.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
  })
  
  const basisData = historyData.value.map(item => item.basis)
  const basisRateData = historyData.value.map(item => item.basis_rate)
  
  const config: ChartConfiguration = {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: '基差',
          data: basisData,
          borderColor: '#2962ff',
          backgroundColor: 'rgba(41, 98, 255, 0.1)',
          borderWidth: 2,
          pointRadius: 0,
          pointHoverRadius: 4,
          fill: true,
          tension: 0.4,
          yAxisID: 'y'
        },
        {
          label: '基差率 (%)',
          data: basisRateData,
          borderColor: '#f7931a',
          backgroundColor: 'rgba(247, 147, 26, 0.1)',
          borderWidth: 2,
          pointRadius: 0,
          pointHoverRadius: 4,
          fill: false,
          tension: 0.4,
          yAxisID: 'y1'
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: true,
          position: 'top',
          labels: {
            color: '#d1d4dc',
            font: {
              size: 12
            },
            usePointStyle: true,
            padding: 15
          }
        },
        tooltip: {
          mode: 'index',
          intersect: false,
          callbacks: {
            label: (context) => {
              const label = context.dataset.label || ''
              const value = context.parsed.y
              if (value == null) return 'N/A'
              if (label.includes('率')) {
                return `${label}: ${value.toFixed(3)}%`
              } else {
                return `${label}: ${value >= 0 ? '+' : ''}${value.toFixed(2)}`
              }
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
          type: 'linear',
          display: true,
          position: 'left',
          grid: {
            color: 'rgba(42, 46, 57, 0.5)'
          },
          ticks: {
            color: '#2962ff',
            callback: (value) => {
              const num = Number(value)
              return num >= 0 ? `+${num.toFixed(0)}` : `${num.toFixed(0)}`
            }
          },
          title: {
            display: true,
            text: '基差',
            color: '#2962ff'
          }
        },
        y1: {
          type: 'linear',
          display: true,
          position: 'right',
          grid: {
            drawOnChartArea: false
          },
          ticks: {
            color: '#f7931a',
            callback: (value) => `${value}%`
          },
          title: {
            display: true,
            text: '基差率 (%)',
            color: '#f7931a'
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

// 监听粒度变化
watch(selectedGranularity, () => {
  if (props.symbol && props.source) {
    loadHistory()
  }
})

// 监听symbol和source变化
watch([() => props.symbol, () => props.source], () => {
  if (props.symbol && props.source) {
    loadHistory()
  }
})
</script>

<style scoped>
.contract-basis-panel {
  padding: 20px;
  background: #1e222d;
  color: #d1d4dc;
  overflow-y: auto;
  max-height: 100%;
}

.current-basis-section {
  margin-bottom: 20px;
}

.basis-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.basis-header h3 {
  font-size: 16px;
  font-weight: 600;
  margin: 0;
}

.update-time {
  font-size: 12px;
  color: #787b86;
}

.basis-display {
  background: #131722;
  border-radius: 8px;
  padding: 16px;
}

.main-basis {
  font-size: 32px;
  font-weight: 700;
  margin-bottom: 4px;
}

.basis-rate {
  font-size: 18px;
  font-weight: 500;
  margin-bottom: 16px;
}

.main-basis.premium,
.basis-rate.premium {
  color: #089981;
}

.main-basis.discount,
.basis-rate.discount {
  color: #f23645;
}

.price-info {
  display: flex;
  gap: 24px;
  padding-top: 12px;
  border-top: 1px solid #2a2e39;
}

.price-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.price-item .label {
  font-size: 12px;
  color: #787b86;
}

.price-item .value {
  font-size: 14px;
  font-weight: 500;
}

.chart-section {
  margin-bottom: 20px;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.chart-header h3 {
  font-size: 16px;
  font-weight: 600;
  margin: 0;
}

.granularity-selector {
  display: flex;
  gap: 6px;
}

.granularity-btn {
  padding: 4px 12px;
  border: 1px solid #363a45;
  background: #2a2e39;
  color: #787b86;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  transition: all 0.2s;
}

.granularity-btn:hover {
  background: #363a45;
  color: #d1d4dc;
}

.granularity-btn.active {
  background: #2962ff;
  color: #ffffff;
  border-color: #2962ff;
}

.chart-info {
  font-size: 12px;
  color: #787b86;
}

.chart-container {
  position: relative;
  height: 300px;
  background: #131722;
  border-radius: 8px;
  padding: 16px;
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

.basis-chart {
  width: 100% !important;
  height: 100% !important;
}

.analysis-section {
  background: #131722;
  border-radius: 8px;
  padding: 16px;
}

.analysis-section h4 {
  font-size: 14px;
  font-weight: 600;
  margin: 0 0 12px 0;
}

.market-state {
  display: inline-block;
  padding: 6px 12px;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 500;
  margin-bottom: 8px;
}

.market-state.premium {
  background: rgba(8, 153, 129, 0.1);
  color: #089981;
}

.market-state.discount {
  background: rgba(242, 54, 69, 0.1);
  color: #f23645;
}

.analysis-desc {
  font-size: 13px;
  color: #787b86;
  margin: 0;
  line-height: 1.5;
}
</style>
