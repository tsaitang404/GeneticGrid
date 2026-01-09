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
      <div class="form-grid">
        <div class="form-group">
          <label>交易对</label>
          <input v-model="positionForm.symbol" placeholder="如 BTCUSDT" />
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
          <input v-model.number="positionForm.leverage" type="number" min="1" max="125" />
        </div>
        <div class="form-group">
          <label>数量</label>
          <input v-model.number="positionForm.size" type="number" min="0" step="0.0001" />
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
import { ref, reactive, computed } from 'vue'

const activeTab = ref<'position' | 'grid'>('position')

const positionForm = reactive({
  symbol: 'BTCUSDT',
  side: 'long',
  leverage: 5,
  size: 0.01,
})

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

const openPosition = (): void => {
  console.log('[PositionManager] open', { ...positionForm })
}

const closePosition = (): void => {
  console.log('[PositionManager] close', { symbol: positionForm.symbol })
}

const createGrid = (): void => {
  console.log('[GridTrading] create', { ...gridForm })
}
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

.tip {
  margin-top: 10px;
  font-size: 12px;
  color: #7f8694;
}
</style>
