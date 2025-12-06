import type { Ref } from 'vue'

// Candle data types
export interface Candle {
  time: number
  open: number
  high: number
  low: number
  close: number
  volume: number
}

// Indicator data types
export interface IndicatorData {
  time: number
  value: number
  color?: string
}

export interface MACDData {
  dif: IndicatorData[]
  dea: IndicatorData[]
  histogram: IndicatorData[]
}

export interface KDJData {
  k: IndicatorData[]
  d: IndicatorData[]
  j: IndicatorData[]
}

export interface BOLLData {
  upper: IndicatorData[]
  middle: IndicatorData[]
  lower: IndicatorData[]
}

// Drawing types
export type DrawingType = 'cursor' | 'line' | 'ray' | 'horizontal' | 'ratio' | 'parallel' | 'delete'

export interface LogicalPoint {
  time: number
  price: number
}

export interface ScreenPoint {
  x: number
  y: number
}

export interface DrawingMeta {
  parallelLineCount?: number
}

export interface Drawing {
  type: DrawingType
  points: LogicalPoint[]
  meta?: DrawingMeta
}

// Indicator config types
export interface IndicatorConfig {
  enabled: boolean
  name: string
  series: any | any[]
  label?: string
  title?: string
  zhName?: string  // 中文名称
  description?: string  // 指标说明
}

export interface Indicators {
  vol: IndicatorConfig
  ma: IndicatorConfig
  maWithMacd: IndicatorConfig
  ema: IndicatorConfig
  emaFib: IndicatorConfig
  boll: IndicatorConfig
  sar: IndicatorConfig
  supertrend: IndicatorConfig
  sr: IndicatorConfig
  macd: IndicatorConfig
  kdj: IndicatorConfig
  rsi: IndicatorConfig
  stochrsi: IndicatorConfig
  cci: IndicatorConfig
  dmi: IndicatorConfig
  wr: IndicatorConfig
  obv: IndicatorConfig
  trix: IndicatorConfig
  roc: IndicatorConfig
  mtm: IndicatorConfig
  dma: IndicatorConfig
  vr: IndicatorConfig
  brar: IndicatorConfig
  psy: IndicatorConfig
  atr: IndicatorConfig
}

export interface ChartColorRefs {
  up: Ref<string>
  down: Ref<string>
  volumeUp: Ref<string>
  volumeDown: Ref<string>
}

// Chart options
export interface ChartOptions {
  symbol: { value: string }
  bar: { value: string }
  source: { value: string }
  exchangeRate?: { value: number }
  colors?: ChartColorRefs
  onLoading?: (loading: boolean) => void
  onError?: (error: ChartError) => void
  onPriceUpdate?: (price: string, change: string, isUp: boolean) => void
}

// Error type
export interface ChartError {
  show: boolean
  message: string
  detail?: string
}

// Tooltip data
export interface TooltipData {
  time: number
  open?: number
  high?: number
  low?: number
  close: number
  volume: number
  changePercent?: string
  isUp: boolean
}

// API response types
export interface APIResponse<T = any> {
  code: number
  data?: T
  error?: string
}

export interface TickerData {
  last: string
  open24h: string
  high24h: string
  low24h: string
  vol24h: string
  changePercent: string
  isUp: boolean
}

