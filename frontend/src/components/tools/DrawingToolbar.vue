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
      
      <button
        v-for="tool in tools"
        :key="tool.id"
        :class="{ active: modelValue === tool.id }"
        @click="$emit('update:tool', tool.id as DrawingType)"
        :title="tool.name"
        class="tool-btn"
      >
        {{ tool.icon }}
      </button>
      
      <button
        @click="$emit('clear')"
        class="tool-btn"
        title="清除所有"
      >
        🗑️
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { DrawingType } from '@/types'

interface Props {
  modelValue: DrawingType
  expanded: boolean
}

defineProps<Props>()
defineEmits<{
  'update:tool': [tool: DrawingType]
  'update:expanded': [expanded: boolean]
  clear: []
}>()

const tools = [
  { id: 'cursor', name: '光标', icon: '👆' },
  { id: 'line', name: '直线', icon: '╱' },
  { id: 'ray', name: '射线', icon: '➚' },
  { id: 'horizontal', name: '横线', icon: '─' },
  { id: 'fib', name: '斐波那契', icon: '≡' },
  { id: 'parallel', name: '等距通道', icon: '∥' }
]
</script>

<style scoped>
.drawing-controls {
  position: absolute;
  top: 0;
  left: 0;
  z-index: 20;
}

.toggle-btn {
  background: rgba(30, 34, 45, 0.9);
  border: 1px solid #2a2e39;
  color: #d1d4dc;
  padding: 6px 10px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 16px;
}

.toggle-btn:hover {
  background: rgba(30, 34, 45, 1);
}

.drawing-toolbar {
  background: rgba(30, 34, 45, 0.95);
  border: 1px solid #2a2e39;
  border-radius: 4px;
  padding: 6px;
  display: flex;
  gap: 4px;
  align-items: center;
}

.close-btn,
.tool-btn {
  background: transparent;
  border: 1px solid transparent;
  color: #d1d4dc;
  padding: 6px 10px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 16px;
  transition: all 0.2s;
}

.close-btn:hover,
.tool-btn:hover {
  background: #363a45;
}

.tool-btn.active {
  background: #363a45;
  border-color: #434651;
}

.separator {
  width: 1px;
  height: 20px;
  background: #2a2e39;
  margin: 0 4px;
}
</style>
