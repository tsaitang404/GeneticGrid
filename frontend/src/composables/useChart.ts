import { ref, onUnmounted, watch, type Ref } from 'vue'
import { createChart, type IChartApi, type ISeriesApi, ColorType } from 'lightweight-charts'
import type { Candle, ChartOptions, APIResponse, SymbolMode } from '@/types'
import { useTimeScaleSync } from './useTimeScaleSync'

export function useChart(chartRef: Ref<HTMLElement | null>, options: ChartOptions) {
  const { isSyncingTimeScale } = useTimeScaleSync()
  const chart = ref<IChartApi | null>(null)
  const subCharts = ref<Record<string, IChartApi>>({})
  const candleSeries = ref<ISeriesApi<'Candlestick'> | null>(null)
  const lineSeries = ref<ISeriesApi<'Line'> | null>(null)
  const volumeSeries = ref<ISeriesApi<'Histogram'> | null>(null)
  const latestPriceLine = ref<ReturnType<NonNullable<typeof candleSeries.value>['createPriceLine']> | ReturnType<NonNullable<typeof lineSeries.value>['createPriceLine']> | null>(null)
  const allCandles = ref<Candle[]>([])
  const isTimelineMode = ref<boolean>(false)

  const DEFAULT_UP_COLOR = '#26a69a'
  const DEFAULT_DOWN_COLOR = '#ef5350'
  const DEFAULT_VOLUME_UP_COLOR = 'rgba(38, 166, 154, 0.5)'
  const DEFAULT_VOLUME_DOWN_COLOR = 'rgba(239, 83, 80, 0.5)'

  const getUpColor = (): string => options.colors?.up.value ?? DEFAULT_UP_COLOR
  const getDownColor = (): string => options.colors?.down.value ?? DEFAULT_DOWN_COLOR
  const getVolumeUpColor = (): string => options.colors?.volumeUp.value ?? DEFAULT_VOLUME_UP_COLOR
  const getVolumeDownColor = (): string => options.colors?.volumeDown.value ?? DEFAULT_VOLUME_DOWN_COLOR
  
  // Data loading states
  const isLoadingMore = ref(false)
  const isLoadingNewer = ref(false)
  const hasMoreData = ref(true)
  const hasNewerData = ref(true)
  const oldestTimestamp = ref<number | null>(null)
  const newestTimestamp = ref<number | null>(null)
  
  let chartObserver: ResizeObserver | null = null
  let refreshInterval: number | null = null
  let loadDebounceTimer: number | null = null // Debounce timer for loading
  let latestPriceLabelEl: HTMLDivElement | null = null
  let latestPriceValue: number | null = null
  const axisInteractionHandlers: Array<{ type: keyof HTMLElementEventMap; handler: EventListener }> = []

  // Helper function to check if current bar is timeline mode
  const checkIsTimelineMode = (bar: string): boolean => {
    const barLower = bar.toLowerCase()
    return barLower === 'timeline' || barLower === '分时' || barLower === 'tick'
  }

  const getModeParam = (): SymbolMode => {
    return (options.mode?.value ?? 'spot') as SymbolMode
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

  const applySeriesColors = (): void => {
    const upColor = getUpColor()
    const downColor = getDownColor()

    if (candleSeries.value) {
      candleSeries.value.applyOptions({
        upColor,
        downColor,
        borderUpColor: upColor,
        borderDownColor: downColor,
        wickUpColor: upColor,
        wickDownColor: downColor
      })
    }

    if (volumeSeries.value) {
      volumeSeries.value.applyOptions({
        color: getVolumeUpColor()
      })
    }

    updateChartData()
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
      const upColor = getUpColor()
      const downColor = getDownColor()
      candleSeries.value = chart.value.addCandlestickSeries({
        upColor,
        downColor,
        borderDownColor: downColor,
        borderUpColor: upColor,
        wickDownColor: downColor,
        wickUpColor: upColor,
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
      color: getVolumeUpColor(),
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
      if (isSyncingTimeScale.value) return
      
      onVisibleRangeChange(range)
      
      // Sync all sub-charts time scale with main chart
      if (range) {
        isSyncingTimeScale.value = true
        Object.values(subCharts.value).forEach(subChart => {
          if (subChart) {
            subChart.timeScale().setVisibleLogicalRange(range)
          }
        })
        isSyncingTimeScale.value = false
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
    // 清除之前的错误状态
    if (options.onError) {
      options.onError({ show: false, message: '' })
    }
    if (options.onLoading) options.onLoading(true)

    try {
      const currentBar = options.bar.value
      const backendBar = getBackendBar(currentBar)
      const isTimeline = checkIsTimelineMode(currentBar)
      const modeParam = getModeParam()
      const requestSymbol = options.symbol.value
      const requestSource = options.source.value
      
      // For timeline mode, limit to today's data only (or recent period)
      let limit = 2000
      if (isTimeline) {
        // 1s 分时模式下使用较大的缓存以支持多次刷新
        limit = 5000
      }
      
      const response = await fetch(
        `/api/candlesticks/?symbol=${requestSymbol}&bar=${backendBar}&limit=${limit}&source=${requestSource}&mode=${modeParam}`
      )
      const result: APIResponse<Candle[]> = await response.json()

      if (
        options.symbol.value !== requestSymbol ||
        options.bar.value !== currentBar ||
        options.source.value !== requestSource ||
        getModeParam() !== modeParam
      ) {
        return
      }

      if (result.code === 0 && result.data) {
        // 应用汇率转换
        const rate = options.exchangeRate?.value || 1
        const convertedData = result.data.map(candle => ({
          ...candle,
          open: candle.open * rate,
          high: candle.high * rate,
          low: candle.low * rate,
          close: candle.close * rate
          // volume 不需要转换
        }))
        
        allCandles.value = convertedData
        
        // Track timestamps for pagination (store as seconds)
        if (convertedData.length > 0) {
          oldestTimestamp.value = convertedData[0].time as number
          newestTimestamp.value = convertedData[convertedData.length - 1].time as number
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
    
    const volumeUpColor = getVolumeUpColor()
    const volumeDownColor = getVolumeDownColor()
    const candles = allCandles.value
    const len = candles.length

    // 优化：一次遍历生成所有数据，减少数组迭代开销
    if (isTimelineMode.value && lineSeries.value) {
      const lineData = new Array(len)
      const volumeData = new Array(len)
      
      for (let i = 0; i < len; i++) {
        const c = candles[i]
        const time = c.time as any
        lineData[i] = { time, value: c.close }
        volumeData[i] = {
          time,
          value: c.volume,
          color: c.close >= c.open ? volumeUpColor : volumeDownColor
        }
      }
      
      lineSeries.value.setData(lineData)
      volumeSeries.value.setData(volumeData)
    } else if (candleSeries.value) {
      const candleData = new Array(len)
      const volumeData = new Array(len)
      
      for (let i = 0; i < len; i++) {
        const c = candles[i]
        const time = c.time as any
        candleData[i] = {
          time,
          open: c.open,
          high: c.high,
          low: c.low,
          close: c.close
        }
        volumeData[i] = {
          time,
          value: c.volume,
          color: c.close >= c.open ? volumeUpColor : volumeDownColor
        }
      }
      
      candleSeries.value.setData(candleData)
      volumeSeries.value.setData(volumeData)
    }

    // Update price info
    if (len > 0 && options.onPriceUpdate) {
      const latest = candles[len - 1]
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

    const volumeUpColor = getVolumeUpColor()
    const volumeDownColor = getVolumeDownColor()

    try {
      const requestSymbol = options.symbol.value
      const requestBar = options.bar.value
      const requestSource = options.source.value
      const requestMode = getModeParam()
      const requestNewestTs = newestTimestamp.value

      // Use 'after' parameter to get only newer data than we have
      const afterMs = requestNewestTs * 1000
      const backendBar = getBackendBar(requestBar)
      const response = await fetch(
        `/api/candlesticks/?symbol=${requestSymbol}&bar=${backendBar}&limit=100&source=${requestSource}&after=${afterMs}&mode=${requestMode}`
      )
      const result: APIResponse<Candle[]> = await response.json()

      // 如果期间切换了交易对/周期/数据源，放弃这次更新
      if (
        options.symbol.value !== requestSymbol ||
        options.bar.value !== requestBar ||
        options.source.value !== requestSource ||
        getModeParam() !== requestMode
      ) {
        return
      }

      if (result.code === 0 && result.data && result.data.length > 0) {
        // 状态可能在请求期间被重置，重新验证
        if (allCandles.value.length === 0) {
          return
        }
        const lastCandle = allCandles.value[allCandles.value.length - 1]
        if (!lastCandle || lastCandle.time === undefined || lastCandle.time === null) {
          return
        }

        // 应用汇率转换
        const rate = options.exchangeRate?.value || 1
        const newCandles = result.data.map(candle => ({
          ...candle,
          open: candle.open * rate,
          high: candle.high * rate,
          low: candle.low * rate,
          close: candle.close * rate
        }))

        // 避免 newestTimestamp 在调用期间被重置导致写回旧数据
        if (!newestTimestamp.value || newestTimestamp.value < lastCandle.time) {
          newestTimestamp.value = lastCandle.time as number
        }

  let hasNewData = false
  let needsFullRefresh = false

        for (const newCandle of newCandles) {
          if (!newCandle || newCandle.time === undefined || newCandle.time === null) {
            continue
          }
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
                color: newCandle.close >= newCandle.open ? volumeUpColor : volumeDownColor
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
                color: newCandle.close >= newCandle.open ? volumeUpColor : volumeDownColor
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
                color: newCandle.close >= newCandle.open ? volumeUpColor : volumeDownColor
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
                color: newCandle.close >= newCandle.open ? volumeUpColor : volumeDownColor
              })
            }
            newestTimestamp.value = newCandle.time as number
            hasNewData = true
          } else if (newCandle.time < lastCandle.time && isTimelineMode.value) {
            // 如果上一次返回的是未来时间，新数据比最新蜡烛还早，则说明历史被覆盖，重建时间线
            allCandles.value = [...allCandles.value.filter(item => (item.time as number) < newCandle.time), newCandle]
            allCandles.value.sort((a, b) => (a.time as number) - (b.time as number))
            newestTimestamp.value = allCandles.value[allCandles.value.length - 1]?.time as number
            hasNewData = true
            needsFullRefresh = true
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

        if (needsFullRefresh) {
          updateChartData()
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
    
    // 动态缓冲区：可视范围的 3 倍，最小 1000，最大 5000
    // 增大缓冲区，提前触发加载
    const bufferZone = Math.max(1000, Math.min(5000, Math.floor(visibleRange * 3.0)))
    
    // Clear existing debounce timer
    if (loadDebounceTimer) {
      clearTimeout(loadDebounceTimer)
      loadDebounceTimer = null
    }
    
    // Determine if we should load
    const shouldLoadHistory = hasMoreData.value && !isLoadingMore.value && visibleFromIndex < bufferZone
    const shouldLoadNewer = hasNewerData.value && !isLoadingNewer.value && visibleToIndex > allCandles.value.length - bufferZone
    
    // Debug logging
    if (shouldLoadHistory || shouldLoadNewer) {
      // Debounce: 200ms - 给用户更多拖动时间，减少请求频率
      loadDebounceTimer = window.setTimeout(() => {
        // Double-check conditions haven't changed during debounce
        if (shouldLoadHistory && !isLoadingMore.value && hasMoreData.value) {
          // 计算需要加载的数量
          // 基础加载量：可视范围的 10 倍
          // 最小 5000 (保证足够数据)，最大 10000 (一次加载更多)
          let loadCount = Math.max(5000, visibleRange * 10)
          loadCount = Math.min(10000, Math.ceil(loadCount))
          
          loadMoreHistory(loadCount)
        } else if (shouldLoadNewer && !isLoadingNewer.value && hasNewerData.value) {
          loadMoreNewerUntilEnough()
        }
        loadDebounceTimer = null
      }, 200)
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
    
    try {
      // oldestTimestamp is in seconds, API expects milliseconds
      if (oldestTimestamp.value === null || allCandles.value.length === 0) {
        hasMoreData.value = false
        isLoadingMore.value = false
        return
      }
      const beforeMs = oldestTimestamp.value * 1000
      // 限制单次请求最大 10000 条，满足用户对更大预加载数据的需求
      const limit = Math.min(count, 10000)
      const requestSymbol = options.symbol.value
      const requestSource = options.source.value
      const requestBar = options.bar.value
      const modeParam = getModeParam()
      const backendBar = getBackendBar(requestBar)
      const url = `/api/candlesticks/?symbol=${requestSymbol}&bar=${backendBar}&limit=${limit}&source=${requestSource}&mode=${modeParam}&before=${beforeMs}`
      
      const response = await fetch(url)
      const result: APIResponse<Candle[]> = await response.json()
      
      if (
        options.symbol.value !== requestSymbol ||
        options.source.value !== requestSource ||
        options.bar.value !== requestBar ||
        getModeParam() !== modeParam
      ) {
        return
      }

      if (result.code === 0 && result.data && result.data.length > 0) {
        // 应用汇率转换
        const rate = options.exchangeRate?.value || 1
        const newCandles = result.data.map(candle => ({
          ...candle,
          open: candle.open * rate,
          high: candle.high * rate,
          low: candle.low * rate,
          close: candle.close * rate
        }))
        
        // 过滤重复数据，只保留比当前最早时间更早的数据
        const firstCurrentTime = allCandles.value.length ? allCandles.value[0].time : undefined
        const uniqueNewCandles = firstCurrentTime === undefined
          ? newCandles
          : newCandles.filter(c => c.time < firstCurrentTime)
        
        if (uniqueNewCandles.length > 0) {
          // 优化：使用 concat 而不是展开运算符，对于大数组性能更好
          allCandles.value = uniqueNewCandles.concat(allCandles.value)
          // 确保排序正确（虽然理论上应该是排好的）
          // allCandles.value.sort((a, b) => (a.time as number) - (b.time as number))
          
          const newOldestTime = allCandles.value[0].time
          
          oldestTimestamp.value = newOldestTime as number
          
          // Update chart data - setData will preserve user's current view position
          updateChartData()
          // As long as we receive any unique candles we still assume there may be more history
          hasMoreData.value = true
        } else {
          hasMoreData.value = false
        }
      } else {
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
      if (newestTimestamp.value === null) {
        isLoadingNewer.value = false
        return
      }
      const afterMs = newestTimestamp.value * 1000
      const requestSymbol = options.symbol.value
      const requestSource = options.source.value
      const requestBar = options.bar.value
      const modeParam = getModeParam()
      const backendBar = getBackendBar(requestBar)
      const response = await fetch(
        `/api/candlesticks/?symbol=${requestSymbol}&bar=${backendBar}&limit=2000&source=${requestSource}&mode=${modeParam}&after=${afterMs}`
      )
      const result: APIResponse<Candle[]> = await response.json()
      if (
        options.symbol.value !== requestSymbol ||
        options.source.value !== requestSource ||
        options.bar.value !== requestBar ||
        getModeParam() !== modeParam
      ) {
        return
      }
      
      if (result.code === 0 && result.data && result.data.length > 0) {
        const newCandles = result.data
        const existingTimes = new Set(allCandles.value.map(c => c.time))
        const uniqueCandles = newCandles.filter(c => !existingTimes.has(c.time))
        
        if (uniqueCandles.length > 0) {
          allCandles.value = [...allCandles.value, ...uniqueCandles]
          allCandles.value.sort((a, b) => (a.time as number) - (b.time as number))
          newestTimestamp.value = allCandles.value[allCandles.value.length - 1].time as number
          
          updateChartData()
        }
        
        // If we got less than requested, we've likely reached the present
        hasNewerData.value = result.data.length >= 1500
      } else {
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
  }

  if (options.colors) {
    watch(
      [options.colors.up, options.colors.down, options.colors.volumeUp, options.colors.volumeDown],
      () => {
        applySeriesColors()
      }
    )
  }

  // Watch for symbol/bar/source/mode changes
  watch([
    () => options.symbol.value,
    () => options.bar.value,
    () => options.source.value,
    () => getModeParam()
  ], () => {
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
