<template>
  <teleport to="body">
    <div class="overlay" @click.self="close">
      <div class="modal">
        <header class="modal-header">
          <h3>仓位管理</h3>
          <button class="close-btn" @click="close">✕</button>
        </header>
        <section class="modal-body">
          <div class="grid">
            <label>
              <span>交易对</span>
              <input v-model="form.symbol" placeholder="如 BTCUSDT" />
            </label>
            <label>
              <span>方向</span>
              <select v-model="form.side">
                <option value="long">多头</option>
                <option value="short">空头</option>
              </select>
            </label>
            <label>
              <span>杠杆</span>
              <input v-model.number="form.leverage" type="number" min="1" max="125" />
            </label>
            <label>
              <span>数量</span>
              <input v-model.number="form.size" type="number" min="0" step="0.0001" />
            </label>
          </div>

          <div class="actions">
            <button class="btn primary" @click="openPosition">开仓(演示)</button>
            <button class="btn" @click="closePosition">平仓(演示)</button>
          </div>

          <p class="tip">提示：当前为原型占位，未接入交易所 API。</p>
        </section>
      </div>
    </div>
  </teleport>
</template>

<script setup lang="ts">
import { reactive } from 'vue'

const emit = defineEmits<{ (e: 'close'): void }>()

const form = reactive({
  symbol: 'BTCUSDT',
  side: 'long',
  leverage: 5,
  size: 0.01,
})

const close = (): void => emit('close')

const openPosition = (): void => {
  // 仅示例输出
  console.log('[PositionManager] open', { ...form })
  close()
}

const closePosition = (): void => {
  // 仅示例输出
  console.log('[PositionManager] close', { symbol: form.symbol })
  close()
}
</script>

<style scoped>
.overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.55);
  display: grid;
  place-items: center;
  z-index: 1100;
}
.modal {
  width: 560px;
  max-width: 92vw;
  background: #12151c;
  border: 1px solid #2a2e39;
  border-radius: 10px;
  box-shadow: 0 -10px 40px rgba(0,0,0,0.35);
}
.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid #2a2e39;
}
.close-btn {
  background: transparent;
  border: 1px solid #2a2e39;
  color: #d1d4dc;
  height: 28px;
  width: 28px;
  border-radius: 6px;
  cursor: pointer;
}
.modal-body {
  padding: 16px;
}
.grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
label {
  display: grid;
  gap: 6px;
  font-size: 12px;
  color: #9aa3b2;
}
input, select {
  background: #1b202b;
  border: 1px solid #2a2e39;
  color: #d1d4dc;
  height: 36px;
  border-radius: 6px;
  padding: 0 10px;
}
.actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}
.btn {
  height: 36px;
  padding: 0 14px;
  border-radius: 6px;
  border: 1px solid #2a2e39;
  background: #1e222d;
  color: #d1d4dc;
  cursor: pointer;
}
.btn.primary {
  background: #2962ff;
  border-color: #2962ff;
}
.tip {
  margin-top: 10px;
  color: #7f8694;
  font-size: 12px;
}
</style>
