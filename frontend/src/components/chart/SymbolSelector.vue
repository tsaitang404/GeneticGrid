<template>
  <div class="symbol-selector">
    <label class="symbol-label">币对:</label>
    <div class="symbol-select-wrapper">
      <div class="symbol-dropdown" ref="dropdownRef">
        <button 
          class="symbol-button" 
          :class="{ 'dropdown-open': showDropdown }"
          @click="toggleDropdown"
          type="button"
        >
          <span class="symbol-value">{{ displaySymbol }}</span>
          <svg class="dropdown-icon" width="12" height="12" viewBox="0 0 12 12">
            <path d="M2 4l4 4 4-4" stroke="currentColor" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </button>
        
        <div v-if="showDropdown" class="symbol-dropdown-menu">
          <div class="search-box">
            <svg class="search-icon" width="14" height="14" viewBox="0 0 14 14">
              <circle cx="6" cy="6" r="4" stroke="currentColor" stroke-width="1.5" fill="none"/>
              <path d="M9 9l3 3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
            </svg>
            <input 
              ref="searchInputRef"
              v-model="searchQuery" 
              type="text" 
              placeholder="搜索交易对..."
              class="search-input"
              @keydown.esc="closeDropdown"
              @keydown.enter="selectFirstFiltered"
            />
          </div>
          
          <div class="symbol-list">
            <div v-if="filteredSymbols.length === 0" class="no-results">
              未找到匹配的交易对
            </div>
            <template v-else>
              <div 
                v-for="group in groupedSymbols" 
                :key="group.category"
                class="symbol-group"
              >
                <div v-if="group.symbols.length > 0" class="group-header">
                  {{ group.category }}
                </div>
                <button
                  v-for="sym in group.symbols"
                  :key="sym"
                  class="symbol-option"
                  :class="{ 'selected': sym === modelValue }"
                  @click="selectSymbol(sym)"
                  type="button"
                >
                  <span class="symbol-name">{{ sym }}</span>
                  <svg v-if="sym === modelValue" class="check-icon" width="14" height="14" viewBox="0 0 14 14">
                    <path d="M3 7l3 3 5-6" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
                  </svg>
                </button>
              </div>
            </template>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'

interface Props {
  modelValue: string
  symbols: string[]
  source?: string
}

const props = defineProps<Props>()
const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const showDropdown = ref(false)
const searchQuery = ref('')
const dropdownRef = ref<HTMLElement | null>(null)
const searchInputRef = ref<HTMLInputElement | null>(null)

const displaySymbol = computed(() => {
  if (!props.modelValue) return '选择币对'
  return props.modelValue
})

const filteredSymbols = computed(() => {
  if (!searchQuery.value) return props.symbols
  const query = searchQuery.value.toLowerCase()
  return props.symbols.filter(sym => 
    sym.toLowerCase().includes(query)
  )
})

const groupedSymbols = computed(() => {
  const groups: Record<string, string[]> = {
    '主流币': [],
    '平台币': [],
    '其他': []
  }
  
  const mainCoins = ['BTC', 'ETH', 'SOL', 'XRP', 'ADA', 'DOGE', 'DOT', 'AVAX', 'LINK', 'ATOM']
  const platformCoins = ['BNB', 'OKB', 'FTT', 'HT', 'KCS']
  
  filteredSymbols.value.forEach(sym => {
    const base = sym.replace(/USDT?$/, '').replace(/-.*$/, '')
    if (mainCoins.some(coin => base.includes(coin))) {
      groups['主流币'].push(sym)
    } else if (platformCoins.some(coin => base.includes(coin))) {
      groups['平台币'].push(sym)
    } else {
      groups['其他'].push(sym)
    }
  })
  
  return [
    { category: '主流币', symbols: groups['主流币'] },
    { category: '平台币', symbols: groups['平台币'] },
    { category: '其他', symbols: groups['其他'] }
  ].filter(group => group.symbols.length > 0)
})

const toggleDropdown = () => {
  showDropdown.value = !showDropdown.value
  if (showDropdown.value) {
    nextTick(() => {
      searchInputRef.value?.focus()
    })
  }
}

const closeDropdown = () => {
  showDropdown.value = false
  searchQuery.value = ''
}

const selectSymbol = (symbol: string) => {
  emit('update:modelValue', symbol)
  closeDropdown()
}

const selectFirstFiltered = () => {
  if (filteredSymbols.value.length > 0) {
    selectSymbol(filteredSymbols.value[0])
  }
}

const handleClickOutside = (event: MouseEvent) => {
  if (dropdownRef.value && !dropdownRef.value.contains(event.target as Node)) {
    closeDropdown()
  }
}

watch(() => props.source, () => {
  closeDropdown()
})

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<style scoped>
.symbol-selector {
  display: flex;
  align-items: center;
  gap: 8px;
}

.symbol-label {
  display: none; /* Hide label in new layout */
}

.symbol-select-wrapper {
  position: relative;
}

.symbol-dropdown {
  position: relative;
}

.symbol-button {
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

.symbol-button:hover {
  background: rgba(41, 98, 255, 0.1);
}

.symbol-button.dropdown-open {
  background: rgba(41, 98, 255, 0.15);
  border-color: transparent;
}

.symbol-value {
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

.symbol-dropdown-menu {
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

.search-box {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-secondary);
}

.search-icon {
  color: var(--text-secondary);
  flex-shrink: 0;
}

.search-input {
  flex: 1;
  border: none;
  background: transparent;
  color: var(--text-primary);
  font-size: 14px;
  outline: none;
}

.search-input::placeholder {
  color: var(--text-secondary);
}

.symbol-list {
  overflow-y: auto;
  max-height: 340px;
}

.symbol-group {
  padding: 8px 0;
}

.symbol-group:not(:last-child) {
  border-bottom: 1px solid var(--border-color);
}

.group-header {
  padding: 6px 12px;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.8px;
}

.symbol-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 8px 12px;
  border: none;
  background: transparent;
  color: var(--text-primary);
  font-size: 14px;
  text-align: left;
  cursor: pointer;
  transition: background 0.15s;
}

.symbol-option:hover {
  background: var(--bg-hover);
}

.symbol-option.selected {
  background: rgba(41, 98, 255, 0.1);
  color: var(--blue-accent);
  font-weight: 500;
}

.symbol-name {
  flex: 1;
  font-weight: 500;
}

.check-icon {
  color: var(--blue-accent);
  flex-shrink: 0;
}

.no-results {
  padding: 24px;
  text-align: center;
  color: var(--text-secondary);
  font-size: 14px;
}

/* 滚动条样式 */
.symbol-list::-webkit-scrollbar {
  width: 6px;
}

.symbol-list::-webkit-scrollbar-track {
  background: transparent;
}

.symbol-list::-webkit-scrollbar-thumb {
  background: var(--border-color);
  border-radius: 3px;
}

.symbol-list::-webkit-scrollbar-thumb:hover {
  background: var(--text-secondary);
}
</style>
