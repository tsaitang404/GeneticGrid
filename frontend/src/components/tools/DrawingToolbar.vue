<template>
  <div class="drawing-controls">
    <button
      v-if="!expanded"
      @click="$emit('update:expanded', true)"
      class="toggle-btn"
      title="画线工具"
    >
      ✏️
    </button>
    
    <div v-else class="drawing-toolbar">
      <button
        @click="$emit('update:expanded', false)"
        class="close-btn"
        title="收起"
      >
        ✕
      </button>
      
      <div class="separator" />
      
      <div
        v-for="tool in tools"
        :key="tool.id"
        class="tool-wrapper"
      >
        <button
          :class="{ active: modelValue === tool.id }"
          @click="handleToolClick(tool)"
          :title="tool.name"
          class="tool-btn"
        >
          {{ tool.icon }}
        </button>
        <transition name="parallel-fade">
          <div
            v-if="tool.id === 'parallel' && showParallelConfig"
            class="parallel-config"
            @mousedown.stop
            @click.stop
          >
            <button class="step-btn" type="button" @click="decrementParallel">-</button>
            <input
              ref="parallelInputRef"
              class="parallel-input"
              type="number"
              :value="parallelValue"
              min="2"
              max="10"
              step="1"
              @input="onParallelInput"
              @keydown.stop
            >
            <button class="step-btn" type="button" @click="incrementParallel">+</button>
          </div>
        </transition>
      </div>
      
      <button
        @click="handleTrashClick"
        :class="['tool-btn', { active: modelValue === 'delete' }]"
        :title="modelValue === 'delete' ? '再次点击清除全部' : '删除模式'"
      >
        🗑️
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import type { DrawingType } from '@/types'

interface Props {
  modelValue: DrawingType
  expanded: boolean
  parallelLineCount: number
}

const props = defineProps<Props>()
const emit = defineEmits<{
  'update:tool': [tool: DrawingType]
  'update:expanded': [expanded: boolean]
  clear: []
  'configure-parallel': [count: number]
}>()

const tools: Array<{ id: DrawingType; name: string; icon: string }> = [
  { id: 'cursor', name: '光标', icon: '👆' },
  { id: 'line', name: '直线', icon: '╱' },
  { id: 'ray', name: '射线', icon: '➚' },
  { id: 'horizontal', name: '横线', icon: '─' },
  { id: 'fib', name: '斐波那契', icon: '≡' },
  { id: 'parallel', name: '等距通道', icon: '∥' }
]

const showParallelConfig = ref(false)

const clampParallelValue = (value: number): number => {
  if (!Number.isFinite(value)) return 2
  const rounded = Math.round(value)
  if (Number.isNaN(rounded)) return 2
  return Math.min(10, Math.max(2, rounded))
}

const parallelValue = ref(clampParallelValue(props.parallelLineCount ?? 2))

watch(() => props.parallelLineCount, value => {
  parallelValue.value = clampParallelValue(value ?? 2)
})

watch(() => props.modelValue, value => {
  if (value !== 'parallel') {
    showParallelConfig.value = false
  }
})

watch(() => props.expanded, value => {
  if (!value) {
    showParallelConfig.value = false
  }
})

const emitParallelValue = (value: number) => {
  const clamped = clampParallelValue(value)
  if (clamped !== parallelValue.value) {
    parallelValue.value = clamped
  }
  emit('configure-parallel', clamped)
}

const handleToolClick = (tool: { id: DrawingType; name: string; icon: string }) => {
  emit('update:tool', tool.id)

  if (tool.id === 'parallel') {
    parallelValue.value = clampParallelValue(props.parallelLineCount ?? parallelValue.value)
    nextTick(() => {
      showParallelConfig.value = true
      parallelInputRef.value?.focus()
      parallelInputRef.value?.select()
    })
  } else {
    showParallelConfig.value = false
  }
}

const parallelInputRef = ref<HTMLInputElement | null>(null)

const incrementParallel = () => {
  emitParallelValue(parallelValue.value + 1)
}

const decrementParallel = () => {
  emitParallelValue(parallelValue.value - 1)
}

const onParallelInput = (event: Event) => {
  const target = event.target as HTMLInputElement
  const parsed = Number.parseInt(target.value, 10)
  if (Number.isNaN(parsed)) {
    return
  }
  emitParallelValue(parsed)
}

const handleTrashClick = () => {
  if (props.modelValue === 'delete') {
    emit('clear')
    return
  }
  emit('update:tool', 'delete')
}
</script>

<style scoped>
.drawing-controls {
  position: absolute;
  top: 10px;
  right: 110px;
  z-index: 20;
}

.toggle-btn {
  background: rgba(42, 46, 57, 0.9);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
  width: 32px;
  height: 32px;
  padding: 0;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.toggle-btn:hover {
  background: rgba(41, 98, 255, 0.2);
  border-color: var(--blue-accent);
  color: var(--blue-accent);
}

.drawing-toolbar {
  background: rgba(42, 46, 57, 0.95);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  padding: 0;
  display: flex;
  gap: 4px;
  align-items: center;
  height: 32px;
}

.tool-wrapper {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}

.close-btn,
.tool-btn {
  background: transparent;
  border: 1px solid transparent;
  color: var(--text-primary);
  width: 32px;
  height: 32px;
  padding: 0;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.close-btn:hover,
.tool-btn:hover {
  background: rgba(41, 98, 255, 0.2);
  border-color: var(--blue-accent);
}

.tool-btn.active {
  background: rgba(41, 98, 255, 0.2);
  border-color: var(--blue-accent);
  color: var(--blue-accent);
}

.separator {
  width: 1px;
  height: 20px;
  background: #2a2e39;
  margin: 0 4px;
}

.parallel-config {
  position: absolute;
  top: 36px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(24, 26, 33, 0.95);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  padding: 6px 8px;
  display: flex;
  gap: 6px;
  align-items: center;
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.4);
  z-index: 1;
}

.parallel-input {
  width: 46px;
  padding: 4px 6px;
  border-radius: 4px;
  border: 1px solid var(--border-color);
  background: rgba(42, 46, 57, 0.95);
  color: var(--text-primary);
  text-align: center;
  font-size: 13px;
  outline: none;
}

.parallel-input:focus {
  border-color: var(--blue-accent);
  box-shadow: 0 0 0 1px rgba(41, 98, 255, 0.4);
}

.step-btn {
  width: 24px;
  height: 24px;
  border-radius: 4px;
  border: 1px solid var(--border-color);
  background: rgba(42, 46, 57, 0.95);
  color: var(--text-primary);
  cursor: pointer;
  font-size: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.step-btn:hover {
  border-color: var(--blue-accent);
  color: var(--blue-accent);
}

.parallel-fade-enter-active,
.parallel-fade-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}

.parallel-fade-enter-from,
.parallel-fade-leave-to {
  opacity: 0;
  transform: translate(-50%, -6px);
}
</style>
