import { defineStore } from 'pinia'

export type ColorScheme = 'green-up' | 'red-up'

const COLOR_SCHEME_KEY = 'geneticgrid_color_scheme'
const CURRENCY_KEY = 'geneticgrid_currency'

const DEFAULT_COLOR_SCHEME: ColorScheme = 'green-up'
const DEFAULT_CURRENCY = 'USDT'

interface ColorPalette {
  up: string
  down: string
}

const COLOR_PALETTES: Record<ColorScheme, ColorPalette> = {
  'green-up': {
    up: '#26a69a',
    down: '#ef5350'
  },
  'red-up': {
    up: '#ef5350',
    down: '#26a69a'
  }
}

const withAlpha = (hex: string, alpha: number): string => {
  const sanitized = hex.replace('#', '')
  const bigint = parseInt(sanitized, 16)
  const r = (bigint >> 16) & 255
  const g = (bigint >> 8) & 255
  const b = bigint & 255
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}

const resolveStoredValue = (key: string, fallback: string): string => {
  if (typeof window === 'undefined') {
    return fallback
  }
  const stored = window.localStorage.getItem(key)
  return stored ?? fallback
}

export const usePreferencesStore = defineStore('preferences', {
  state: () => ({
    colorScheme: resolveStoredValue(COLOR_SCHEME_KEY, DEFAULT_COLOR_SCHEME) as ColorScheme,
    currency: resolveStoredValue(CURRENCY_KEY, DEFAULT_CURRENCY)
  }),
  getters: {
    upColor(state): string {
      return COLOR_PALETTES[state.colorScheme].up
    },
    downColor(state): string {
      return COLOR_PALETTES[state.colorScheme].down
    },
    volumeUpColor(): string {
      return withAlpha(this.upColor, 0.5)
    },
    volumeDownColor(): string {
      return withAlpha(this.downColor, 0.5)
    }
  },
  actions: {
    initialize(): void {
      this.applyColorsToDocument()
    },
    setColorScheme(scheme: ColorScheme): void {
      if (this.colorScheme === scheme) return
      this.colorScheme = scheme
      if (typeof window !== 'undefined') {
        window.localStorage.setItem(COLOR_SCHEME_KEY, scheme)
      }
      this.applyColorsToDocument()
    },
    setCurrency(currency: string): void {
      if (this.currency === currency) return
      this.currency = currency
      if (typeof window !== 'undefined') {
        window.localStorage.setItem(CURRENCY_KEY, currency)
      }
    },
    applyColorsToDocument(): void {
      if (typeof document === 'undefined') return
      const root = document.documentElement
      root.style.setProperty('--up-color', this.upColor)
      root.style.setProperty('--down-color', this.downColor)
    }
  }
})
