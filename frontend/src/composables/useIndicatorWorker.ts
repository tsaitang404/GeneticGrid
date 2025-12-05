import { ref } from 'vue'
import type { Candle, Indicators } from '@/types'

interface WorkerMessage {
  id: number
  type: 'CALCULATE' | 'RESULT'
  data?: {
    candles: Candle[]
    indicators: string[]
  }
  results?: any
}

export function useIndicatorWorker() {
  const worker = ref<Worker | null>(null)
  const taskCounter = ref<number>(0)
  const pendingTasks = ref<Map<number, (results: any) => void>>(new Map())

  const initWorker = (): void => {
    if (worker.value) return

    try {
      // Vite base 是 /static/dist/，所以 public 目录的文件也在这个路径下
      const workerPath = import.meta.env.BASE_URL + 'indicator-worker.js'
      
      worker.value = new Worker(workerPath, { type: 'classic' })
      
      worker.value.onmessage = (e: MessageEvent<WorkerMessage>) => {
        const { id, type, results } = e.data
        
        if (type === 'RESULT' && results) {
          const callback = pendingTasks.value.get(id)
          if (callback) {
            callback(results)
            pendingTasks.value.delete(id)
          }
        }
      }
      
      worker.value.onerror = (error) => {
        console.error('Indicator worker error:', error)
        console.error('Worker path:', workerPath)
        console.error('BASE_URL:', import.meta.env.BASE_URL)
      }
      
      console.log('✅ Indicator worker initialized:', workerPath)
    } catch (error) {
      console.error('Failed to initialize indicator worker:', error)
    }
  }

  const calculateIndicators = (
    candles: Candle[],
    indicators: Indicators
  ): Promise<any> => {
    return new Promise((resolve) => {
      if (!worker.value) initWorker()
      if (!worker.value) {
        resolve({})
        return
      }

      // Get list of enabled indicators
      const activeIndicators: string[] = []
      for (const [key, config] of Object.entries(indicators)) {
        if (config.enabled && key !== 'vol') {
          activeIndicators.push(key)
        }
      }

      if (activeIndicators.length === 0) {
        resolve({})
        return
      }

      taskCounter.value++
      const taskId = taskCounter.value

      pendingTasks.value.set(taskId, resolve)

      worker.value.postMessage({
        id: taskId,
        type: 'CALCULATE',
        data: {
          candles: candles.map(c => ({
            time: c.time,
            open: c.open,
            high: c.high,
            low: c.low,
            close: c.close,
            volume: c.volume
          })),
          indicators: activeIndicators
        }
      })
    })
  }

  const terminateWorker = (): void => {
    if (worker.value) {
      worker.value.terminate()
      worker.value = null
    }
    pendingTasks.value.clear()
  }

  return {
    initWorker,
    calculateIndicators,
    terminateWorker
  }
}
