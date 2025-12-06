import { reactive, computed, nextTick, type Ref, type ComputedRef } from 'vue'
import { createChart, type IChartApi, ColorType } from 'lightweight-charts'
import type { IndicatorConfig, Indicators, Candle } from '@/types'
import { useIndicatorWorker } from './useIndicatorWorker'
import { useTimeScaleSync } from './useTimeScaleSync'

export function useIndicators(
  chart: Ref<IChartApi | null>, 
  subCharts: Ref<Record<string, IChartApi>>,
  allCandles: Ref<Candle[]>
) {
  const { calculateIndicators, terminateWorker } = useIndicatorWorker()
  const { isSyncingTimeScale } = useTimeScaleSync()
  
  const indicators = reactive<Partial<Indicators>>({
    vol: { 
      enabled: true, 
      name: 'VOL', 
      zhName: '成交量',
      description: '显示某时段内的成交量，通常用柱状图表示。成交量大小反映市场活跃度，价涨量增为强势，价涨量减为弱势。',
      series: null 
    },
    ma: { 
      enabled: false, 
      name: 'MA(5,10,20)', 
      zhName: '移动平均线(标准)',
      description: '简单移动平均线(Simple Moving Average)，采用标准周期配置。MA5(短期)、MA10(中期)、MA20(长期)，是最常用的均线组合，适用于大多数市场环境。',
      series: [] 
    },
    maWithMacd: { 
      enabled: false, 
      name: 'MA(9,12,26)', 
      zhName: '移动平均线(MACD标准)',
      description: '配合MACD指标使用的移动平均线。MA9(信号线周期)、MA12(快线周期)、MA26(慢线周期)，与MACD指标完美配合，便于识别均线与MACD的共振信号。',
      series: [] 
    },
    ema: { 
      enabled: false, 
      name: 'EMA(5,10,20)', 
      zhName: '指数移动平均线(短期)',
      description: '指数平滑移动平均线(Exponential Moving Average)，对近期价格赋予更高权重。短期配置：EMA5、EMA10、EMA20，反应灵敏，适合捕捉快速趋势变化。',
      series: [] 
    },
    emaFib: { 
      enabled: false, 
      name: 'EMA(9,21,55)', 
      zhName: '指数移动平均线(斐波那契)',
      description: '基于斐波那契数列的EMA配置。EMA9、EMA21、EMA55符合黄金分割比例，是加密货币和量化交易中最流行的配置，TradingView默认推荐。',
      series: [] 
    },
    boll: { 
      enabled: false, 
      name: 'BOLL', 
      zhName: '布林带',
      description: '布林带(Bollinger Bands)由中轨(MA)、上轨(MA+2倍标准差)、下轨(MA-2倍标准差)组成。价格在上下轨间波动，触及上轨可能回调，触及下轨可能反弹。带宽收窄预示突破。',
      series: [] 
    },
    sar: { 
      enabled: false, 
      name: 'SAR', 
      zhName: '抛物线转向',
      description: '抛物线转向指标(Stop And Reverse)，以点状显示止损位。点在价格下方为多头，上方为空头。点位翻转提示趋势转换，适合跟踪趋势交易。',
      series: [] 
    },
    supertrend: { 
      enabled: false, 
      name: 'SuperTrend', 
      zhName: '超级趋势',
      description: '基于ATR的趋势跟踪指标，结合价格和波动率计算支撑/阻力带。线在价格下方显示上升趋势，上方显示下降趋势。简单直观，适合趋势交易。',
      series: [] 
    },
    sr: { 
      enabled: false, 
      name: 'S/R', 
      zhName: '支撑阻力',
      description: '支撑与阻力线(Support/Resistance)，基于历史高低点自动识别关键价格位。支撑线为买方力量强区，阻力线为卖方力量强区。突破后角色互换。',
      series: [] 
    },
    macd: { 
      enabled: false, 
      name: 'MACD', 
      zhName: '指数平滑异同平均线',
      description: '由快线DIF(12日EMA-26日EMA)、慢线DEA(DIF的9日EMA)和柱状图(DIF-DEA)组成。DIF上穿DEA金叉看涨，下穿死叉看跌。柱状图表示多空力量强弱。',
      series: [] 
    },
    kdj: { 
      enabled: false, 
      name: 'KDJ', 
      zhName: '随机指标',
      description: '随机指标(Stochastic)，包含K值、D值(K的移动平均)、J值(3K-2D)。取值0-100，>80超买，<20超卖。K线上穿D线金叉看涨，下穿死叉看跌。J值更敏感。',
      series: [] 
    },
    rsi: { 
      enabled: false, 
      name: 'RSI', 
      zhName: '相对强弱指标',
      description: '相对强弱指标(Relative Strength Index)，衡量价格涨跌速度，取值0-100。>70超买区，<30超卖区，50为强弱分界线。可用于判断背离和反转信号。',
      series: [] 
    },
    stochrsi: { 
      enabled: false, 
      name: 'StochRSI', 
      zhName: '随机相对强弱指标',
      description: '将Stochastic公式应用于RSI值，比RSI更敏感。取值0-1，>0.8超买，<0.2超卖。K线上穿D线金叉看涨，下穿死叉看跌。适合捕捉短期机会。',
      series: [] 
    },
    cci: { 
      enabled: false, 
      name: 'CCI', 
      zhName: '顺势指标',
      description: '顺势指标(Commodity Channel Index)，衡量价格偏离统计平均值程度。>+100超买，<-100超卖，±100间为常态区。穿越±100线产生交易信号。',
      series: [] 
    },
    dmi: { 
      enabled: false, 
      name: 'DMI', 
      zhName: '趋向指标',
      description: '趋向指标(Directional Movement Index)，包含PDI(上升动向)、MDI(下降动向)、ADX(趋势强度)。PDI>MDI多头市场，MDI>PDI空头市场。ADX>25趋势强劲。',
      series: [] 
    },
    wr: { 
      enabled: false, 
      name: 'WR', 
      zhName: '威廉指标',
      description: '威廉指标(Williams %R)，反映超买超卖和价格动量。取值0到-100，>-20超买，<-80超卖。从超卖区向上突破-80为买入信号，从超买区向下突破-20为卖出信号。',
      series: [] 
    },
    obv: { 
      enabled: false, 
      name: 'OBV', 
      zhName: '能量潮',
      description: '能量潮(On-Balance Volume)，累计成交量指标。涨日加成交量，跌日减成交量。OBV上升表明资金流入，下降表明资金流出。与价格背离预示反转。',
      series: [] 
    },
    trix: { 
      enabled: false, 
      name: 'TRIX', 
      zhName: '三重指数平滑平均线',
      description: '三重指数平滑移动平均(Triple Exponentially Smoothed Average)，对价格进行三次指数平滑计算变化率。过滤短期波动，识别长期趋势。上穿零轴看涨，下穿看跌。',
      series: [] 
    },
    roc: { 
      enabled: false, 
      name: 'ROC', 
      zhName: '变动率指标',
      description: '变动率(Rate of Change)，当前价格相对N日前价格的百分比变化。正值表示上涨，负值表示下跌。可识别超买超卖和背离，配合其他指标使用。',
      series: [] 
    },
    mtm: { 
      enabled: false, 
      name: 'MTM', 
      zhName: '动量指标',
      description: '动量指标(Momentum)，当前收盘价减N日前收盘价。测量价格变化速度，>0上涨动能，<0下跌动能。与价格背离可预示反转。常用周期12日。',
      series: [] 
    },
    dma: { 
      enabled: false, 
      name: 'DMA', 
      zhName: '平行线差指标',
      description: '平行线差(Different of Moving Average)，短期均线减长期均线及其移动平均。DMA上穿AMA金叉看涨，下穿死叉看跌。反映短期趋势偏离长期趋势程度。',
      series: [] 
    },
    vr: { 
      enabled: false, 
      name: 'VR', 
      zhName: '成交量比率',
      description: '成交量比率(Volume Ratio)，上涨日成交量与下跌日成交量的比值。>160%过热，<70%低迷，70-160%正常。极端值往往预示反转。',
      series: [] 
    },
    brar: { 
      enabled: false, 
      name: 'BRAR', 
      zhName: '情绪指标',
      description: '人气指标AR(买卖气势)和意愿指标BR(买卖意愿)。AR反映市场人气，BR反映市场意愿。AR/BR>1多头，<1空头。两者配合判断市场情绪和潜在转折点。',
      series: [] 
    },
    psy: { 
      enabled: false, 
      name: 'PSY', 
      zhName: '心理线',
      description: '心理线(Psychological Line)，N日内上涨天数占比。取值0-100%，>75%超买，<25%超卖，50%为多空平衡。反映市场心理，配合其他指标判断买卖时机。',
      series: [] 
    },
    atr: { 
      enabled: false, 
      name: 'ATR', 
      zhName: '平均真实波幅',
      description: '平均真实波幅(Average True Range)，衡量市场波动性的指标。ATR值越大波动越剧烈，越小波动越平缓。不判断方向，常用于设置动态止损(价格±2-3倍ATR)和仓位管理。标准周期14。',
      series: [] 
    }
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
    psy: 180,
    atr: 180
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

    // 立即同步主图的时间轴状态到新创建的副图
    if (chart.value) {
      const mainTimeScale = chart.value.timeScale()
      const visibleRange = mainTimeScale.getVisibleLogicalRange()
      if (visibleRange) {
        subChart.timeScale().setVisibleLogicalRange(visibleRange)
      }
    }

    // 双向同步时间轴：副图 → 主图 + 其他副图
    subChart.timeScale().subscribeVisibleLogicalRangeChange((range) => {
      if (isSyncingTimeScale.value || !range) return
      
      isSyncingTimeScale.value = true
      try {
        // 同步到主图
        if (chart.value) {
          chart.value.timeScale().setVisibleLogicalRange(range)
        }
        
        // 同步到其他副图
        Object.entries(subCharts.value).forEach(([subKey, subChart]) => {
          if (subKey !== key && subChart) {
            subChart.timeScale().setVisibleLogicalRange(range)
          }
        })
      } finally {
        isSyncingTimeScale.value = false
      }
    })

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
        subChart.addLineSeries({ color: '#E91E63', lineWidth: 1, title: 'PSY' })
      ]
    } else if (key === 'atr' && indicators[key as keyof Indicators]) {
      indicators[key]!.series = [
        subChart.addLineSeries({ 
          color: '#FF9800', 
          lineWidth: 2, 
          title: 'ATR',
          lastValueVisible: true,
          priceLineVisible: true,
          priceLineWidth: 1,
          priceLineStyle: 2
        })
      ]
    }
  }

  const createMainIndicatorSeries = (key: string): void => {
    if (!chart.value) return

    if (key === 'ma') {
      indicators.ma.series = [
        chart.value.addLineSeries({ color: '#2196F3', lineWidth: 1, lastValueVisible: false, priceLineVisible: false }),
        chart.value.addLineSeries({ color: '#FF9800', lineWidth: 1, lastValueVisible: false, priceLineVisible: false }),
        chart.value.addLineSeries({ color: '#9C27B0', lineWidth: 1, lastValueVisible: false, priceLineVisible: false })
      ]
    } else if (key === 'maWithMacd') {
      indicators.maWithMacd.series = [
        chart.value.addLineSeries({ color: '#2962FF', lineWidth: 1, lastValueVisible: false, priceLineVisible: false }),
        chart.value.addLineSeries({ color: '#FF6D00', lineWidth: 1, lastValueVisible: false, priceLineVisible: false }),
        chart.value.addLineSeries({ color: '#9C27B0', lineWidth: 1, lastValueVisible: false, priceLineVisible: false })
      ]
    } else if (key === 'ema') {
      indicators.ema.series = [
        chart.value.addLineSeries({ color: '#00BCD4', lineWidth: 1, lastValueVisible: false, priceLineVisible: false }),
        chart.value.addLineSeries({ color: '#FFC107', lineWidth: 1, lastValueVisible: false, priceLineVisible: false }),
        chart.value.addLineSeries({ color: '#E91E63', lineWidth: 1, lastValueVisible: false, priceLineVisible: false })
      ]
    } else if (key === 'emaFib') {
      indicators.emaFib.series = [
        chart.value.addLineSeries({ color: '#4CAF50', lineWidth: 1, lastValueVisible: false, priceLineVisible: false }),
        chart.value.addLineSeries({ color: '#FF5722', lineWidth: 1, lastValueVisible: false, priceLineVisible: false }),
        chart.value.addLineSeries({ color: '#9C27B0', lineWidth: 1, lastValueVisible: false, priceLineVisible: false })
      ]
    } else if (key === 'boll') {
      indicators.boll.series = [
        chart.value.addLineSeries({ color: '#2196F3', lineWidth: 1, lastValueVisible: false, priceLineVisible: false }),
        chart.value.addLineSeries({ color: '#FFC107', lineWidth: 1, lastValueVisible: false, priceLineVisible: false }),
        chart.value.addLineSeries({ color: '#2196F3', lineWidth: 1, lastValueVisible: false, priceLineVisible: false })
      ]
    } else if (key === 'sar') {
      indicators.sar.series = chart.value.addLineSeries({ 
        color: '#FF6D00', 
        lineWidth: 2, 
        lineStyle: 2,
        lastValueVisible: false,
        priceLineVisible: false
      })
    } else if (key === 'supertrend') {
      indicators.supertrend.series = chart.value.addLineSeries({ 
        color: '#26a69a', 
        lineWidth: 2, 
        lastValueVisible: false,
        priceLineVisible: false
      })
    } else if (key === 'sr') {
      indicators.sr.series = [
        chart.value.addLineSeries({ color: '#ef5350', lineWidth: 1, lineStyle: 2, lastValueVisible: false, priceLineVisible: false }),
        chart.value.addLineSeries({ color: '#26a69a', lineWidth: 1, lineStyle: 2, lastValueVisible: false, priceLineVisible: false })
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

    // Update MA with MACD
    if (results.maWithMacd && Array.isArray(indicators.maWithMacd.series)) {
      results.maWithMacd.forEach((data: any, i: number) => {
        if (indicators.maWithMacd.series[i]) {
          indicators.maWithMacd.series[i].setData(data.map((d: any) => ({ time: d.time as any, value: d.value })))
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

    // Update EMA Fibonacci
    if (results.emaFib && Array.isArray(indicators.emaFib.series)) {
      results.emaFib.forEach((data: any, i: number) => {
        if (indicators.emaFib.series[i]) {
          indicators.emaFib.series[i].setData(data.map((d: any) => ({ time: d.time as any, value: d.value })))
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

    // Update ATR
    if (results.atr && Array.isArray(indicators.atr.series) && indicators.atr.series[0]) {
      indicators.atr.series[0].setData(results.atr.map((d: any) => ({ time: d.time as any, value: d.value })))
    }
  }

  const enabledSubIndicators: ComputedRef<Record<string, IndicatorConfig>> = computed(() => {
    const enabled: Record<string, IndicatorConfig> = {}
    // 副图指标列表：不是覆盖在主图上的指标
    const subIndicatorKeys = ['macd', 'rsi', 'kdj', 'stochrsi', 'cci', 'dmi', 'wr', 'obv', 'trix', 'roc', 'mtm', 'dma', 'vr', 'brar', 'psy', 'atr']
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

  // 计算主图指标的图例信息
  const mainChartLegends = computed(() => {
    const legends: Array<{ indicator: string; lines: Array<{ name: string; color: string }> }> = []
    
    // MA(5,10,20) - 标准
    if (indicators.ma?.enabled) {
      legends.push({
        indicator: 'MA',
        lines: [
          { name: 'MA5', color: '#2196F3' },
          { name: 'MA10', color: '#FF9800' },
          { name: 'MA20', color: '#9C27B0' }
        ]
      })
    }
    
    // MA(9,12,26) - MACD标准
    if (indicators.maWithMacd?.enabled) {
      legends.push({
        indicator: 'MA',
        lines: [
          { name: 'MA9', color: '#2962FF' },
          { name: 'MA12', color: '#FF6D00' },
          { name: 'MA26', color: '#9C27B0' }
        ]
      })
    }
    
    // EMA(5,10,20)
    if (indicators.ema?.enabled) {
      legends.push({
        indicator: 'EMA',
        lines: [
          { name: 'EMA5', color: '#00BCD4' },
          { name: 'EMA10', color: '#FFC107' },
          { name: 'EMA20', color: '#E91E63' }
        ]
      })
    }
    
    // EMA(9,21,55) Fibonacci
    if (indicators.emaFib?.enabled) {
      legends.push({
        indicator: 'EMA',
        lines: [
          { name: 'EMA9', color: '#4CAF50' },
          { name: 'EMA21', color: '#FF5722' },
          { name: 'EMA55', color: '#9C27B0' }
        ]
      })
    }
    
    // BOLL
    if (indicators.boll?.enabled) {
      legends.push({
        indicator: 'BOLL',
        lines: [
          { name: 'BOLL Upper', color: '#2196F3' },
          { name: 'BOLL Mid', color: '#FFC107' },
          { name: 'BOLL Lower', color: '#2196F3' }
        ]
      })
    }
    
    // SAR
    if (indicators.sar?.enabled) {
      legends.push({
        indicator: 'SAR',
        lines: [{ name: 'SAR', color: '#FF6D00' }]
      })
    }
    
    // SuperTrend
    if (indicators.supertrend?.enabled) {
      legends.push({
        indicator: 'SuperTrend',
        lines: [{ name: 'SuperTrend', color: '#26a69a' }]
      })
    }
    
    // Support/Resistance
    if (indicators.sr?.enabled) {
      legends.push({
        indicator: 'SR',
        lines: [
          { name: 'Resistance', color: '#ef5350' },
          { name: 'Support', color: '#26a69a' }
        ]
      })
    }
    
    // 按图例数量降序排序：图例多的在前，图例少的在后
    return legends.sort((a, b) => b.lines.length - a.lines.length)
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
    if (['vol', 'ma', 'maWithMacd', 'ema', 'emaFib', 'boll', 'sar', 'supertrend', 'sr'].includes(key)) {
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
    mainChartLegends,
    setSubChartRef,
    triggerWorkerCalculation,
    rebuildSubCharts,
    cleanup
  }
}
