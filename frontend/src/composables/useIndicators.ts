import { reactive, computed, nextTick, type Ref, type ComputedRef } from 'vue'
import { createChart, type IChartApi, ColorType } from 'lightweight-charts'
import type { IndicatorConfig, Indicators, Candle } from '@/types'
import { useIndicatorWorker } from './useIndicatorWorker'

export function useIndicators(
  chart: Ref<IChartApi | null>, 
  subCharts: Ref<Record<string, IChartApi>>,
  allCandles: Ref<Candle[]>
) {
  const { calculateIndicators, terminateWorker } = useIndicatorWorker()
  
  const indicators = reactive<Partial<Indicators>>({
    vol: { enabled: true, name: 'VOL', series: null }, // 默认指标，始终显示
    ma: { enabled: false, name: 'MA', series: [] },
    ema: { enabled: false, name: 'EMA', series: [] },
    boll: { enabled: false, name: 'BOLL', series: [] },
    sar: { enabled: false, name: 'SAR', series: [] },
    supertrend: { enabled: false, name: 'SuperTrend', series: [] },
    sr: { enabled: false, name: 'S/R', series: [] },
    macd: { enabled: false, name: 'MACD', series: [] },
    kdj: { enabled: false, name: 'KDJ', series: [] },
    rsi: { enabled: false, name: 'RSI', series: [] },
    stochrsi: { enabled: false, name: 'StochRSI', series: [] },
    cci: { enabled: false, name: 'CCI', series: [] },
    dmi: { enabled: false, name: 'DMI', series: [] },
    wr: { enabled: false, name: 'WR', series: [] },
    obv: { enabled: false, name: 'OBV', series: [] },
    trix: { enabled: false, name: 'TRIX', series: [] },
    roc: { enabled: false, name: 'ROC', series: [] },
    mtm: { enabled: false, name: 'MTM', series: [] },
    dma: { enabled: false, name: 'DMA', series: [] },
    vr: { enabled: false, name: 'VR', series: [] },
    brar: { enabled: false, name: 'BRAR', series: [] },
    psy: { enabled: false, name: 'PSY', series: [] }
  }) as Indicators

  const subChartRefs: Record<string, HTMLElement> = {}
  const subChartHeights = reactive<Record<string, number>>({
    macd: 180,
    rsi: 180,
    kdj: 180,
    stochrsi: 180,
    cci: 180,
    dmi: 180,
    wr: 180,
    obv: 180,
    trix: 180,
    roc: 180,
    mtm: 180,
    dma: 180,
    vr: 180,
    brar: 180,
    psy: 180
  })

  const setSubChartRef = (el: HTMLElement | null, key: string): void => {
    if (el) {
      subChartRefs[key] = el
    }
  }

  const initSubChart = (key: string): void => {
    if (!subChartRefs[key]) {
      console.warn(`Sub chart ref for ${key} not found`)
      return
    }

    // Remove existing sub-chart
    if (subCharts.value[key]) {
      subCharts.value[key].remove()
      delete subCharts.value[key]
    }

    const parentWidth = subChartRefs[key].clientWidth || 800
    const parentHeight = subChartRefs[key].clientHeight || 180

    // Create new sub-chart
    const subChart = createChart(subChartRefs[key], {
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
        mode: 0,
        vertLine: { width: 1, style: 2, visible: true, labelVisible: false },
        horzLine: { width: 1, style: 2, visible: true, labelVisible: true }
      },
      rightPriceScale: { 
        borderColor: '#2a2e39',
        borderVisible: true
      },
      timeScale: { borderColor: '#2a2e39', timeVisible: true, secondsVisible: false },
      width: parentWidth,
      height: parentHeight
    })

    subCharts.value[key] = subChart

    // Sync time scale with main chart (sub-chart → main chart)
    // Note: Main chart also syncs to sub-charts, so we don't need bidirectional sync here
    // The main chart's sync will handle updating all sub-charts
    // This subscription is kept for direct user interaction on sub-charts only

    // Create series based on indicator type
    createSubIndicatorSeries(key, subChart)
  }

  const createSubIndicatorSeries = (key: string, subChart: IChartApi): void => {
    if (key === 'macd' && indicators[key as keyof Indicators]) {
      indicators[key]!.series = [
        subChart.addHistogramSeries({
          color: '#26a69a',
          priceFormat: { type: 'volume' },
          title: 'MACD',
          lastValueVisible: false
        }),
        subChart.addLineSeries({ 
          color: '#2962FF', 
          lineWidth: 1, 
          title: 'DIF',
          lastValueVisible: false,
          priceLineVisible: false
        }),
        subChart.addLineSeries({ 
          color: '#FF6D00', 
          lineWidth: 1, 
          title: 'DEA',
          lastValueVisible: false,
          priceLineVisible: false
        })
      ]
    } else if (key === 'rsi' && indicators[key as keyof Indicators]) {
      indicators[key]!.series = [
        subChart.addLineSeries({ 
          color: '#9C27B0', 
          lineWidth: 1, 
          title: 'RSI',
          lastValueVisible: false,
          priceLineVisible: false
        })
      ]
    } else if (key === 'kdj' && indicators[key as keyof Indicators]) {
      indicators[key]!.series = [
        subChart.addLineSeries({ 
          color: '#2962FF', 
          lineWidth: 1, 
          title: 'K',
          lastValueVisible: false,
          priceLineVisible: false
        }),
        subChart.addLineSeries({ 
          color: '#FF6D00', 
          lineWidth: 1, 
          title: 'D',
          lastValueVisible: false,
          priceLineVisible: false
        }),
        subChart.addLineSeries({ 
          color: '#E91E63', 
          lineWidth: 1, 
          title: 'J',
          lastValueVisible: false,
          priceLineVisible: false
        })
      ]
    } else if (key === 'stochrsi' && indicators[key as keyof Indicators]) {
      indicators[key]!.series = [
        subChart.addLineSeries({ color: '#2962FF', lineWidth: 1, title: 'StochRSI K', lastValueVisible: false, priceLineVisible: false }),
        subChart.addLineSeries({ color: '#FF6D00', lineWidth: 1, title: 'StochRSI D', lastValueVisible: false, priceLineVisible: false })
      ]
    } else if (key === 'cci' && indicators[key as keyof Indicators]) {
      indicators[key]!.series = [
        subChart.addLineSeries({ color: '#9C27B0', lineWidth: 1, title: 'CCI', lastValueVisible: false, priceLineVisible: false })
      ]
    } else if (key === 'dmi' && indicators[key as keyof Indicators]) {
      indicators[key]!.series = [
        subChart.addLineSeries({ color: '#2962FF', lineWidth: 1, title: 'PDI', lastValueVisible: false, priceLineVisible: false }),
        subChart.addLineSeries({ color: '#FF6D00', lineWidth: 1, title: 'MDI', lastValueVisible: false, priceLineVisible: false }),
        subChart.addLineSeries({ color: '#26a69a', lineWidth: 1, title: 'ADX', lastValueVisible: false, priceLineVisible: false })
      ]
    } else if (key === 'wr' && indicators[key as keyof Indicators]) {
      indicators[key]!.series = [
        subChart.addLineSeries({ color: '#E91E63', lineWidth: 1, title: 'WR', lastValueVisible: false, priceLineVisible: false })
      ]
    } else if (key === 'obv' && indicators[key as keyof Indicators]) {
      indicators[key]!.series = [
        subChart.addLineSeries({ color: '#00BCD4', lineWidth: 1, title: 'OBV', lastValueVisible: false, priceLineVisible: false })
      ]
    } else if (key === 'trix' && indicators[key as keyof Indicators]) {
      indicators[key]!.series = [
        subChart.addLineSeries({ color: '#FFC107', lineWidth: 1, title: 'TRIX', lastValueVisible: false, priceLineVisible: false })
      ]
    } else if (key === 'roc' && indicators[key as keyof Indicators]) {
      indicators[key]!.series = [
        subChart.addLineSeries({ color: '#9C27B0', lineWidth: 1, title: 'ROC', lastValueVisible: false, priceLineVisible: false })
      ]
    } else if (key === 'mtm' && indicators[key as keyof Indicators]) {
      indicators[key]!.series = [
        subChart.addLineSeries({ color: '#2196F3', lineWidth: 1, title: 'MTM', lastValueVisible: false, priceLineVisible: false })
      ]
    } else if (key === 'dma' && indicators[key as keyof Indicators]) {
      indicators[key]!.series = [
        subChart.addLineSeries({ color: '#2962FF', lineWidth: 1, title: 'DMA1', lastValueVisible: false, priceLineVisible: false }),
        subChart.addLineSeries({ color: '#FF6D00', lineWidth: 1, title: 'DMA2', lastValueVisible: false, priceLineVisible: false })
      ]
    } else if (key === 'vr' && indicators[key as keyof Indicators]) {
      indicators[key]!.series = [
        subChart.addLineSeries({ color: '#26a69a', lineWidth: 1, title: 'VR', lastValueVisible: false, priceLineVisible: false })
      ]
    } else if (key === 'brar' && indicators[key as keyof Indicators]) {
      indicators[key]!.series = [
        subChart.addLineSeries({ color: '#2962FF', lineWidth: 1, title: 'BR', lastValueVisible: false, priceLineVisible: false }),
        subChart.addLineSeries({ color: '#FF6D00', lineWidth: 1, title: 'AR', lastValueVisible: false, priceLineVisible: false })
      ]
    } else if (key === 'psy' && indicators[key as keyof Indicators]) {
      indicators[key]!.series = [
        subChart.addLineSeries({ color: '#E91E63', lineWidth: 1, title: 'PSY', lastValueVisible: false, priceLineVisible: false })
      ]
    }
  }

  const createMainIndicatorSeries = (key: string): void => {
    if (!chart.value) return

    if (key === 'ma') {
      indicators.ma.series = [
        chart.value.addLineSeries({ color: '#2196F3', lineWidth: 1, title: 'MA7', lastValueVisible: false, priceLineVisible: false }),
        chart.value.addLineSeries({ color: '#FF9800', lineWidth: 1, title: 'MA25', lastValueVisible: false, priceLineVisible: false }),
        chart.value.addLineSeries({ color: '#9C27B0', lineWidth: 1, title: 'MA99', lastValueVisible: false, priceLineVisible: false })
      ]
    } else if (key === 'ema') {
      indicators.ema.series = [
        chart.value.addLineSeries({ color: '#00BCD4', lineWidth: 1, title: 'EMA7', lastValueVisible: false, priceLineVisible: false }),
        chart.value.addLineSeries({ color: '#FFC107', lineWidth: 1, title: 'EMA25', lastValueVisible: false, priceLineVisible: false }),
        chart.value.addLineSeries({ color: '#E91E63', lineWidth: 1, title: 'EMA99', lastValueVisible: false, priceLineVisible: false })
      ]
    } else if (key === 'boll') {
      indicators.boll.series = [
        chart.value.addLineSeries({ color: '#2196F3', lineWidth: 1, title: 'BOLL Upper', lastValueVisible: false, priceLineVisible: false }),
        chart.value.addLineSeries({ color: '#FFC107', lineWidth: 1, title: 'BOLL Middle', lastValueVisible: false, priceLineVisible: false }),
        chart.value.addLineSeries({ color: '#2196F3', lineWidth: 1, title: 'BOLL Lower', lastValueVisible: false, priceLineVisible: false })
      ]
    } else if (key === 'sar') {
      indicators.sar.series = chart.value.addLineSeries({ 
        color: '#FF6D00', 
        lineWidth: 2, 
        lineStyle: 2,
        title: 'SAR',
        lastValueVisible: false,
        priceLineVisible: false
      })
    } else if (key === 'supertrend') {
      indicators.supertrend.series = chart.value.addLineSeries({ 
        color: '#26a69a', 
        lineWidth: 2, 
        title: 'SuperTrend',
        lastValueVisible: false,
        priceLineVisible: false
      })
    } else if (key === 'sr') {
      indicators.sr.series = [
        chart.value.addLineSeries({ color: '#ef5350', lineWidth: 1, lineStyle: 2, title: 'Resistance', lastValueVisible: false, priceLineVisible: false }),
        chart.value.addLineSeries({ color: '#26a69a', lineWidth: 1, lineStyle: 2, title: 'Support', lastValueVisible: false, priceLineVisible: false })
      ]
    }
  }

  const removeIndicatorSeries = (key: string): void => {
    if (!chart.value || !indicators[key as keyof Indicators]) return
    
    const series = indicators[key as keyof Indicators].series
    if (Array.isArray(series)) {
      series.forEach(s => chart.value?.removeSeries(s))
    } else if (series) {
      chart.value.removeSeries(series)
    }
    indicators[key as keyof Indicators].series = Array.isArray(series) ? [] : null
  }

  const triggerWorkerCalculation = async (): Promise<void> => {
    if (allCandles.value.length === 0) return

    try {
      const results = await calculateIndicators(allCandles.value, indicators)
      updateIndicatorData(results)
    } catch (error) {
      console.error('Failed to calculate indicators:', error)
    }
  }

  const updateIndicatorData = (results: any): void => {
    if (!chart.value) return

    // Update MA
    if (results.ma && Array.isArray(indicators.ma.series)) {
      results.ma.forEach((data: any, i: number) => {
        if (indicators.ma.series[i]) {
          indicators.ma.series[i].setData(data.map((d: any) => ({ time: d.time as any, value: d.value })))
        }
      })
    }

    // Update EMA
    if (results.ema && Array.isArray(indicators.ema.series)) {
      results.ema.forEach((data: any, i: number) => {
        if (indicators.ema.series[i]) {
          indicators.ema.series[i].setData(data.map((d: any) => ({ time: d.time as any, value: d.value })))
        }
      })
    }

    // Update BOLL
    if (results.boll && Array.isArray(indicators.boll.series)) {
      if (indicators.boll.series[0]) {
        indicators.boll.series[0].setData(results.boll.upper.map((d: any) => ({ time: d.time as any, value: d.value })))
      }
      if (indicators.boll.series[1]) {
        indicators.boll.series[1].setData(results.boll.middle.map((d: any) => ({ time: d.time as any, value: d.value })))
      }
      if (indicators.boll.series[2]) {
        indicators.boll.series[2].setData(results.boll.lower.map((d: any) => ({ time: d.time as any, value: d.value })))
      }
    }

    // Update SAR
    if (results.sar && indicators.sar.series && !Array.isArray(indicators.sar.series)) {
      indicators.sar.series.setData(results.sar.map((d: any) => ({ time: d.time as any, value: d.value })))
    }

    // Update SuperTrend
    if (results.supertrend && indicators.supertrend.series && !Array.isArray(indicators.supertrend.series)) {
      indicators.supertrend.series.setData(results.supertrend.map((d: any) => ({ 
        time: d.time as any, 
        value: d.value
      })))
    }

    // Update S/R
    if (results.sr && Array.isArray(indicators.sr.series)) {
      if (indicators.sr.series[0] && results.sr.resistance) {
        indicators.sr.series[0].setData(results.sr.resistance.map((d: any) => ({ time: d.time as any, value: d.value })))
      }
      if (indicators.sr.series[1] && results.sr.support) {
        indicators.sr.series[1].setData(results.sr.support.map((d: any) => ({ time: d.time as any, value: d.value })))
      }
    }

    // Update MACD
    if (results.macd && Array.isArray(indicators.macd.series)) {
      if (indicators.macd.series[0]) {
        indicators.macd.series[0].setData(results.macd.histogram.map((d: any) => ({ 
          time: d.time as any, 
          value: d.value,
          color: d.color
        })))
      }
      if (indicators.macd.series[1]) {
        indicators.macd.series[1].setData(results.macd.dif.map((d: any) => ({ time: d.time as any, value: d.value })))
      }
      if (indicators.macd.series[2]) {
        indicators.macd.series[2].setData(results.macd.dea.map((d: any) => ({ time: d.time as any, value: d.value })))
      }
    }

    // Update KDJ
    if (results.kdj && Array.isArray(indicators.kdj.series)) {
      if (indicators.kdj.series[0]) {
        indicators.kdj.series[0].setData(results.kdj.k.map((d: any) => ({ time: d.time as any, value: d.value })))
      }
      if (indicators.kdj.series[1]) {
        indicators.kdj.series[1].setData(results.kdj.d.map((d: any) => ({ time: d.time as any, value: d.value })))
      }
      if (indicators.kdj.series[2]) {
        indicators.kdj.series[2].setData(results.kdj.j.map((d: any) => ({ time: d.time as any, value: d.value })))
      }
    }

    // Update RSI
    if (results.rsi && Array.isArray(indicators.rsi.series) && indicators.rsi.series[0]) {
      indicators.rsi.series[0].setData(results.rsi.map((d: any) => ({ time: d.time as any, value: d.value })))
    }

    // Update StochRSI
    if (results.stochrsi && Array.isArray(indicators.stochrsi.series)) {
      if (indicators.stochrsi.series[0] && results.stochrsi.k) {
        indicators.stochrsi.series[0].setData(results.stochrsi.k.map((d: any) => ({ time: d.time as any, value: d.value })))
      }
      if (indicators.stochrsi.series[1] && results.stochrsi.d) {
        indicators.stochrsi.series[1].setData(results.stochrsi.d.map((d: any) => ({ time: d.time as any, value: d.value })))
      }
    }

    // Update CCI
    if (results.cci && Array.isArray(indicators.cci.series) && indicators.cci.series[0]) {
      indicators.cci.series[0].setData(results.cci.map((d: any) => ({ time: d.time as any, value: d.value })))
    }

    // Update DMI
    if (results.dmi && Array.isArray(indicators.dmi.series)) {
      if (indicators.dmi.series[0] && results.dmi.pdi) {
        indicators.dmi.series[0].setData(results.dmi.pdi.map((d: any) => ({ time: d.time as any, value: d.value })))
      }
      if (indicators.dmi.series[1] && results.dmi.mdi) {
        indicators.dmi.series[1].setData(results.dmi.mdi.map((d: any) => ({ time: d.time as any, value: d.value })))
      }
      if (indicators.dmi.series[2] && results.dmi.adx) {
        indicators.dmi.series[2].setData(results.dmi.adx.map((d: any) => ({ time: d.time as any, value: d.value })))
      }
    }

    // Update WR
    if (results.wr && Array.isArray(indicators.wr.series) && indicators.wr.series[0]) {
      indicators.wr.series[0].setData(results.wr.map((d: any) => ({ time: d.time as any, value: d.value })))
    }

    // Update OBV
    if (results.obv && Array.isArray(indicators.obv.series) && indicators.obv.series[0]) {
      indicators.obv.series[0].setData(results.obv.map((d: any) => ({ time: d.time as any, value: d.value })))
    }

    // Update TRIX
    if (results.trix && Array.isArray(indicators.trix.series) && indicators.trix.series[0]) {
      indicators.trix.series[0].setData(results.trix.map((d: any) => ({ time: d.time as any, value: d.value })))
    }

    // Update ROC
    if (results.roc && Array.isArray(indicators.roc.series) && indicators.roc.series[0]) {
      indicators.roc.series[0].setData(results.roc.map((d: any) => ({ time: d.time as any, value: d.value })))
    }

    // Update MTM
    if (results.mtm && Array.isArray(indicators.mtm.series) && indicators.mtm.series[0]) {
      indicators.mtm.series[0].setData(results.mtm.map((d: any) => ({ time: d.time as any, value: d.value })))
    }

    // Update DMA
    if (results.dma && Array.isArray(indicators.dma.series)) {
      if (indicators.dma.series[0] && results.dma.dma1) {
        indicators.dma.series[0].setData(results.dma.dma1.map((d: any) => ({ time: d.time as any, value: d.value })))
      }
      if (indicators.dma.series[1] && results.dma.dma2) {
        indicators.dma.series[1].setData(results.dma.dma2.map((d: any) => ({ time: d.time as any, value: d.value })))
      }
    }

    // Update VR
    if (results.vr && Array.isArray(indicators.vr.series) && indicators.vr.series[0]) {
      indicators.vr.series[0].setData(results.vr.map((d: any) => ({ time: d.time as any, value: d.value })))
    }

    // Update BRAR
    if (results.brar && Array.isArray(indicators.brar.series)) {
      if (indicators.brar.series[0] && results.brar.br) {
        indicators.brar.series[0].setData(results.brar.br.map((d: any) => ({ time: d.time as any, value: d.value })))
      }
      if (indicators.brar.series[1] && results.brar.ar) {
        indicators.brar.series[1].setData(results.brar.ar.map((d: any) => ({ time: d.time as any, value: d.value })))
      }
    }

    // Update PSY
    if (results.psy && Array.isArray(indicators.psy.series) && indicators.psy.series[0]) {
      indicators.psy.series[0].setData(results.psy.map((d: any) => ({ time: d.time as any, value: d.value })))
    }
  }

  const enabledSubIndicators: ComputedRef<Record<string, IndicatorConfig>> = computed(() => {
    const enabled: Record<string, IndicatorConfig> = {}
    // 副图指标列表：不是覆盖在主图上的指标
    const subIndicatorKeys = ['macd', 'rsi', 'kdj', 'stochrsi', 'cci', 'dmi', 'wr', 'obv', 'trix', 'roc', 'mtm', 'dma', 'vr', 'brar', 'psy']
    Object.keys(indicators).forEach(key => {
      const k = key as keyof Indicators
      if (subIndicatorKeys.includes(key) && indicators[k].enabled) {
        enabled[key] = indicators[k]
      }
    })
    return enabled
  })

  const hasSubIndicators: ComputedRef<boolean> = computed(() => {
    return Object.keys(enabledSubIndicators.value).length > 0
  })

  const cleanup = (): void => {
    terminateWorker()
    Object.keys(subCharts.value).forEach(key => {
      subCharts.value[key].remove()
    })
  }

  const toggleIndicator = (key: keyof Indicators): void => {
    if (!indicators[key]) return
    
    // VOL 是默认指标，不允许禁用
    if (key === 'vol') return
    
    indicators[key]!.enabled = !indicators[key]!.enabled

    // Handle main indicators (overlays on main chart)
    if (['vol', 'ma', 'ema', 'boll', 'sar', 'supertrend', 'sr'].includes(key)) {
      if (key === 'vol' && indicators.vol && indicators.vol.series) {
        indicators.vol.series.applyOptions({ visible: indicators.vol.enabled })
      } else if (indicators[key]!.enabled) {
        // Create series for main indicators
        createMainIndicatorSeries(key)
        triggerWorkerCalculation()
      } else {
        // Remove series
        removeIndicatorSeries(key)
      }
      return
    }

    // Handle sub-indicators
    if (indicators[key]!.enabled) {
      nextTick(() => {
        setTimeout(() => {
          if (subChartRefs[key]) {
            initSubChart(key)
            triggerWorkerCalculation()
          }
        }, 100)
      })
    } else {
      if (subCharts.value[key]) {
        subCharts.value[key].remove()
        delete subCharts.value[key]
      }
      indicators[key]!.series = []
    }
  }

  const rebuildSubCharts = (): void => {
    // 重建所有已启用的副图（切换币种/周期时使用）
    const subIndicatorKeys = ['macd', 'rsi', 'kdj', 'stochrsi', 'cci', 'dmi', 'wr', 'obv', 'trix', 'roc', 'mtm', 'dma', 'vr', 'brar', 'psy'] as const
    
    subIndicatorKeys.forEach(key => {
      if (indicators[key]?.enabled && subChartRefs[key]) {
        // 移除旧的副图
        if (subCharts.value[key]) {
          subCharts.value[key].remove()
          delete subCharts.value[key]
        }
        // 重新初始化
        nextTick(() => {
          setTimeout(() => {
            initSubChart(key)
          }, 100)
        })
      }
    })
  }

  return {
    indicators,
    subChartHeights,
    toggleIndicator,
    enabledSubIndicators,
    hasSubIndicators,
    setSubChartRef,
    triggerWorkerCalculation,
    rebuildSubCharts,
    cleanup
  }
}
