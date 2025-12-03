<template>
  <div
    class="resize-handle"
    @mousedown.prevent="$emit('resize-start', $event)"
    @mouseover="isHovered = true"
    @mouseleave="isHovered = false"
    :class="{ hovered: isHovered }"
  >
    <div class="handle-indicator" />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

defineEmits<{
  'resize-start': [event: MouseEvent]
}>()

const isHovered = ref<boolean>(false)
</script>

<style scoped>
.resize-handle {
  height: 8px;
  background: #131722;
  cursor: ns-resize;
  width: 100%;
  flex-shrink: 0;
  border-top: 1px solid #2a2e39;
  border-bottom: 1px solid #2a2e39;
  z-index: 10;
  transition: background 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.resize-handle:hover,
.resize-handle.hovered {
  background: #2a2e39;
}

.handle-indicator {
  width: 30px;
  height: 2px;
  background: #434651;
  border-radius: 1px;
}
</style>
