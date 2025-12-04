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
        @click="$emit('update:tool', tool.id)"
        :title="tool.name"
        class="tool-btn"
      >
        {{ tool.icon }}
      </button>
      
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
import type { DrawingType } from '@/types'

interface Props {
  modelValue: DrawingType
  expanded: boolean
}

const props = defineProps<Props>()
const emit = defineEmits<{
  'update:tool': [tool: DrawingType]
  'update:expanded': [expanded: boolean]
  clear: []
}>()

const tools: Array<{ id: DrawingType; name: string; icon: string }> = [
  { id: 'cursor', name: '光标', icon: '👆' },
  { id: 'line', name: '直线', icon: '╱' },
  { id: 'ray', name: '射线', icon: '➚' },
  { id: 'horizontal', name: '横线', icon: '─' },
  { id: 'fib', name: '斐波那契', icon: '≡' },
  { id: 'parallel', name: '等距通道', icon: '∥' }
]

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
</style>
