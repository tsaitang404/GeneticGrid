<template>
  <section class="trading-tools-panel">
    <div class="tools-tabs">
      <button 
        :class="['tab-btn', { active: activeTab === 'position' }]"
        @click="activeTab = 'position'"
      >
        📊 仓位管理
      </button>
      <button 
        :class="['tab-btn', { active: activeTab === 'grid' }]"
        @click="activeTab = 'grid'"
      >
        🧱 网格交易
      </button>
    </div>

    <!-- 仓位管理标签页 -->
    <div v-show="activeTab === 'position'" class="tab-content">
      <!-- 未登陆：引导登陆 -->
      <div v-if="!isLoggedIn" class="login-prompt">
        <div class="prompt-icon">🔑</div>
        <div class="prompt-text">请先登陆以查看仓位信息</div>
        <button class="btn primary" @click="$emit('open-account')">前往登陆</button>
      </div>

      <!-- 已登陆：仓位管理 -->
      <template v-else>
        <div class="position-toolbar">
          <div class="position-section">
            <h4>持有仓位</h4>
            <span v-if="filteredPositions.length" class="total-count">
              共 {{ filteredPositions.length }} 个
            </span>
          </div>
          <div class="toolbar-actions">
            <div class="search-box">
              <input
                v-model="filterSymbol"
                placeholder="搜索币对"
                class="search-input"
              />
            </div>
            <button class="refresh-btn" :disabled="posLoading" @click="loadPositions">
              {{ posLoading ? '加载中...' : '🔄 刷新' }}
            </button>
          </div>
        </div>

        <!-- 汇总 -->
        <div v-if="filteredPositions.length" class="summary-bar">
          <div class="summary-item">
            <span class="label">总名义价值</span>
            <span class="value">${{ totalNotional }}</span>
          </div>
          <div class="summary-item">
            <span class="label">总未实现盈亏</span>
            <span :class="['value', totalUnrealizedPnl >= 0 ? 'profit' : 'loss']">
              {{ totalUnrealizedPnl >= 0 ? '+' : '' }}{{ totalUnrealizedPnl }}
            </span>
          </div>
          <div class="summary-item">
            <span class="label">多头</span>
            <span class="value long-count">{{ longCount }}</span>
          </div>
          <div class="summary-item">
            <span class="label">空头</span>
            <span class="value short-count">{{ shortCount }}</span>
          </div>
        </div>

        <!-- 加载状态 -->
        <div v-if="posLoading" class="loading">加载仓位中...</div>
        <div v-else-if="posError" class="error">{{ posError }}</div>

        <!-- 无持仓 -->
        <div v-else-if="filteredPositions.length === 0" class="empty">
          {{ filterSymbol ? '没有匹配的仓位' : '暂无持仓' }}
        </div>

        <!-- 仓位卡片列表 -->
        <div v-else class="position-list">
          <div
            v-for="pos in filteredPositions"
            :key="pos.symbol + '-' + pos.side"
            :class="['position-card', { expanded: expandedSymbol === pos.symbol + '-' + pos.side }]"
            @click="toggleExpand(pos.symbol + '-' + pos.side)"
          >
            <div class="pos-header">
              <div class="pos-title">
                <h5>{{ pos.symbol }}</h5>
                <span :class="['pos-side', pos.side?.toLowerCase()]">{{ pos.side }}</span>
              </div>
              <div class="pos-pnl">
                <span :class="+pos.unrealizedPnl >= 0 ? 'profit' : 'loss'">
                  {{ +pos.unrealizedPnl >= 0 ? '+' : '' }}{{ formatNumber(pos.unrealizedPnl) }}
                </span>
                <span class="pnl-pct" :class="+pos.unrealizedPnl >= 0 ? 'profit' : 'loss'">
                  {{ (+pos.unrealizedPnlRatio * 100).toFixed(2) }}%
                </span>
              </div>
            </div>

            <div class="pos-row">
              <div class="pos-metric">
                <span class="label">数量</span>
                <span class="value">{{ formatNumber(pos.positionQty) }}</span>
              </div>
              <div class="pos-metric">
                <span class="label">标记价格</span>
                <span class="value">${{ formatNumber(pos.markPrice) }}</span>
              </div>
              <div class="pos-metric">
                <span class="label">杠杆</span>
                <span class="value">{{ pos.leverage }}x</span>
              </div>
            </div>

            <!-- 展开详情 -->
            <div v-if="expandedSymbol === pos.symbol + '-' + pos.side" class="pos-details">
              <div class="detail-row">
                <div class="detail-item">
                  <span class="label">名义价值</span>
                  <span class="value">${{ formatNumber(pos.notionalValue) }}</span>
                </div>
                <div class="detail-item">
                  <span class="label">保证金模式</span>
                  <span class="value">{{ pos.mgnMode === 'cross' ? '全仓' : '逐仓' }}</span>
                </div>
              </div>
              <div class="detail-row">
                <div class="detail-item">
                  <span class="label">可平数量</span>
                  <span class="value">{{ formatNumber(pos.available) }}</span>
                </div>
                <div class="detail-item">
                  <span class="label">冻结数量</span>
                  <span class="value frozen">{{ formatNumber(pos.frozenQty) }}</span>
                </div>
              </div>
              <div class="detail-row">
                <div class="detail-item">
                  <span class="label">未实现盈亏率</span>
                  <span :class="['value', +pos.unrealizedPnlRatio >= 0 ? 'profit' : 'loss']">
                    {{ (+pos.unrealizedPnlRatio * 100).toFixed(4) }}%
                  </span>
                </div>
                <div class="detail-item">
                  <span class="label">更新时间</span>
                  <span class="value">{{ formatTime(pos.timestamp) }}</span>
                </div>
              </div>
            </div>

            <div class="pos-expand-hint">
              {{ expandedSymbol === pos.symbol + '-' + pos.side ? '收起' : '查看详情' }}
            </div>
          </div>
        </div>
      </template>
    </div>

    <!-- 网格交易标签页（保持不变） -->
    <div v-show="activeTab === 'grid'" class="tab-content">
      <div class="form-grid">
        <div class="form-group">
          <label>交易对</label>
          <input v-model="gridForm.symbol" placeholder="如 BTCUSDT" />
        </div>
        <div class="form-group">
          <label>网格数量</label>
          <input v-model.number="gridForm.grids" type="number" min="2" max="200" />
        </div>
        <div class="form-group">
          <label>下限价格</label>
          <input v-model.number="gridForm.lower" type="number" min="0" step="0.01" />
        </div>
        <div class="form-group">
          <label>上限价格</label>
          <input v-model.number="gridForm.upper" type="number" min="0" step="0.01" />
        </div>
        <div class="form-group">
          <label>投资金额</label>
          <input v-model.number="gridForm.invest" type="number" min="0" step="0.01" />
        </div>
        <div class="form-group">
          <label>风格</label>
          <select v-model="gridForm.mode">
            <option value="arithmetic">等差</option>
            <option value="geometric">等比</option>
          </select>
        </div>
      </div>

      <div class="preview-info">
        <div class="preview-item">
          <span>预计每网格资金</span>
          <b>{{ gridFund.toFixed(4) }}</b>
        </div>
        <div class="preview-item">
          <span>预计价格步长</span>
          <b>{{ stepPreview }}</b>
        </div>
      </div>

      <div class="form-actions">
        <button class="btn primary" @click="createGrid">创建网格</button>
      </div>
      <p class="tip">💡 当前为原型占位，不会触发真实交易</p>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, onMounted, onUnmounted } from 'vue'
import { useAuth } from '../../composables/useAuth'

const emit = defineEmits<{ (e: 'open-account'): void }>()

const {
  positions,
  error: authError,
  isLoggedIn,
  fetchPositions,
} = useAuth()

const activeTab = ref<'position' | 'grid'>('position')
const posLoading = ref(false)
const posError = ref('')
const filterSymbol = ref('')
const expandedSymbol = ref<string | null>(null)
let refreshTimer: ReturnType<typeof setInterval> | null = null

// 筛选仓位
const filteredPositions = computed(() => {
  if (!filterSymbol.value) return positions.value
  const q = filterSymbol.value.toUpperCase()
  return positions.value.filter((p: any) => p.symbol.includes(q))
})

// 汇总统计
const totalNotional = computed(() => {
  return filteredPositions.value
    .reduce((s: number, p: any) => s + (parseFloat(p.notionalValue) || 0), 0)
    .toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
})

const totalUnrealizedPnl = computed(() => {
  return filteredPositions.value
    .reduce((s: number, p: any) => s + (parseFloat(p.unrealizedPnl) || 0), 0)
})

const longCount = computed(() => {
  return filteredPositions.value.filter((p: any) => p.side?.toLowerCase() === 'long').length
})

const shortCount = computed(() => {
  return filteredPositions.value.filter((p: any) => p.side?.toLowerCase() === 'short').length
})

// 展开/收起详情
function toggleExpand(key: string): void {
  expandedSymbol.value = expandedSymbol.value === key ? null : key
}

// 加载仓位信息
const loadPositions = async (): Promise<void> => {
  if (!isLoggedIn.value) return
  posLoading.value = true
  posError.value = ''
  await fetchPositions()
  posLoading.value = false
  if (authError.value) {
    posError.value = authError.value
  }
}

// 登陆状态变化时自动加载/清空
watch(isLoggedIn, (loggedIn) => {
  if (loggedIn) {
    posError.value = ''
    loadPositions()
  } else {
    positions.value = []
    posError.value = ''
    filterSymbol.value = ''
    expandedSymbol.value = null
  }
})

// 格式化数字
const formatNumber = (num: number | string): string => {
  const n = typeof num === 'string' ? parseFloat(num) : num
  if (!n || isNaN(n)) return '-'
  if (Math.abs(n) >= 1000000) {
    return (n / 1000000).toFixed(2) + 'M'
  }
  if (Math.abs(n) >= 1000) {
    return (n / 1000).toFixed(2) + 'K'
  }
  return n.toFixed(Math.abs(n) < 1 ? 6 : 2)
}

const formatTime = (ts: string | number): string => {
  if (!ts) return '-'
  const n = typeof ts === 'string' ? parseInt(ts) : ts
  const d = new Date(n)
  return d.toLocaleString('zh-CN', { hour12: false })
}

const gridForm = reactive({
  symbol: 'BTCUSDT',
  grids: 20,
  lower: 50000,
  upper: 60000,
  invest: 1000,
  mode: 'arithmetic' as 'arithmetic' | 'geometric',
})

const gridFund = computed(() => {
  if (gridForm.grids <= 0) return 0
  return gridForm.invest / gridForm.grids
})

const stepPreview = computed(() => {
  const g = Math.max(2, gridForm.grids)
  if (gridForm.mode === 'arithmetic') {
    const step = (gridForm.upper - gridForm.lower) / (g - 1)
    return step > 0 ? step.toFixed(2) : '-'
  } else {
    if (gridForm.lower <= 0 || gridForm.upper <= 0) return '-'
    const ratio = Math.pow(gridForm.upper / gridForm.lower, 1 / (g - 1))
    return ratio > 0 ? ratio.toFixed(4) + 'x' : '-'
  }
})

const createGrid = (): void => {
  console.log('[GridTrading] create', { ...gridForm })
}

onMounted(() => {
  if (isLoggedIn.value) {
    loadPositions()
  }
})

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer)
})
</script>

<style scoped>
.trading-tools-panel {
  background: #1e222d;
  border: 1px solid #2a2e39;
  border-radius: 8px;
  overflow: hidden;
}

.tools-tabs {
  display: flex;
  background: #12151c;
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
  background: rgba(255, 255, 255, 0.03);
}

.tab-btn.active {
  color: #2962ff;
  border-bottom-color: #2962ff;
}

.tab-content {
  padding: 16px;
  max-height: calc(100vh - 300px);
  overflow-y: auto;
}

.position-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  flex-wrap: wrap;
  gap: 8px;
}

.position-section {
  display: flex;
  align-items: center;
  gap: 8px;
}

.position-section h4 {
  margin: 0;
  font-size: 14px;
  color: #d1d4dc;
}

.total-count {
  font-size: 12px;
  color: #787b86;
  background: #202534;
  padding: 2px 8px;
  border-radius: 10px;
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.search-box {
  position: relative;
}

.search-input {
  width: 140px;
  height: 32px;
  background: #1b202b;
  border: 1px solid #2a2e39;
  color: #d1d4dc;
  border-radius: 6px;
  padding: 0 10px;
  font-size: 12px;
  outline: none;
  transition: border-color 0.2s;
}

.search-input:focus {
  border-color: #2962ff;
}

.search-input::placeholder {
  color: #5a5e6b;
}

.refresh-btn {
  height: 32px;
  padding: 0 12px;
  border-radius: 6px;
  border: 1px solid #2a2e39;
  background: #202534;
  color: #d1d4dc;
  cursor: pointer;
  font-size: 12px;
  transition: all 0.2s;
  white-space: nowrap;
}

.refresh-btn:hover:not(:disabled) {
  background: #23283a;
  border-color: #2f3b52;
}

.refresh-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 未登陆提示 */
.login-prompt {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 20px;
  gap: 12px;
}

.prompt-icon {
  font-size: 40px;
  line-height: 1;
}

.prompt-text {
  font-size: 14px;
  color: #8b90a0;
}

/* 汇总栏 */
.summary-bar {
  display: flex;
  gap: 16px;
  padding: 10px 12px;
  background: #161a23;
  border: 1px solid #2a2e39;
  border-radius: 6px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.summary-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: 12px;
}

.summary-item .label {
  color: #787b86;
}

.summary-item .value {
  color: #d1d4dc;
  font-weight: 600;
}

.long-count { color: #4caf50 !important; }
.short-count { color: #f44336 !important; }

.loading,
.error,
.empty {
  padding: 20px;
  text-align: center;
  font-size: 13px;
  color: #8b90a0;
}

.error {
  color: #ff6b6b;
}

/* 仓位列表 */
.position-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 10px;
  margin-bottom: 16px;
}

.position-card {
  background: #161a23;
  border: 1px solid #2a2e39;
  border-radius: 8px;
  padding: 12px;
  cursor: pointer;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.position-card:hover {
  border-color: #3a3e49;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.3);
}

.position-card.expanded {
  border-color: #2962ff;
}

.pos-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 10px;
}

.pos-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.pos-title h5 {
  margin: 0;
  font-size: 14px;
  color: #e0e2e8;
  font-weight: 600;
}

.pos-side {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 600;
}

.pos-side.long { background: rgba(76, 175, 80, 0.15); color: #4caf50; }
.pos-side.short { background: rgba(244, 67, 54, 0.15); color: #f44336; }

.pos-pnl {
  text-align: right;
  display: flex;
  flex-direction: column;
  gap: 1px;
  font-size: 13px;
  font-weight: 600;
}

.pnl-pct {
  font-size: 11px;
  font-weight: 400;
}

.profit { color: #4caf50; }
.loss { color: #f44336; }

.pos-row {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

.pos-metric {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: 12px;
}

.pos-metric .label {
  color: #787b86;
  font-size: 11px;
}

.pos-metric .value {
  color: #d1d4dc;
  font-weight: 500;
}

/* 展开详情 */
.pos-details {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid #2a2e39;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.detail-row {
  display: flex;
  gap: 20px;
  font-size: 12px;
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 100px;
}

.detail-item .label {
  color: #787b86;
  font-size: 11px;
}

.detail-item .value {
  color: #d1d4dc;
  font-weight: 500;
}

.detail-item .value.frozen { color: #ff9800; }

.pos-expand-hint {
  margin-top: 8px;
  font-size: 11px;
  color: #2962ff;
  text-align: center;
}

hr {
  border: none;
  border-top: 1px solid #2a2e39;
  margin: 16px 0;
}

.form-title {
  font-size: 13px;
  color: #d1d4dc;
  margin-bottom: 12px;
  font-weight: 500;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
  margin-bottom: 12px;
}

.form-group {
  display: grid;
  gap: 6px;
}

.form-group label {
  font-size: 12px;
  color: #9aa3b2;
}

.form-group input,
.form-group select {
  background: #1b202b;
  border: 1px solid #2a2e39;
  color: #d1d4dc;
  height: 36px;
  border-radius: 6px;
  padding: 0 10px;
  font-size: 13px;
}

.form-group input:focus,
.form-group select:focus {
  outline: none;
  border-color: #2962ff;
  box-shadow: 0 0 0 2px rgba(41, 98, 255, 0.1);
}

.preview-info {
  background: #161a23;
  border: 1px dashed #2a2e39;
  border-radius: 6px;
  padding: 10px;
  margin-bottom: 12px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.preview-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
}

.preview-item span {
  color: #8b90a0;
}

.preview-item b {
  color: #2962ff;
  font-weight: 600;
}

.form-actions {
  display: flex;
  gap: 8px;
}

.btn {
  height: 36px;
  padding: 0 16px;
  border-radius: 6px;
  border: 1px solid #2a2e39;
  background: #202534;
  color: #d1d4dc;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
}

.btn:hover {
  background: #23283a;
  border-color: #2f3b52;
}

.btn.primary {
  background: #2962ff;
  border-color: #2962ff;
  color: white;
}

.btn.primary:hover {
  background: #1e53e5;
  border-color: #1e53e5;
}

.btn.secondary {
  background: transparent;
  border-color: #2a2e39;
}

.btn.secondary:hover {
  background: rgba(255, 255, 255, 0.03);
}

.tip {
  margin-top: 10px;
  font-size: 12px;
  color: #7f8694;
}
</style>
