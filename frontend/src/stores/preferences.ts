import { defineStore } from 'pinia'

export type ColorScheme = 'green-up' | 'red-up'

export interface ProxySettings {
  enabled: boolean
  containerAutoHost: boolean
  proxyUrl: string
}

const COLOR_SCHEME_KEY = 'geneticgrid_color_scheme'
const CURRENCY_KEY = 'geneticgrid_currency'
const PROXY_SETTINGS_KEY = 'geneticgrid_proxy_settings'

const DEFAULT_COLOR_SCHEME: ColorScheme = 'green-up'
const DEFAULT_CURRENCY = 'USDT'
const DEFAULT_PROXY_SETTINGS: ProxySettings = {
  enabled: true,
  containerAutoHost: true,
  proxyUrl: 'socks5://127.0.0.1:1080'
}

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
    currency: resolveStoredValue(CURRENCY_KEY, DEFAULT_CURRENCY),
    proxySettings: (() => {
      if (typeof window === 'undefined') {
        return { ...DEFAULT_PROXY_SETTINGS }
      }

      const raw = window.localStorage.getItem(PROXY_SETTINGS_KEY)
      if (!raw) {
        return { ...DEFAULT_PROXY_SETTINGS }
      }

      try {
        const parsed = JSON.parse(raw) as Partial<ProxySettings>
        return {
          ...DEFAULT_PROXY_SETTINGS,
          ...parsed
        }
      } catch {
        return { ...DEFAULT_PROXY_SETTINGS }
      }
    })()
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
    setProxySettings(settings: ProxySettings): void {
      this.proxySettings = { ...settings }
      if (typeof window !== 'undefined') {
        window.localStorage.setItem(PROXY_SETTINGS_KEY, JSON.stringify(this.proxySettings))
      }
    },
    async loadProxySettings(): Promise<void> {
      try {
        const response = await fetch('/api/proxy-config/')
        if (!response.ok) {
          return
        }

        const payload = await response.json()
        if (payload.code !== 0 || !payload.data) {
          return
        }

        const httpUrl = payload.data.http?.configured_url || 'http://127.0.0.1:8080'
        const socks5Url = payload.data.socks5?.configured_url || 'socks5://127.0.0.1:1080'
        const socks5Avail = Boolean(payload.data.socks5?.available)
        const httpAvail = Boolean(payload.data.http?.available)
        const proxyUrl = socks5Avail ? socks5Url : httpAvail ? httpUrl : socks5Url
        this.setProxySettings({
          enabled: Boolean(payload.data.enabled),
          containerAutoHost: Boolean(payload.data.container_auto_host),
          proxyUrl
        })
      } catch {
        // 网络失败时保留本地设置
      }
    },
    async saveProxySettings(settings: ProxySettings): Promise<string | null> {
      const response = await fetch('/api/proxy-config/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          enabled: settings.enabled,
          container_auto_host: settings.containerAutoHost,
          ...(settings.proxyUrl.startsWith('http://') ? { http_url: settings.proxyUrl } : {}),
          ...(settings.proxyUrl.startsWith('socks5://') ? { socks5_url: settings.proxyUrl } : {})
        })
      })

      const payload = await response.json()
      if (!response.ok || payload.code !== 0) {
        return payload.error || `保存失败 (HTTP ${response.status})`
      }

      this.setProxySettings({
        enabled: Boolean(payload.data.enabled),
        containerAutoHost: Boolean(payload.data.container_auto_host),
        proxyUrl: settings.proxyUrl
      })

      return null
    },
    applyColorsToDocument(): void {
      if (typeof document === 'undefined') return
      const root = document.documentElement
      root.style.setProperty('--up-color', this.upColor)
      root.style.setProperty('--down-color', this.downColor)
    }
  }
})
