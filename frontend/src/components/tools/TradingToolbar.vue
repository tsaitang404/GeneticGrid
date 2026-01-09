<template>
  <teleport to="body">
    <div class="trading-toolbar" role="toolbar" aria-label="交易工具栏">
      <div class="toolbar-inner">
        <button class="tool-btn" @click="openPositionManager">
          <span class="icon">📊</span>
          <span class="label">仓位管理</span>
        </button>
        <button class="tool-btn" @click="openGridTrading">
          <span class="icon">🧱</span>
          <span class="label">网格交易</span>
        </button>
        <button class="tool-btn" disabled title="即将上线">
          <span class="icon">🛡️</span>
          <span class="label">风险控制</span>
        </button>
        <div class="spacer" />
        <button class="tool-btn secondary" disabled title="即将上线">
          <span class="icon">📈</span>
          <span class="label">策略回测</span>
        </button>
      </div>
    </div>
  </teleport>

  <PositionManagerModal v-if="showPosition" @close="showPosition = false" />
  <GridTradingModal v-if="showGrid" @close="showGrid = false" />
</template>

<script setup lang="ts">
import { ref } from 'vue'
import PositionManagerModal from './position-manager-modal.vue'
import GridTradingModal from './grid-trading-modal.vue'

const showPosition = ref(false)
const showGrid = ref(false)

const openPositionManager = (): void => {
  showPosition.value = true
}

const openGridTrading = (): void => {
  showGrid.value = true
}
</script>

<style scoped>
.trading-toolbar {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  height: 56px;
  background: rgba(17, 20, 28, 0.96);
  border-top: 1px solid #2a2e39;
  backdrop-filter: blur(6px);
  z-index: 1000;
}

.toolbar-inner {
  max-width: 1440px;
  margin: 0 auto;
  height: 100%;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 16px;
}

.tool-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  height: 36px;
  padding: 0 12px;
  border-radius: 6px;
  border: 1px solid #2a2e39;
  background: #1e222d;
  color: #d1d4dc;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.15s ease;
}

.tool-btn:hover {
  background: #232838;
  border-color: #2f3b52;
}

.tool-btn.secondary {
  background: transparent;
}

.tool-btn[disabled] {
  opacity: 0.5;
  cursor: not-allowed;
}

.icon {
  font-size: 16px;
  line-height: 1;
}

.label {
  line-height: 1;
}

.spacer {
  flex: 1;
}
</style>
