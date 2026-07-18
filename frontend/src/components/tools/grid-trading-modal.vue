<template>
  <teleport to="body">
    <div class="overlay" @click.self="close">
      <div class="modal">
        <header class="modal-header">
          <h3>网格交易</h3>
          <button class="close-btn" @click="close">✕</button>
        </header>
        <section class="modal-body">
          <div class="grid">
            <label>
              <span>交易对</span>
              <input v-model="form.symbol" placeholder="如 BTCUSDT">
            </label>
            <label>
              <span>网格数量</span>
              <input v-model.number="form.grids" type="number" min="2" max="200">
            </label>
            <label>
              <span>下限价格</span>
              <input v-model.number="form.lower" type="number" min="0" step="0.01">
            </label>
            <label>
              <span>上限价格</span>
              <input v-model.number="form.upper" type="number" min="0" step="0.01">
            </label>
            <label>
              <span>投资金额</span>
              <input v-model.number="form.invest" type="number" min="0" step="0.01">
            </label>
            <label>
              <span>风格</span>
              <select v-model="form.mode">
                <option value="arithmetic">等差</option>
                <option value="geometric">等比</option>
              </select>
            </label>
          </div>

          <div class="preview">
            <div>预计每网格资金：<b>{{ gridFund.toFixed(4) }}</b></div>
            <div>预计价格步长：<b>{{ stepPreview }}</b></div>
          </div>

          <div class="actions">
            <button class="btn primary" @click="createGrid">创建网格(演示)</button>
            <button class="btn" @click="close">取消</button>
          </div>

          <p class="tip">提示：这是原型占位，当前不接入真实交易。</p>
        </section>
      </div>
    </div>
  </teleport>
</template>

<script setup lang="ts">
import { reactive, computed } from 'vue'

const emit = defineEmits<{ (e: 'close'): void }>()

const form = reactive({
  symbol: 'BTCUSDT',
  grids: 20,
  lower: 50000,
  upper: 60000,
  invest: 1000,
  mode: 'arithmetic' as 'arithmetic' | 'geometric',
})

const close = (): void => emit('close')

const gridFund = computed(() => {
  if (form.grids <= 0) return 0
  return form.invest / form.grids
})

const stepPreview = computed(() => {
  const g = Math.max(2, form.grids)
  if (form.mode === 'arithmetic') {
    const step = (form.upper - form.lower) / (g - 1)
    return step > 0 ? step.toFixed(2) : '-'
  } else {
    if (form.lower <= 0 || form.upper <= 0) return '-'
    const ratio = Math.pow(form.upper / form.lower, 1 / (g - 1))
    return ratio > 0 ? ratio.toFixed(4) + 'x' : '-'
  }
})

const createGrid = (): void => {
  console.log('[GridTrading] create', { ...form })
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
  width: 640px;
  max-width: 94vw;
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
.preview {
  margin-top: 12px;
  padding: 10px;
  background: #161a23;
  border: 1px dashed #2a2e39;
  border-radius: 8px;
  color: #c3cad7;
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
