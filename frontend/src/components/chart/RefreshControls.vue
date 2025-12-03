<template>
  <div class="refresh-controls">
    <button
      class="refresh-btn"
      title="手动刷新"
      @click="$emit('refresh')"
    >
      🔄
    </button>
    <button
      class="auto-refresh-btn"
      :class="{ active: autoRefresh }"
      title="切换自动刷新"
      @click="$emit('toggle-auto-refresh')"
    >
      自动: {{ autoRefresh ? '开' : '关' }}
    </button>
  </div>
</template>

<script setup lang="ts">
interface Props {
  autoRefresh: boolean
}

defineProps<Props>()

defineEmits<{
  'refresh': []
  'toggle-auto-refresh': []
}>()
</script>

<style scoped>
.refresh-controls {
  display: flex;
  align-items: center;
  gap: 8px;
}

.refresh-btn,
.auto-refresh-btn {
  padding: 6px 12px;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  background: var(--bg-primary);
  color: var(--text-primary);
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.refresh-btn:hover,
.auto-refresh-btn:hover {
  background: var(--bg-secondary);
  border-color: var(--blue-accent);
}

.refresh-btn:active,
.auto-refresh-btn:active {
  transform: scale(0.95);
}

.auto-refresh-btn.active {
  background: var(--blue-accent);
  border-color: var(--blue-accent);
  color: white;
}

.refresh-btn {
  font-size: 16px;
  padding: 6px 10px;
}
</style>
