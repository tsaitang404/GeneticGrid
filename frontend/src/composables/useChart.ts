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
  let isSyncingTimeScale = false // Prevent circular time scale sync
  let loadDebounceTimer: number | null = null // Debounce timer for loading

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
      watermark: {
        visible: false
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

    // Subscribe to visible range changes for auto-loading and syncing sub-charts
    chart.value.timeScale().subscribeVisibleLogicalRangeChange((range) => {
      // Prevent infinite loop from sub-chart sync
      if (isSyncingTimeScale) return
      
      onVisibleRangeChange(range)
      
      // Sync all sub-charts time scale with main chart
      if (range) {
        isSyncingTimeScale = true
        Object.values(subCharts.value).forEach(subChart => {
          if (subChart) {
            subChart.timeScale().setVisibleLogicalRange(range)
          }
        })
        isSyncingTimeScale = false
      }
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
        
        // Track timestamps for pagination (store as seconds)
        if (result.data.length > 0) {
          oldestTimestamp.value = result.data[0].time as number
          newestTimestamp.value = result.data[result.data.length - 1].time as number
          hasMoreData.value = result.data.length >= 500
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
    if (!candleSeries.value || !volumeSeries.value || !chart.value) return

    // Full update: replace all data
    // Note: setData() will preserve the current scroll position automatically
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
    if (!range || !chart.value || allCandles.value.length === 0) return
    
    // range.from and range.to are logical indices
    const visibleFromIndex = Math.max(0, Math.floor(range.from || 0))
    const visibleToIndex = Math.min(allCandles.value.length - 1, Math.ceil(range.to || allCandles.value.length - 1))
    const visibleRange = visibleToIndex - visibleFromIndex
    
    // Dynamic buffer zone based on visible range (40% of visible candles, min 100, max 1000)
    const bufferZone = Math.max(100, Math.min(1000, Math.floor(visibleRange * 0.4)))
    
    // Clear existing debounce timer
    if (loadDebounceTimer) {
      clearTimeout(loadDebounceTimer)
      loadDebounceTimer = null
    }
    
    // Determine if we should load
    const shouldLoadHistory = hasMoreData.value && !isLoadingMore.value && visibleFromIndex < bufferZone
    const shouldLoadNewer = hasNewerData.value && !isLoadingNewer.value && visibleToIndex > allCandles.value.length - bufferZone
    
    if (shouldLoadHistory || shouldLoadNewer) {
      // Debounce: wait 200ms to avoid loading during active dragging
      loadDebounceTimer = window.setTimeout(() => {
        // Double-check conditions haven't changed during debounce
        if (shouldLoadHistory && !isLoadingMore.value && hasMoreData.value) {
          // Calculate gap: how much data is missing before the start
          const gap = Math.abs(visibleFromIndex)
          
          // Smart load count calculation:
          // 1. If gap is negative (we're in the data), load 3x visible range
          // 2. If gap exists, load gap + 4x visible range to ensure smooth scrolling
          // 3. Minimum 2000 (for small intervals), maximum 8000
          let loadCount: number
          if (gap <= 0) {
            // Normal scrolling near beginning
            loadCount = Math.max(2000, visibleRange * 3)
          } else {
            // Large gap detected (fast drag or zoom out)
            loadCount = Math.max(3000, gap + visibleRange * 4)
          }
          
          // Cap at 8000 to avoid overwhelming the server
          loadCount = Math.min(8000, Math.ceil(loadCount))
          
          console.log('🔄 Loading history - visible:', visibleFromIndex, 'range:', visibleRange, 'gap:', gap, 'loading:', loadCount)
          loadMoreHistory(loadCount)
        } else if (shouldLoadNewer && !isLoadingNewer.value && hasNewerData.value) {
          console.log('🔄 Loading newer - visible:', visibleToIndex, '/', allCandles.value.length)
          loadMoreNewerUntilEnough()
        }
        loadDebounceTimer = null
      }, 200)
    }
    
    updateNoDataOverlay()
  }

  const updateNoDataOverlay = (): { show: boolean; width: number } => {
    if (!chart.value || allCandles.value.length === 0) {
      return { show: false, width: 0 }
    }
    
    // Only show "no data" area when we've confirmed there's no more historical data
    // The overlay should follow the first candle position
    if (!hasMoreData.value && allCandles.value.length > 0) {
      const firstCandleTime = allCandles.value[0].time
      const x = chart.value.timeScale().timeToCoordinate(firstCandleTime as any)
      
      // x is the pixel position of the first candle
      // If x > 0, there's empty space to the left that should show "no data"
      if (x !== null && x > 0) {
        console.log(`🚧 No more data overlay: width=${Math.floor(x)}px, first candle at ${new Date(firstCandleTime as number * 1000).toLocaleString()}`)
        return { show: true, width: Math.floor(x) }
      }
    }
    
    return { show: false, width: 0 }
  }

  const loadMoreHistory = async (count: number): Promise<void> => {
    if (isLoadingMore.value || !hasMoreData.value) {
      return
    }
    
    isLoadingMore.value = true
    const startTime = Date.now()
    
    try {
      // oldestTimestamp is in seconds, API expects milliseconds
      const beforeMs = oldestTimestamp.value * 1000
      const limit = Math.min(count, 8000) // Increased max to 8000
      const url = `/api/candlesticks/?symbol=${options.symbol.value}&bar=${options.bar.value}&limit=${limit}&source=${options.source.value}&before=${beforeMs}`
      
      const response = await fetch(url)
      const result: APIResponse<Candle[]> = await response.json()
      
      if (result.code === 0 && result.data && result.data.length > 0) {
        const loadTime = Date.now() - startTime
        const newCandles = result.data
        
        // Prepend new data and remove duplicates
        const existingTimes = new Set(allCandles.value.map(c => c.time))
        const uniqueNewCandles = newCandles.filter(c => !existingTimes.has(c.time))
        
        if (uniqueNewCandles.length > 0) {
          const oldLength = allCandles.value.length
          const oldestTime = allCandles.value[0]?.time
          
          allCandles.value = [...uniqueNewCandles, ...allCandles.value]
          allCandles.value.sort((a, b) => (a.time as number) - (b.time as number))
          
          const newLength = allCandles.value.length
          const newOldestTime = allCandles.value[0].time
          
          oldestTimestamp.value = newOldestTime as number
          
          // Only has more data if we got close to what we requested
          // If we got less than 80% of requested, probably reached the limit
          hasMoreData.value = result.data.length >= Math.min(limit * 0.8, 500)
          
          console.log(`✅ Loaded ${uniqueNewCandles.length}/${result.data.length} unique candles in ${loadTime}ms`)
          console.log(`   Array: ${oldLength} → ${newLength}, Oldest: ${new Date((oldestTime as number) * 1000).toISOString()} → ${new Date(newOldestTime as number * 1000).toISOString()}`)
          console.log(`   hasMoreData: ${hasMoreData.value} (got ${result.data.length}/${limit})`)
          
          // Update chart data - setData will preserve user's current view position
          updateChartData()
        } else {
          console.log('⚠️ All loaded data was duplicate')
          hasMoreData.value = false
        }
      } else {
        console.log('❌ No more history data from server')
        hasMoreData.value = false
      }
    } catch (err) {
      console.error('❌ Failed to load history:', err)
      // Don't set hasMoreData to false on network error, might be temporary
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
