import { ref, onUnmounted, watch, type Ref } from 'vue'
import { createChart, type IChartApi, type ISeriesApi, ColorType } from 'lightweight-charts'
import type { Candle, ChartOptions, APIResponse } from '@/types'

export function useChart(chartRef: Ref<HTMLElement | null>, options: ChartOptions) {
  const chart = ref<IChartApi | null>(null)
  const subCharts = ref<Record<string, IChartApi>>({})
  const candleSeries = ref<ISeriesApi<'Candlestick'> | null>(null)
  const volumeSeries = ref<ISeriesApi<'Histogram'> | null>(null)
  const allCandles = ref<Candle[]>([])
  
  // Data loading states
  const isLoadingMore = ref(false)
  const isLoadingNewer = ref(false)
  const hasMoreData = ref(true)
  const hasNewerData = ref(true)
  const oldestTimestamp = ref<number>(0)
  const newestTimestamp = ref<number>(0)
  
  let chartObserver: ResizeObserver | null = null
  let refreshInterval: number | null = null

  const initChart = (): void => {
    if (!chartRef.value) return

    // Remove existing chart
    if (chart.value) {
      chart.value.remove()
      chart.value = null
    }

    // Create new chart
    chart.value = createChart(chartRef.value, {
      layout: {
        background: { type: ColorType.Solid, color: '#131722' },
        textColor: '#d1d4dc'
      },
      grid: {
        vertLines: { color: '#1e222d' },
        horzLines: { color: '#1e222d' }
      },
      crosshair: {
        mode: 0, // Normal
        vertLine: {
          width: 1,
          style: 2,
          visible: true,
          labelVisible: true
        },
        horzLine: {
          width: 1,
          style: 2,
          visible: true,
          labelVisible: true
        }
      },
      rightPriceScale: {
        borderColor: '#2a2e39'
      },
      timeScale: {
        borderColor: '#2a2e39',
        timeVisible: true,
        secondsVisible: false
      },
      width: chartRef.value.clientWidth,
      height: chartRef.value.clientHeight
    })

    // Add candlestick series
    candleSeries.value = chart.value.addCandlestickSeries({
      upColor: '#26a69a',
      downColor: '#ef5350',
      borderDownColor: '#ef5350',
      borderUpColor: '#26a69a',
      wickDownColor: '#ef5350',
      wickUpColor: '#26a69a'
    })

    // Add volume series
    volumeSeries.value = chart.value.addHistogramSeries({
      color: '#26a69a',
      priceFormat: { type: 'volume' },
      priceScaleId: ''
    })

    volumeSeries.value.priceScale().applyOptions({
      scaleMargins: { top: 0.8, bottom: 0 }
    })

    // Subscribe to visible range changes for auto-loading
    chart.value.timeScale().subscribeVisibleLogicalRangeChange((range) => {
      onVisibleRangeChange(range)
    })

    // Setup resize observer
    chartObserver = new ResizeObserver(entries => {
      if (entries.length === 0 || !chart.value) return
      const { width, height } = entries[0].contentRect
      chart.value.applyOptions({ width, height })
    })
    chartObserver.observe(chartRef.value)
  }

  const loadCandlesticks = async (): Promise<void> => {
    if (options.onLoading) options.onLoading(true)

    try {
      const response = await fetch(
        `/api/candlesticks/?symbol=${options.symbol.value}&bar=${options.bar.value}&limit=500&source=${options.source.value}`
      )
      const result: APIResponse<Candle[]> = await response.json()

      if (result.code === 0 && result.data) {
        allCandles.value = result.data
        
        // Track timestamps for pagination
        if (result.data.length > 0) {
          oldestTimestamp.value = result.data[0].time
          newestTimestamp.value = result.data[result.data.length - 1].time
          hasMoreData.value = result.data.length >= 1000
          hasNewerData.value = true
        }
        
        updateChartData()
        if (chart.value) {
          chart.value.timeScale().fitContent()
        }
        
        // Ensure we have enough history data
        if (allCandles.value.length < 1000 && hasMoreData.value) {
          loadMoreHistory(1000)
        }
      } else {
        if (options.onError) {
          options.onError({ show: true, message: result.error || '加载失败' })
        }
      }
    } catch (err) {
      if (options.onError) {
        options.onError({ show: true, message: '无法连接到服务器' })
      }
    } finally {
      if (options.onLoading) options.onLoading(false)
    }
  }

  const updateChartData = (): void => {
    if (!candleSeries.value || !volumeSeries.value) return

    const candleData = allCandles.value.map(c => ({
      time: c.time as any,
      open: c.open,
      high: c.high,
      low: c.low,
      close: c.close
    }))

    const volumeData = allCandles.value.map(c => ({
      time: c.time as any,
      value: c.volume,
      color: c.close >= c.open ? 'rgba(38, 166, 154, 0.5)' : 'rgba(239, 83, 80, 0.5)'
    }))

    candleSeries.value.setData(candleData)
    volumeSeries.value.setData(volumeData)

    // Update price info
    if (allCandles.value.length > 0 && options.onPriceUpdate) {
      const latest = allCandles.value[allCandles.value.length - 1]
      const changeNum = ((latest.close - latest.open) / latest.open * 100)
      const change = changeNum.toFixed(2)
      const isUp = latest.close >= latest.open
      options.onPriceUpdate(
        latest.close.toLocaleString(),
        changeNum >= 0 ? `+${change}` : change,
        isUp
      )
    }
  }

  const updateLatestData = async (): Promise<void> => {
    if (allCandles.value.length === 0) return

    try {
      const response = await fetch(
        `/api/candlesticks/?symbol=${options.symbol.value}&bar=${options.bar.value}&limit=5&source=${options.source.value}`
      )
      const result: APIResponse<Candle[]> = await response.json()

      if (result.code === 0 && result.data && result.data.length > 0) {
        const newCandles = result.data
        const lastCandle = allCandles.value[allCandles.value.length - 1]

        for (const newCandle of newCandles) {
          if (newCandle.time === lastCandle.time) {
            // Update existing candle
            allCandles.value[allCandles.value.length - 1] = newCandle
            if (candleSeries.value) {
              candleSeries.value.update({
                time: newCandle.time as any,
                open: newCandle.open,
                high: newCandle.high,
                low: newCandle.low,
                close: newCandle.close
              })
            }
          } else if (newCandle.time > lastCandle.time) {
            // Add new candle
            allCandles.value.push(newCandle)
            if (candleSeries.value) {
              candleSeries.value.update({
                time: newCandle.time as any,
                open: newCandle.open,
                high: newCandle.high,
                low: newCandle.low,
                close: newCandle.close
              })
            }
          }
        }
      }
    } catch (err) {
      console.error('Failed to update latest data:', err)
    }
  }

  const onVisibleRangeChange = (range: any): void => {
    if (!range || allCandles.value.length === 0) return
    
    // Load more history when scrolling to the left
    if (hasMoreData.value && !isLoadingMore.value && range.from < 0) {
      loadMoreHistory(Math.abs(Math.floor(range.from)) + 1000)
    } else if (hasMoreData.value && !isLoadingMore.value && range.from < 1000) {
      loadMoreHistory(1000)
    }
    
    // Load newer data when scrolling to the right
    if (range.to > allCandles.value.length - 500 && hasNewerData.value && !isLoadingNewer.value) {
      loadMoreNewerUntilEnough()
    }
    
    updateNoDataOverlay()
  }

  const updateNoDataOverlay = (): { show: boolean; width: number } => {
    if (!chart.value || allCandles.value.length === 0) {
      return { show: false, width: 0 }
    }
    
    // Calculate the width of the no-data area
    if (!hasMoreData.value && allCandles.value.length > 0) {
      const firstCandleTime = allCandles.value[0].time
      const x = chart.value.timeScale().timeToCoordinate(firstCandleTime as any)
      
      if (x !== null && x > 0) {
        return { show: true, width: x }
      }
    }
    
    return { show: false, width: 0 }
  }

  const loadMoreHistory = async (count: number): Promise<void> => {
    if (isLoadingMore.value || !hasMoreData.value) return
    
    isLoadingMore.value = true
    try {
      const before = oldestTimestamp.value * 1000
      const limit = Math.min(count, 2000)
      const response = await fetch(
        `/api/candlesticks/?symbol=${options.symbol.value}&bar=${options.bar.value}&limit=${limit}&source=${options.source.value}&before=${before}`
      )
      const result: APIResponse<Candle[]> = await response.json()
      
      if (result.code === 0 && result.data && result.data.length > 0) {
        const newCandles = result.data
        allCandles.value = [...newCandles, ...allCandles.value]
        allCandles.value.sort((a, b) => a.time - b.time)
        oldestTimestamp.value = allCandles.value[0].time
        updateChartData()
      } else {
        hasMoreData.value = false
      }
    } catch (err) {
      console.error('Failed to load more history:', err)
    } finally {
      isLoadingMore.value = false
    }
  }

  const loadMoreNewerUntilEnough = async (): Promise<void> => {
    if (isLoadingNewer.value || !hasNewerData.value) return
    
    isLoadingNewer.value = true
    let loadedCount = 0
    
    try {
      while (hasNewerData.value && loadedCount < 2000) {
        const afterTs = newestTimestamp.value * 1000
        const response = await fetch(
          `/api/candlesticks/?symbol=${options.symbol.value}&bar=${options.bar.value}&limit=500&source=${options.source.value}&after=${afterTs}`
        )
        const result: APIResponse<Candle[]> = await response.json()
        
        if (result.code === 0 && result.data && result.data.length > 0) {
          const newCandles = result.data
          const existingTimes = new Set(allCandles.value.map(c => c.time))
          const uniqueCandles = newCandles.filter(c => !existingTimes.has(c.time))
          
          if (uniqueCandles.length > 0) {
            allCandles.value = [...allCandles.value, ...uniqueCandles]
            allCandles.value.sort((a, b) => a.time - b.time)
            newestTimestamp.value = allCandles.value[allCandles.value.length - 1].time
            loadedCount += uniqueCandles.length
            updateChartData()
          } else {
            hasNewerData.value = false
            break
          }
          
          if (newCandles.length < 500) {
            hasNewerData.value = false
            break
          }
        } else {
          hasNewerData.value = false
          break
        }
      }
    } catch (err) {
      console.error('Failed to load newer data:', err)
    } finally {
      isLoadingNewer.value = false
    }
  }

  const retryLoad = (): void => {
    initChart()
    loadCandlesticks()
  }

  // Watch for symbol/bar changes
  watch([() => options.symbol.value, () => options.bar.value], () => {
    // Reset loading states
    hasMoreData.value = true
    hasNewerData.value = true
    isLoadingMore.value = false
    isLoadingNewer.value = false
    
    initChart()
    loadCandlesticks()
  })

  onUnmounted(() => {
    if (refreshInterval) clearInterval(refreshInterval)
    if (chartObserver) chartObserver.disconnect()
    if (chart.value) chart.value.remove()
  })

  return {
    chart,
    subCharts,
    candleSeries,
    volumeSeries,
    allCandles,
    isLoadingMore,
    isLoadingNewer,
    hasMoreData,
    hasNewerData,
    initChart,
    loadCandlesticks,
    updateChartData,
    updateLatestData,
    loadMoreHistory,
    loadMoreNewerUntilEnough,
    updateNoDataOverlay,
    retryLoad
  }
}
