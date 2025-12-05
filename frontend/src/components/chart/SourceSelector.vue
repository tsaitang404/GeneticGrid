<template>
  <div class="source-selector">
    <label class="source-label">数据源:</label>
    <div class="source-select-wrapper">
      <div class="source-dropdown" ref="dropdownRef">
        <button 
          class="source-button" 
          :class="{ 'dropdown-open': showDropdown }"
          :disabled="loading || error"
          @click="toggleDropdown"
          type="button"
        >
          <span v-if="loading" class="source-value">加载中...</span>
          <span v-else-if="error" class="source-value">加载失败</span>
          <span v-else class="source-value">{{ displaySource }}</span>
          <svg class="dropdown-icon" width="12" height="12" viewBox="0 0 12 12">
            <path d="M2 4l4 4 4-4" stroke="currentColor" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </button>
        
        <div v-if="showDropdown && !loading && !error" class="source-dropdown-menu">
          <div class="source-list">
            <button
              v-for="src in sources"
              :key="src.name"
              class="source-option"
              :class="{ 'selected': src.name === modelValue }"
              @click="selectSource(src)"
              type="button"
            >
              <div class="source-content">
                <span class="source-name">{{ src.display_name }}</span>
                <span class="source-badges">
                  <span class="source-badge" :class="getSourceBadgeClass(src)">
                    {{ getSourceBadge(src) }}
                  </span>
                  <span v-if="src.requires_proxy" class="proxy-badge">🔒</span>
                  <span v-if="!src.supports_candlesticks" class="ticker-only-badge">仅行情</span>
                </span>
              </div>
              <svg v-if="src.name === modelValue" class="check-icon" width="14" height="14" viewBox="0 0 14 14">
                <path d="M3 7l3 3 5-6" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, onUnmounted } from 'vue'

interface Source {
  name: string
  display_name: string
  description: string
  source_type: string
  supports_candlesticks: boolean
  requires_proxy: boolean
  supported_symbols: string[]
  candlestick_granularities: string[]
  rate_limit_per_minute?: number
}

interface Props {
  modelValue: string
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
  'sourceChanged': [source: Source]
}>()

const sources = ref<Source[]>([])
const loading = ref(true)
const error = ref(false)
const showDropdown = ref(false)
const dropdownRef = ref<HTMLElement | null>(null)

const selectedSource = computed(() => 
  sources.value.find(s => s.name === props.modelValue)
)

const displaySource = computed(() => {
  if (!selectedSource.value) return '选择数据源'
  return selectedSource.value.display_name
})

const loadSources = async () => {
  try {
    loading.value = true
    error.value = false
    const response = await fetch('/api/sources/')
    const data = await response.json()
    
    if (data.code === 0 && data.data) {
      sources.value = Object.entries(data.data).map(([name, info]: [string, any]) => ({
        name,
        display_name: info.metadata.display_name,
        description: info.metadata.description,
        source_type: info.metadata.source_type,
        supports_candlesticks: info.capability.supports_candlesticks,
        requires_proxy: info.capability.requires_proxy,
        supported_symbols: info.capability.supported_symbols || [],
        candlestick_granularities: info.capability.candlestick_granularities || [],
        rate_limit_per_minute: info.capability.rate_limit_per_minute
      }))
      
      // 按类型排序：交易所 > 聚合器
      sources.value.sort((a, b) => {
        if (a.source_type === b.source_type) return a.display_name.localeCompare(b.display_name)
        return a.source_type === 'exchange' ? -1 : 1
      })
    }
  } catch (e) {
    console.error('Failed to load sources:', e)
    error.value = true
  } finally {
    loading.value = false
  }
}

const toggleDropdown = () => {
  if (loading.value || error.value) return
  showDropdown.value = !showDropdown.value
}

const closeDropdown = () => {
  showDropdown.value = false
}

const selectSource = (source: Source) => {
  emit('update:modelValue', source.name)
  emit('sourceChanged', source)
  closeDropdown()
}

const handleClickOutside = (event: MouseEvent) => {
  if (dropdownRef.value && !dropdownRef.value.contains(event.target as Node)) {
    closeDropdown()
  }
}

const getSourceBadge = (source: Source): string => {
  if (source.source_type === 'exchange') return '交易所'
  if (source.source_type === 'aggregator') return '聚合器'
  return source.source_type
}

const getSourceBadgeClass = (source: Source): string => {
  return `badge-${source.source_type}`
}

onMounted(() => {
  loadSources()
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<style scoped>
.source-selector {
  display: flex;
  align-items: center;
  gap: 8px;
}

.source-label {
  display: none; /* Hide label in new layout */
}

.source-select-wrapper {
  position: relative;
}

.source-dropdown {
  position: relative;
}

.source-button {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 6px 10px;
  min-width: 120px;
  border: 1px solid transparent;
  border-radius: 4px;
  background: transparent;
  color: var(--text-primary);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  outline: none;
  transition: all 0.2s;
}

.source-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.source-button:hover:not(:disabled) {
  background: rgba(41, 98, 255, 0.1);
}

.source-button.dropdown-open {
  background: rgba(41, 98, 255, 0.15);
  border-color: transparent;
}

.source-value {
  flex: 1;
  text-align: left;
  font-weight: 500;
}

.dropdown-icon {
  color: var(--text-secondary);
  transition: transform 0.2s;
}

.dropdown-open .dropdown-icon {
  transform: rotate(180deg);
}

.source-dropdown-menu {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  right: 0;
  min-width: 280px;
  max-height: 400px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
  z-index: 1000;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.source-list {
  overflow-y: auto;
  max-height: 400px;
  padding: 4px 0;
}

.source-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 10px 12px;
  border: none;
  background: transparent;
  color: var(--text-primary);
  text-align: left;
  cursor: pointer;
  transition: background 0.15s;
}

.source-option:hover {
  background: var(--bg-hover);
}

.source-option.selected {
  background: rgba(41, 98, 255, 0.1);
  color: var(--blue-accent);
}

.source-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.source-name {
  font-size: 14px;
  font-weight: 500;
}

.source-badges {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.source-badge {
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 3px;
  font-weight: 500;
  white-space: nowrap;
}

.badge-exchange {
  background: rgba(38, 166, 154, 0.15);
  color: #26a69a;
}

.badge-aggregator {
  background: rgba(41, 98, 255, 0.15);
  color: #2962ff;
}

.proxy-badge {
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 3px;
  background: rgba(255, 193, 7, 0.15);
  color: #ffc107;
}

.ticker-only-badge {
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 3px;
  background: rgba(156, 39, 176, 0.15);
  color: #9c27b0;
}

.check-icon {
  color: var(--blue-accent);
  flex-shrink: 0;
}

/* 滚动条样式 */
.source-list::-webkit-scrollbar {
  width: 6px;
}

.source-list::-webkit-scrollbar-track {
  background: transparent;
}

.source-list::-webkit-scrollbar-thumb {
  background: var(--border-color);
  border-radius: 3px;
}

.source-list::-webkit-scrollbar-thumb:hover {
  background: var(--text-secondary);
}
</style>
