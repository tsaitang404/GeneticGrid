<template>
  <div class="indicator-selector">
    <div class="indicator-dropdown" ref="dropdownRef">
      <button
        class="indicator-btn"
        @click="toggleDropdown"
      >
        {{ dropdownLabel }}
        <span class="arrow" :class="{ open: isOpen }">▼</span>
      </button>

      <div v-if="isOpen" class="dropdown-menu">
        <div
          v-for="item in allIndicatorEntries"
          :key="item.key"
          class="dropdown-item"
          @click="emitToggle(item.key)"
        >
          <input
            type="checkbox"
            :checked="item.config.enabled"
            @click.stop
            @change="emitToggle(item.key)"
          />
          <span>{{ item.config.name }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted } from 'vue'
import type { IndicatorConfig, Indicators } from '@/types'

interface Props {
  indicators: Indicators
}

const props = defineProps<Props>()
const emit = defineEmits<{
  toggle: [key: keyof Indicators]
}>()

const isOpen = ref(false)
const dropdownRef = ref<HTMLElement | null>(null)

const allIndicatorEntries = computed(() => {
  return (Object.entries(props.indicators) as [keyof Indicators, Indicators[keyof Indicators]][])
    .map(([key, config]) => ({ key, config }))
    .filter((item): item is { key: keyof Indicators, config: IndicatorConfig } => item.config !== undefined)
})

const enabledCount = computed(() => {
  return allIndicatorEntries.value.filter(item => item.config.enabled).length
})

const dropdownLabel = computed(() => {
  return enabledCount.value > 0 ? `指标 (${enabledCount.value})` : '指标'
})

const emitToggle = (key: keyof Indicators): void => {
  emit('toggle', key)
}

const toggleDropdown = (): void => {
  isOpen.value = !isOpen.value
}

const handleClickOutside = (event: MouseEvent): void => {
  if (dropdownRef.value && !dropdownRef.value.contains(event.target as Node)) {
    isOpen.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<style scoped>
.indicator-selector {
  display: flex;
  align-items: center;
  position: relative;
}

.indicator-dropdown {
  position: relative;
}

.indicator-btn {
  background: #2a2e39;
  color: #d1d4dc;
  border: 1px solid #363a45;
  border-radius: 4px;
  padding: 6px 12px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 100px;
  justify-content: space-between;
}

.indicator-btn:hover {
  background: #363a45;
  border-color: var(--blue-accent);
}

.arrow {
  font-size: 10px;
  transition: transform 0.2s;
}

.arrow.open {
  transform: rotate(180deg);
}

.dropdown-menu {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  background: #2a2e39;
  border: 1px solid #363a45;
  border-radius: 4px;
  min-width: 200px;
  max-height: 400px;
  overflow-y: auto;
  z-index: 1000;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.dropdown-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  cursor: pointer;
  transition: background 0.2s;
  font-size: 13px;
  color: #d1d4dc;
}

.dropdown-item:hover {
  background: #363a45;
}

.dropdown-item input[type="checkbox"] {
  cursor: pointer;
  width: 16px;
  height: 16px;
}

.dropdown-item span {
  user-select: none;
}
</style>
