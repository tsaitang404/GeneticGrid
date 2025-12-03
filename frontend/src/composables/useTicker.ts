import { ref, reactive, watch, type Ref } from 'vue'
import type { TickerData, APIResponse } from '@/types'

interface ExchangeRates {
  [key: string]: number
}

export function useTicker(
  symbol: Ref<string>,
  source: Ref<string>,
  currency: Ref<string>
) {
  const ticker = reactive<TickerData>({
    last: '--',
    open24h: '--',
    high24h: '--',
    low24h: '--',
    vol24h: '--',
    changePercent: '--',
    isUp: true
  })

  const exchangeRates = reactive<ExchangeRates>({
    'USDT': 1,
    'USDC': 1,
    'USD': 1,
    'CNY': 7.25,
    'EUR': 0.95,
    'GBP': 0.79,
    'JPY': 150,
    'KRW': 1400,
    'HKD': 7.8,
    'AUD': 1.5,
    'CAD': 1.4,
    'CHF': 0.88,
    'SGD': 1.34,
    'INR': 84,
    'RUB': 105
  })

  const isLoading = ref<boolean>(false)

  const fetchExchangeRates = async (): Promise<void> => {
    try {
      const response = await fetch('https://open.er-api.com/v6/latest/USD')
      const data = await response.json()
      
      if (data.result === 'success') {
        Object.keys(exchangeRates).forEach(key => {
          if (data.rates[key]) {
            exchangeRates[key] = data.rates[key]
          }
        })
      }
    } catch (error) {
      console.warn('Failed to fetch exchange rates, using defaults:', error)
    }
  }

  const getRate = (): number => {
    return exchangeRates[currency.value] || 1
  }

  const loadTicker = async (): Promise<void> => {
    if (isLoading.value) return
    
    isLoading.value = true
    try {
      const response = await fetch(
        `/api/ticker/?symbol=${symbol.value}&source=${source.value}`
      )
      const result: APIResponse<any> = await response.json()

      if (result.code === 0 && result.data) {
        const t = result.data
        const rate = getRate()
        
        const last = parseFloat(t.last) * rate
        const open = parseFloat(t.open24h) * rate
        
        ticker.last = last.toLocaleString()
        ticker.changePercent = ((last - open) / open * 100).toFixed(2)
        ticker.isUp = last >= open
        ticker.high24h = (parseFloat(t.high24h) * rate).toLocaleString()
        ticker.low24h = (parseFloat(t.low24h) * rate).toLocaleString()
        ticker.vol24h = parseFloat(t.vol24h).toLocaleString()
        ticker.open24h = open.toLocaleString()
      }
    } catch (error) {
      console.error('Failed to load ticker:', error)
    } finally {
      isLoading.value = false
    }
  }

  // Watch for symbol, source, or currency changes
  watch([symbol, source, currency], () => {
    loadTicker()
  })

  // Fetch exchange rates on initialization
  fetchExchangeRates()

  return {
    ticker,
    exchangeRates,
    isLoading,
    loadTicker,
    fetchExchangeRates,
    getRate
  }
}
