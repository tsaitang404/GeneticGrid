import { ref, onUnmounted, watch, type Ref } from 'vue'
import { createChart, type IChartApi, type ISeriesApi, ColorType } from 'lightweight-charts'
import type { Candle, ChartOptions, APIResponse } from '@/types'

export function useChart(chartRef: Ref<HTMLElement | null>, options: ChartOptions) {
  const chart = ref<IChartApi | null>(null)
  const subCharts = ref<Record<string, IChartApi>>({})
  const candleSeries = ref<ISeriesApi<'Candlestick'> | null>(null)
  const lineSeries = ref<ISeriesApi<'Line'> | null>(null)
  const volumeSeries = ref<ISeriesApi<'Histogram'> | null>(null)
  const latestPriceLine = ref<ReturnType<NonNullable<typeof candleSeries.value>['createPriceLine']> | ReturnType<NonNullable<typeof lineSeries.value>['createPriceLine']> | null>(null)
  const allCandles = ref<Candle[]>([])
  const isTimelineMode = ref<boolean>(false)
  
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
  let latestPriceLabelEl: HTMLDivElement | null = null
  let latestPriceValue: number | null = null
  const axisInteractionHandlers: Array<{ type: keyof HTMLElementEventMap; handler: EventListener }> = []

  // Helper function to check if current bar is timeline mode
  const checkIsTimelineMode = (bar: string): boolean => {
    const barLower = bar.toLowerCase()
    return barLower === 'timeline' || barLower === '分时' || barLower === 'tick'
  }

  // Helper function to get backend bar parameter
  const getBackendBar = (bar: string): string => {
    // Map Chinese/special timeframes to backend format
    if (checkIsTimelineMode(bar)) {
      return '1s' // Use 1s data for timeline display with second precision
    }
    return bar
  }

  const formatAxisPrice = (price: number): string => {
    if (!Number.isFinite(price)) return '--'
    if (price >= 100000) return price.toLocaleString()
    if (price >= 1000) return price.toLocaleString(undefined, { maximumFractionDigits: 2 })
    if (price >= 1) return price.toFixed(2)
    return price.toPrecision(4)
  }

  const ensurePriceAxisLabelElement = (): HTMLDivElement | null => {
    if (latestPriceLabelEl && latestPriceLabelEl.isConnected) return latestPriceLabelEl
    if (!chartRef.value) return null
    const el = document.createElement('div')
    el.className = 'latest-price-axis-label'
    el.style.display = 'none'
    chartRef.value.appendChild(el)
    latestPriceLabelEl = el
    return latestPriceLabelEl
  }

  const removeLatestPriceAxisLabel = (): void => {
    if (latestPriceLabelEl && latestPriceLabelEl.parentElement) {
      latestPriceLabelEl.parentElement.removeChild(latestPriceLabelEl)
    }
    latestPriceLabelEl = null
  }

  const updatePriceAxisLabel = (price: number): void => {
    const el = ensurePriceAxisLabelElement()
    const activeSeries = isTimelineMode.value ? lineSeries.value : candleSeries.value
    if (!el || !activeSeries || !chart.value) return
    
    const coordinate = activeSeries.priceToCoordinate(price)
    if (coordinate === null || coordinate === undefined) {
      el.style.display = 'none'
      return
    }
    
    // Get chart dimensions to clamp the label within bounds
    const chartHeight = chart.value.options().height as number
    const labelHeight = 20 // Approximate label height
    const topMargin = 5
    const bottomMargin = 28 // Reserve space for time axis
    
    // Clamp coordinate to visible chart area (convert Coordinate type to number)
    const clampedY = Math.max(topMargin, Math.min(chartHeight - bottomMargin - labelHeight, coordinate as number))
    
    el.style.display = 'block'
    el.style.top = `${clampedY}px`
    el.textContent = formatAxisPrice(price)
  }

  const refreshPriceAxisLabel = (): void => {
    if (latestPriceValue !== null) {
      updatePriceAxisLabel(latestPriceValue)
    }
  }

  const attachAxisInteractionListeners = (): void => {
    if (!chartRef.value) return
    const events: Array<keyof HTMLElementEventMap> = ['wheel', 'mouseup', 'mouseleave', 'touchend']
    events.forEach((type) => {
      const handler: EventListener = () => {
        window.requestAnimationFrame(() => refreshPriceAxisLabel())
      }
      chartRef.value?.addEventListener(type, handler)
      axisInteractionHandlers.push({ type, handler })
    })
  }

  const detachAxisInteractionListeners = (): void => {
    if (!chartRef.value || axisInteractionHandlers.length === 0) return
    axisInteractionHandlers.splice(0).forEach(({ type, handler }) => {
      chartRef.value?.removeEventListener(type, handler)
    })
  }

  // Create or update a labeled latest price line on right axis
  const createOrUpdateLatestPriceLine = (price: number): void => {
    // Remove existing line
    if (latestPriceLine.value) {
      if (isTimelineMode.value && lineSeries.value) {
        lineSeries.value.removePriceLine(latestPriceLine.value)
      } else if (candleSeries.value) {
        candleSeries.value.removePriceLine(latestPriceLine.value)
      }
      latestPriceLine.value = null
    }
    
    const opts = {
      price,
      color: '#FFD54F',
      lineStyle: 2 as const, // Dashed line
      lineWidth: 2 as const,
      axisLabelVisible: true,
      axisLabelColor: '#FFD54F', // Background color
      axisLabelTextColor: '#000000', // Text color
      title: ''
    }
    
    latestPriceLine.value = isTimelineMode.value && lineSeries.value
      ? lineSeries.value.createPriceLine(opts)
      : candleSeries.value?.createPriceLine(opts) || null
      
    latestPriceValue = price
    updatePriceAxisLabel(price)
  }

  const initChart = (): void => {
    if (!chartRef.value) return

    // Remove existing chart
    if (chart.value) {
      removeLatestPriceAxisLabel()
      detachAxisInteractionListeners()
      chart.value.remove()
      chart.value = null
    }

    // 清空所有数据状态，确保切换时不会有旧数据残留
    allCandles.value = []
    oldestTimestamp.value = null
    newestTimestamp.value = null
    hasMoreData.value = true
    hasNewerData.value = true
    latestPriceLine.value = null
    latestPriceValue = null

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
        borderColor: '#2a2e39',
        visible: true,
        scaleMargins: {
          top: 0.1,
          bottom: 0.1
        }
      },
      timeScale: {
        borderColor: '#2a2e39',
        timeVisible: true,
        secondsVisible: true // Always show full time format
      },
      width: chartRef.value.clientWidth,
      height: chartRef.value.clientHeight
    })

    // Determine if we should use timeline (line) mode
    isTimelineMode.value = checkIsTimelineMode(options.bar.value)
    
    // Adjust spacing based on mode
    if (isTimelineMode.value) {
      // Timeline mode: tighter spacing for continuous line
      chart.value.timeScale().applyOptions({
        rightOffset: 2,
        barSpacing: 3,
        minBarSpacing: 0.5
      })
      console.log('📊 Timeline mode activated')
    } else {
      // Candlestick mode: normal spacing
      chart.value.timeScale().applyOptions({
        rightOffset: 2,
        barSpacing: 6,
        minBarSpacing: 3
      })
    }

    // Add price series (candlestick or line based on mode)
    if (isTimelineMode.value) {
      // Timeline mode: use line chart
      lineSeries.value = chart.value.addLineSeries({
        color: '#2962FF',
        lineWidth: 2,
        crosshairMarkerVisible: true,
        crosshairMarkerRadius: 4,
        lastValueVisible: true,
        priceLineVisible: true,
        priceLineWidth: 2,
        priceLineStyle: 2, // Dashed line
        priceLineColor: '#2962FF',
        priceFormat: {
          type: 'price',
          precision: 2,
          minMove: 0.01
        }
      })
      candleSeries.value = null
    } else {
      // Candlestick mode
      candleSeries.value = chart.value.addCandlestickSeries({
        upColor: '#26a69a',
        downColor: '#ef5350',
        borderDownColor: '#ef5350',
        borderUpColor: '#26a69a',
        wickDownColor: '#ef5350',
        wickUpColor: '#26a69a',
        lastValueVisible: true,
        priceLineVisible: true,
        priceLineWidth: 2,
        priceLineStyle: 2, // Dashed line
        priceFormat: {
          type: 'price',
          precision: 2,
          minMove: 0.01
        }
      })
      lineSeries.value = null
    }

    

    // Add volume series on a separate overlay
    volumeSeries.value = chart.value.addHistogramSeries({
      color: '#26a69a',
      priceFormat: { type: 'volume' },
      priceScaleId: 'volume', // Use separate price scale for volume
      lastValueVisible: false, // Hide volume label
      priceLineVisible: false
    })

    volumeSeries.value.priceScale().applyOptions({
      scaleMargins: { top: 0.8, bottom: 0 },
      visible: false // Hide the volume price scale completely
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
      refreshPriceAxisLabel()
    })
    chartObserver.observe(chartRef.value)
    attachAxisInteractionListeners()
  }

  const loadCandlesticks = async (): Promise<void> => {
    if (options.onLoading) options.onLoading(true)

    try {
      const currentBar = options.bar.value
      const backendBar = getBackendBar(currentBar)
      const isTimeline = checkIsTimelineMode(currentBar)
      
      // For timeline mode, limit to today's data only (or recent period)
      let limit = 2000
      if (isTimeline) {
        // For 1s data: 1 day = 86400 seconds, use smaller limit
        limit = Math.min(500, 2000) // Start with less data for intraday view
      }
      
      const response = await fetch(
        `/api/candlesticks/?symbol=${options.symbol.value}&bar=${backendBar}&limit=${limit}&source=${options.source.value}`
      )
      const result: APIResponse<Candle[]> = await response.json()

      if (result.code === 0 && result.data) {
        allCandles.value = result.data
        
        // Track timestamps for pagination (store as seconds)
        if (result.data.length > 0) {
          oldestTimestamp.value = result.data[0].time as number
          newestTimestamp.value = result.data[result.data.length - 1].time as number
          hasMoreData.value = true
          hasNewerData.value = true
        } else {
          hasMoreData.value = false
          hasNewerData.value = false
        }
        
        updateChartData()
        // Ensure latest price line is visible with label
        if (allCandles.value.length > 0) {
          const latest = allCandles.value[allCandles.value.length - 1]
          createOrUpdateLatestPriceLine(latest.close)
        }
        if (chart.value) {
          chart.value.timeScale().fitContent()
        }
        
        // Preload more history data for smooth scrolling (but not for timeline)
        if (!isTimeline && allCandles.value.length < 10000 && hasMoreData.value) {
          console.log('🔄 Preloading additional 10000 candles for buffer...')
          // Use setTimeout to avoid blocking initial render
          setTimeout(() => {
            loadMoreHistory(10000)
          }, 100)
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
    if ((!candleSeries.value && !lineSeries.value) || !volumeSeries.value || !chart.value) return

    // Full update: replace all data
    // Note: setData() will preserve the current scroll position automatically
    
    if (isTimelineMode.value && lineSeries.value) {
      // Timeline mode: use close price for line chart
      const lineData = allCandles.value.map(c => ({
        time: c.time as any,
        value: c.close
      }))
      lineSeries.value.setData(lineData)
    } else if (candleSeries.value) {
      // Candlestick mode
      const candleData = allCandles.value.map(c => ({
        time: c.time as any,
        open: c.open,
        high: c.high,
        low: c.low,
        close: c.close
      }))
      candleSeries.value.setData(candleData)
    }

    const volumeData = allCandles.value.map(c => ({
      time: c.time as any,
      value: c.volume,
      color: c.close >= c.open ? 'rgba(38, 166, 154, 0.5)' : 'rgba(239, 83, 80, 0.5)'
    }))

    volumeSeries.value.setData(volumeData)

    // Update price info
    if (allCandles.value.length > 0 && options.onPriceUpdate) {
      const latest = allCandles.value[allCandles.value.length - 1]
      const price = latest.close
      
      // Update latest price line
      if (price !== undefined && price !== null) {
        createOrUpdateLatestPriceLine(price)
      }
      
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
    if (allCandles.value.length === 0 || !newestTimestamp.value) return

    try {
      // Use 'after' parameter to get only newer data than we have
      const afterMs = newestTimestamp.value * 1000
      const backendBar = getBackendBar(options.bar.value)
      const response = await fetch(
        `/api/candlesticks/?symbol=${options.symbol.value}&bar=${backendBar}&limit=100&source=${options.source.value}&after=${afterMs}`
      )
      const result: APIResponse<Candle[]> = await response.json()

      if (result.code === 0 && result.data && result.data.length > 0) {
        const newCandles = result.data
        const lastCandle = allCandles.value[allCandles.value.length - 1]
        let hasNewData = false

        for (const newCandle of newCandles) {
          if (newCandle.time === lastCandle.time) {
            // Update existing candle (current period may still be updating)
            allCandles.value[allCandles.value.length - 1] = newCandle
            
            if (isTimelineMode.value && lineSeries.value && volumeSeries.value) {
              // Timeline mode
              lineSeries.value.update({
                time: newCandle.time as any,
                value: newCandle.close
              })
              volumeSeries.value.update({
                time: newCandle.time as any,
                value: newCandle.volume,
                color: newCandle.close >= newCandle.open ? 'rgba(38, 166, 154, 0.5)' : 'rgba(239, 83, 80, 0.5)'
              })
            } else if (candleSeries.value && volumeSeries.value) {
              // Candlestick mode
              candleSeries.value.update({
                time: newCandle.time as any,
                open: newCandle.open,
                high: newCandle.high,
                low: newCandle.low,
                close: newCandle.close
              })
              volumeSeries.value.update({
                time: newCandle.time as any,
                value: newCandle.volume,
                color: newCandle.close >= newCandle.open ? 'rgba(38, 166, 154, 0.5)' : 'rgba(239, 83, 80, 0.5)'
              })
            }
            hasNewData = true
          } else if (newCandle.time > lastCandle.time) {
            // Add new candle (new period started)
            allCandles.value.push(newCandle)
            
            if (isTimelineMode.value && lineSeries.value && volumeSeries.value) {
              // Timeline mode
              lineSeries.value.update({
                time: newCandle.time as any,
                value: newCandle.close
              })
              volumeSeries.value.update({
                time: newCandle.time as any,
                value: newCandle.volume,
                color: newCandle.close >= newCandle.open ? 'rgba(38, 166, 154, 0.5)' : 'rgba(239, 83, 80, 0.5)'
              })
            } else if (candleSeries.value && volumeSeries.value) {
              // Candlestick mode
              candleSeries.value.update({
                time: newCandle.time as any,
                open: newCandle.open,
                high: newCandle.high,
                low: newCandle.low,
                close: newCandle.close
              })
              volumeSeries.value.update({
                time: newCandle.time as any,
                value: newCandle.volume,
                color: newCandle.close >= newCandle.open ? 'rgba(38, 166, 154, 0.5)' : 'rgba(239, 83, 80, 0.5)'
              })
            }
            newestTimestamp.value = newCandle.time as number
            hasNewData = true
          }
        }
        
        // Update price info
        if (hasNewData && options.onPriceUpdate) {
          const latest = allCandles.value[allCandles.value.length - 1]
          const price = latest.close
          
          // Update latest price line
          if (price !== undefined && price !== null) {
            createOrUpdateLatestPriceLine(price)
          }
          
          const changeNum = ((latest.close - latest.open) / latest.open * 100)
          const change = changeNum.toFixed(2)
          options.onPriceUpdate(
            latest.close.toLocaleString(),
            changeNum >= 0 ? `+${change}` : change,
            latest.close >= latest.open
          )
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
    
    // Much larger buffer zone to trigger preload earlier (100% of visible range, min 1000, max 3000)
    const bufferZone = Math.max(1000, Math.min(3000, Math.floor(visibleRange * 1.0)))
    
    // Clear existing debounce timer
    if (loadDebounceTimer) {
      clearTimeout(loadDebounceTimer)
      loadDebounceTimer = null
    }
    
    // Determine if we should load
    const shouldLoadHistory = hasMoreData.value && !isLoadingMore.value && visibleFromIndex < bufferZone
    const shouldLoadNewer = hasNewerData.value && !isLoadingNewer.value && visibleToIndex > allCandles.value.length - bufferZone
    
    if (shouldLoadHistory || shouldLoadNewer) {
      // Debounce: wait 50ms to avoid loading during active dragging (reduced for faster response)
      loadDebounceTimer = window.setTimeout(() => {
        // Double-check conditions haven't changed during debounce
        if (shouldLoadHistory && !isLoadingMore.value && hasMoreData.value) {
          // Calculate gap: how much data is missing before the start
          const gap = Math.abs(visibleFromIndex)
          
          // Aggressive load count for smooth dragging:
          // 1. If gap is negative (we're in the data), load 8x visible range
          // 2. If gap exists, load gap + 10x visible range to ensure smooth scrolling
          // 3. Minimum 8000 (for generous buffer), maximum 15000
          let loadCount: number
          if (gap <= 0) {
            // Normal scrolling near beginning - load generously
            loadCount = Math.max(8000, visibleRange * 8)
          } else {
            // Large gap detected (fast drag or zoom out) - load even more
            loadCount = Math.max(10000, gap + visibleRange * 10)
          }
          
          // Cap at 15000 (backend cache makes this fast)
          loadCount = Math.min(15000, Math.ceil(loadCount))
          
          console.log('🔄 Loading history - visible:', visibleFromIndex, 'range:', visibleRange, 'gap:', gap, 'loading:', loadCount)
          loadMoreHistory(loadCount)
        } else if (shouldLoadNewer && !isLoadingNewer.value && hasNewerData.value) {
          console.log('🔄 Loading newer - visible:', visibleToIndex, '/', allCandles.value.length)
          loadMoreNewerUntilEnough()
        }
        loadDebounceTimer = null
      }, 100)
    }
    
    updateNoDataOverlay()
    refreshPriceAxisLabel()
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
      const limit = Math.min(count, 15000) // Increased max to 15000 (backend has cache)
      const backendBar = getBackendBar(options.bar.value)
      const url = `/api/candlesticks/?symbol=${options.symbol.value}&bar=${backendBar}&limit=${limit}&source=${options.source.value}&before=${beforeMs}`
      
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
          
          console.log(`✅ Loaded ${uniqueNewCandles.length}/${result.data.length} unique candles in ${loadTime}ms`)
          console.log(`   Array: ${oldLength} → ${newLength}, Oldest: ${new Date((oldestTime as number) * 1000).toISOString()} → ${new Date(newOldestTime as number * 1000).toISOString()}`)
          console.log(`   hasMoreData: ${hasMoreData.value} (got ${result.data.length}/${limit})`)
          
          // Update chart data - setData will preserve user's current view position
          updateChartData()
          // As long as we receive any unique candles we still assume there may be more history
          hasMoreData.value = true
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
    
    try {
      // Request a large batch of newer data (up to current time)
      const afterMs = newestTimestamp.value * 1000
      const backendBar = getBackendBar(options.bar.value)
      const response = await fetch(
        `/api/candlesticks/?symbol=${options.symbol.value}&bar=${backendBar}&limit=2000&source=${options.source.value}&after=${afterMs}`
      )
      const result: APIResponse<Candle[]> = await response.json()
      
      if (result.code === 0 && result.data && result.data.length > 0) {
        const newCandles = result.data
        const existingTimes = new Set(allCandles.value.map(c => c.time))
        const uniqueCandles = newCandles.filter(c => !existingTimes.has(c.time))
        
        if (uniqueCandles.length > 0) {
          const oldLength = allCandles.value.length
          allCandles.value = [...allCandles.value, ...uniqueCandles]
          allCandles.value.sort((a, b) => (a.time as number) - (b.time as number))
          newestTimestamp.value = allCandles.value[allCandles.value.length - 1].time as number
          
          console.log(`✅ Loaded ${uniqueCandles.length} newer candles (${oldLength} → ${allCandles.value.length})`)
          updateChartData()
        }
        
        // If we got less than requested, we've likely reached the present
        hasNewerData.value = result.data.length >= 1500
      } else {
        console.log('❌ No newer data available')
        hasNewerData.value = false
      }
    } catch (err) {
      console.error('❌ Failed to load newer data:', err)
    } finally {
      isLoadingNewer.value = false
    }
  }

  const retryLoad = (): void => {
    initChart()
    loadCandlesticks()
  }

  // Start auto-refresh for latest data
  const startAutoRefresh = (): void => {
    if (refreshInterval) clearInterval(refreshInterval)
    
    // Determine refresh interval based on bar timeframe
    let intervalMs = 5000 // Default 5 seconds
    const bar = options.bar.value.toLowerCase()
    
    // Parse the timeframe
    if (bar === 'timeline' || bar === '分时' || bar === 'tick') {
      // Timeline/tick mode: refresh every 1-2 seconds for real-time price
      intervalMs = 1000
    } else if (bar.includes('s')) {
      // For second bars (1s, 5s, etc.), refresh at half the period or 500ms minimum
      const seconds = parseInt(bar.replace(/[^0-9]/g, '')) || 1
      intervalMs = Math.max(500, seconds * 500) // Half period, min 500ms
    } else if (bar.includes('m')) {
      // For minute bars, refresh based on the period
      const minutes = parseInt(bar.replace(/[^0-9]/g, '')) || 1
      if (minutes === 1) {
        intervalMs = 2000 // 1m: refresh every 2s
      } else if (minutes <= 5) {
        intervalMs = 5000 // 5m: refresh every 5s
      } else if (minutes <= 15) {
        intervalMs = 10000 // 15m: refresh every 10s
      } else {
        intervalMs = 30000 // 30m+: refresh every 30s
      }
    } else if (bar.includes('h')) {
      // For hour bars, refresh every 30-60 seconds
      const hours = parseInt(bar.replace(/[^0-9]/g, '')) || 1
      intervalMs = hours >= 4 ? 60000 : 30000
    } else if (bar.includes('d')) {
      // For day bars, refresh every 2 minutes
      intervalMs = 120000
    } else if (bar.includes('w') || bar.includes('M')) {
      // For week/month bars, refresh every 5 minutes
      intervalMs = 300000
    }
    
    refreshInterval = window.setInterval(() => {
      updateLatestData()
    }, intervalMs)
    
    console.log(`🔄 Auto-refresh started: ${bar} → ${intervalMs}ms interval (${(intervalMs / 1000).toFixed(1)}s)`)
  }

  // Watch for symbol/bar changes
  watch([() => options.symbol.value, () => options.bar.value], () => {
    // Reset loading states
    hasMoreData.value = true
    hasNewerData.value = true
    isLoadingMore.value = false
    isLoadingNewer.value = false
    
    // Stop old refresh timer
    if (refreshInterval) {
      clearInterval(refreshInterval)
      refreshInterval = null
    }
    
    initChart()
    loadCandlesticks().then(() => {
      // Start auto-refresh after initial load
      startAutoRefresh()
    })
  })

  onUnmounted(() => {
    if (refreshInterval) clearInterval(refreshInterval)
    if (chartObserver) chartObserver.disconnect()
    if (chart.value) chart.value.remove()
    removeLatestPriceAxisLabel()
    detachAxisInteractionListeners()
  })

  // Initialize
  const initialize = async (): Promise<void> => {
    initChart()
    await loadCandlesticks()
    startAutoRefresh()
  }

  return {
    chart,
    subCharts,
    candleSeries,
    lineSeries,
    volumeSeries,
    allCandles,
    isLoadingMore,
    isLoadingNewer,
    hasMoreData,
    hasNewerData,
    isTimelineMode,
    initialize,
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
