import { ref, reactive, type Ref } from 'vue'
import type { IChartApi } from 'lightweight-charts'

export function useChartResize(chart: Ref<IChartApi | null>, subCharts: Ref<Record<string, IChartApi>>) {
  const mainChartHeight = ref<number>(450)
  const subChartHeights = reactive<Record<string, number>>({
    macd: 180,
    rsi: 180,
    kdj: 180
  })

  const resizingTarget = ref<string | null>(null)
  const resizeStartY = ref<number>(0)
  const resizeStartHeight = ref<number>(0)

  const startResize = (target: string, event: MouseEvent): void => {
    resizingTarget.value = target
    resizeStartY.value = event.clientY

    if (target === 'main') {
      resizeStartHeight.value = mainChartHeight.value
    } else {
      if (!subChartHeights[target]) {
        subChartHeights[target] = 180
      }
      resizeStartHeight.value = subChartHeights[target]
    }

    window.addEventListener('mousemove', handleResizeMove)
    window.addEventListener('mouseup', stopResize)
    document.body.style.cursor = 'ns-resize'
    document.body.style.userSelect = 'none'
  }

  const handleResizeMove = (event: MouseEvent): void => {
    if (!resizingTarget.value) return

    const delta = event.clientY - resizeStartY.value
    const newHeight = Math.max(100, resizeStartHeight.value + delta)

    if (resizingTarget.value === 'main') {
      mainChartHeight.value = newHeight
      if (chart.value) {
        chart.value.applyOptions({ height: newHeight })
      }
    } else {
      subChartHeights[resizingTarget.value] = newHeight
      if (subCharts.value[resizingTarget.value]) {
        subCharts.value[resizingTarget.value].applyOptions({ height: newHeight })
      }
    }
  }

  const stopResize = (): void => {
    resizingTarget.value = null
    window.removeEventListener('mousemove', handleResizeMove)
    window.removeEventListener('mouseup', stopResize)
    document.body.style.cursor = ''
    document.body.style.userSelect = ''
  }

  return {
    mainChartHeight,
    subChartHeights,
    startResize
  }
}
