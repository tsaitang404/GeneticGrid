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
      <div class="position-section">
        <h4>持有仓位</h4>
        <button class="refresh-btn" :disabled="posLoading" @click="loadPositions">
          {{ posLoading ? '加载中...' : '刷新' }}
        </button>
      </div>

      <!-- 仓位列表 -->
      <div v-if="posLoading" class="loading">加载仓位中...</div>
      <div v-else-if="posError" class="error">{{ posError }}</div>
      <div v-else-if="positions.length === 0" class="empty">暂无持仓</div>
      <div v-else class="position-list">
        <div v-for="pos in positions" :key="pos.symbol" class="position-card">
          <div class="pos-header">
            <h5>{{ pos.symbol }}</h5>
            <span :class="['pos-side', pos.side.toLowerCase()]">{{ pos.side }}</span>
          </div>
          <div class="pos-grid">
            <div class="pos-item">
              <span class="label">数量</span>
              <span class="value">{{ formatNumber(pos.positionQty) }}</span>
            </div>
            <div class="pos-item">
              <span class="label">标记价格</span>
              <span class="value">{{ formatNumber(pos.markPrice) }}</span>
            </div>
            <div class="pos-item">
              <span class="label">名义价值(USD)</span>
              <span class="value">{{ formatNumber(pos.notionalValue) }}</span>
            </div>
            <div class="pos-item">
              <span class="label">杠杆</span>
              <span class="value">{{ pos.leverage }}x</span>
            </div>
            <div class="pos-item">
              <span class="label">未实现盈亏</span>
              <span :class="['value', pos.unrealizedPnl >= 0 ? 'profit' : 'loss']">
                {{ formatNumber(pos.unrealizedPnl) }}
              </span>
            </div>
            <div class="pos-item">
              <span class="label">盈亏率</span>
              <span :class="['value', pos.unrealizedPnlRatio >= 0 ? 'profit' : 'loss']">
                {{ (pos.unrealizedPnlRatio * 100).toFixed(2) }}%
              </span>
            </div>
          </div>
        </div>
      </div>

      <hr>

      <div class="form-title">开平仓</div>
      <div class="form-grid">
        <div class="form-group">
          <label>交易对</label>
          <input v-model="positionForm.symbol" placeholder="如 BTC-USDT">
        </div>
        <div class="form-group">
          <label>方向</label>
          <select v-model="positionForm.side">
            <option value="long">多头</option>
            <option value="short">空头</option>
          </select>
        </div>
        <div class="form-group">
          <label>杠杆</label>
          <input v-model.number="positionForm.leverage" type="number" min="1" max="125">
        </div>
        <div class="form-group">
          <label>数量</label>
          <input v-model.number="positionForm.size" type="number" min="0" step="0.0001">
        </div>
      </div>
      <div class="form-actions">
        <button class="btn primary" @click="openPosition">开仓</button>
        <button class="btn secondary" @click="closePosition">平仓</button>
      </div>
      <p class="tip">💡 当前为原型占位，不会触发真实交易</p>
    </div>

    <!-- 网格交易标签页 -->
    <div v-show="activeTab === 'grid'" class="tab-content">
      <div class="form-grid">
        <div class="form-group">
          <label>交易对</label>
          <input v-model="gridForm.symbol" placeholder="如 BTCUSDT">
        </div>
        <div class="form-group">
          <label>网格数量</label>
          <input v-model.number="gridForm.grids" type="number" min="2" max="200">
        </div>
        <div class="form-group">
          <label>下限价格</label>
          <input v-model.number="gridForm.lower" type="number" min="0" step="0.01">
        </div>
        <div class="form-group">
          <label>上限价格</label>
          <input v-model.number="gridForm.upper" type="number" min="0" step="0.01">
        </div>
        <div class="form-group">
          <label>投资金额</label>
          <input v-model.number="gridForm.invest" type="number" min="0" step="0.01">
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
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { useAuth } from '../../composables/useAuth'

const {
  positions,
  session,
  error: authError,
  isLoggedIn,
  fetchPositions,
} = useAuth()

watch(session, (newVal) => {
  if (!newVal?.authenticated) {
    positions.value = []
    posError.value = ''
  }
})

const activeTab = ref<'position' | 'grid'>('position')

// 仓位管理相关
const posLoading = ref(false)
const posError = ref('')

const positionForm = reactive({
  symbol: 'BTC-USDT',
  side: 'long',
  leverage: 5,
  size: 0.01,
})

// 网格交易相关
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

// 加载仓位信息
const loadPositions = async (): Promise<void> => {
  if (!isLoggedIn.value) {
    posError.value = '请先在账户面板登陆'
    return
  }
  posLoading.value = true
  posError.value = ''
  await fetchPositions()
  posLoading.value = false
  if (authError.value) {
    posError.value = authError.value
  }
}

// 格式化数字
const formatNumber = (num: number): string => {
  if (typeof num !== 'number') return '-'
  if (Math.abs(num) >= 1000000) {
    return (num / 1000000).toFixed(2) + 'M'
  }
  if (Math.abs(num) >= 1000) {
    return (num / 1000).toFixed(2) + 'K'
  }
  return num.toFixed(num > 0 && num < 1 ? 8 : 2)
}

const openPosition = (): void => {
  console.log('[PositionManager] open', { ...positionForm })
}

const closePosition = (): void => {
  console.log('[PositionManager] close', { symbol: positionForm.symbol })
}

const createGrid = (): void => {
  console.log('[GridTrading] create', { ...gridForm })
}

// 组件挂载时加载仓位
onMounted(() => {
  loadPositions()
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

.position-section {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.position-section h4 {
  margin: 0;
  font-size: 14px;
  color: #d1d4dc;
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
}

.refresh-btn:hover:not(:disabled) {
  background: #23283a;
  border-color: #2f3b52;
}

.refresh-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

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

.position-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.position-card {
  background: #161a23;
  border: 1px solid #2a2e39;
  border-radius: 6px;
  padding: 12px;
}

.pos-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  padding-bottom: 8px;
  border-bottom: 1px solid #2a2e39;
}

.pos-header h5 {
  margin: 0;
  font-size: 13px;
  color: #d1d4dc;
}

.pos-side {
  font-size: 11px;
  padding: 4px 8px;
  border-radius: 4px;
  font-weight: 600;
}

.pos-side.long {
  background: rgba(76, 175, 80, 0.2);
  color: #4caf50;
}

.pos-side.short {
  background: rgba(244, 67, 54, 0.2);
  color: #f44336;
}

.pos-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  font-size: 12px;
}

.pos-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.pos-item .label {
  color: #8b90a0;
}

.pos-item .value {
  color: #d1d4dc;
  font-weight: 500;
}

.value.profit {
  color: #4caf50;
}

.value.loss {
  color: #f44336;
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
