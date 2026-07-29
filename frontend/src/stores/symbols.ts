import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export interface SymbolMeta {
  inst_id: string
  last: number | null
  market_cap: number | null
  market_cap_rank: number | null
  change_24h_pct: number | null
  volume_24h: number | null
}

export const useSymbolsStore = defineStore('symbols', () => {
  // --- state ---
  const allSymbols = ref<SymbolMeta[]>([])
  const loading = ref(false)
  const error = ref('')
  const searchQuery = ref('')

  // --- getters ---

  /** 纯符号名列表（兼容旧接口） */
  const symbols = computed(() => allSymbols.value.map(s => s.inst_id))

  /** 按搜索过滤 + 市值降序的完整列表 */
  const filteredSymbols = computed(() => {
    let list = [...allSymbols.value]
    const q = searchQuery.value.toLowerCase()
    if (q) {
      list = list.filter(s => s.inst_id.toLowerCase().includes(q))
    }
    // 市值降序（缺失的放最后）
    list.sort((a, b) => (b.market_cap ?? 0) - (a.market_cap ?? 0))
    return list
  })

  /** 分组：热门 Top 10 + 其他 */
  const groupedSymbols = computed(() => {
    const top10 = filteredSymbols.value.slice(0, 10)
    const rest = filteredSymbols.value.slice(10)
    return [
      { category: '🔥 热门 Top 10', symbols: top10.map(s => s.inst_id) },
      { category: '其他', symbols: rest.map(s => s.inst_id) },
    ].filter(g => g.symbols.length > 0)
  })

  // --- actions ---

  async function fetchSymbols(source = 'coingecko') {
    if (allSymbols.value.length > 0) return // 已加载则复用
    loading.value = true
    error.value = ''
    try {
      const res = await fetch(`/api/symbols/?source=${source}&limit=100`)
      const json = await res.json()
      if (json.code === 0 && json.data) {
        allSymbols.value = json.data
      } else {
        error.value = json.error || '获取符号列表失败'
      }
    } catch (e: any) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  /** 格式化市值显示 */
  function formatMarketCap(cap: number | null): string {
    if (!cap) return ''
    if (cap >= 1e12) return `$${(cap / 1e12).toFixed(1)}T`
    if (cap >= 1e9) return `$${(cap / 1e9).toFixed(1)}B`
    if (cap >= 1e6) return `$${(cap / 1e6).toFixed(1)}M`
    return `$${cap.toFixed(0)}`
  }

  /** 格式化价格显示 */
  function formatPrice(price: number | null): string {
    if (!price) return ''
    return price >= 1 ? price.toFixed(2) : price.toFixed(6)
  }

  /** 获取单个符号的元数据 */
  function getMeta(sym: string): SymbolMeta | undefined {
    return allSymbols.value.find(s => s.inst_id === sym)
  }

  return {
    allSymbols, loading, error, searchQuery,
    symbols, filteredSymbols, groupedSymbols,
    fetchSymbols, formatMarketCap, formatPrice, getMeta,
  }
})
