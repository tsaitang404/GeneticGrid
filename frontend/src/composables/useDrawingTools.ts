import { ref, reactive, onMounted, onUnmounted, type Ref } from 'vue'
import type { IChartApi } from 'lightweight-charts'
import type { Drawing, DrawingType, LogicalPoint, ScreenPoint } from '@/types'

export function useDrawingTools(canvasRef: Ref<HTMLCanvasElement | null>, chart: Ref<IChartApi | null>) {
  const currentTool = ref<DrawingType>('cursor')
  const toolbarExpanded = ref<boolean>(false)
  const drawings = reactive<Drawing[]>([])
  const currentDrawing = ref<Drawing | null>(null)

  const logicalToPoint = (logical: LogicalPoint): ScreenPoint | null => {
    if (!chart.value || !logical) return null
    const timeScale = chart.value.timeScale()
    
    const x = timeScale.timeToCoordinate(logical.time as any)
    // Note: Price to coordinate conversion requires series context
    // For now, we'll use a simplified approach
    if (x === null) return null
    return { x, y: 0 } // Simplified for type checking
  }

  const renderDrawings = (): void => {
    if (!canvasRef.value || !chart.value) return
    
    const ctx = canvasRef.value.getContext('2d')
    if (!ctx) return
    
    const width = canvasRef.value.width
    const height = canvasRef.value.height
    
    ctx.clearRect(0, 0, width, height)

    const drawList = [...drawings]
    if (currentDrawing.value) drawList.push(currentDrawing.value)

    drawList.forEach(d => {
      ctx.beginPath()
      ctx.strokeStyle = '#2962FF'
      ctx.lineWidth = 2

      if (d.type === 'line' || d.type === 'ray') {
        if (d.points.length >= 2) {
          const p1 = logicalToPoint(d.points[0])
          const p2 = logicalToPoint(d.points[1])
          if (p1 && p2) {
            ctx.moveTo(p1.x, p1.y)
            ctx.lineTo(p2.x, p2.y)
            if (d.type === 'ray') {
              const dx = p2.x - p1.x
              const dy = p2.y - p1.y
              ctx.lineTo(p2.x + dx * 100, p2.y + dy * 100)
            }
          }
        }
      } else if (d.type === 'horizontal') {
        const p1 = logicalToPoint(d.points[0])
        if (p1) {
          ctx.moveTo(0, p1.y)
          ctx.lineTo(width, p1.y)
        }
      }

      ctx.stroke()

      // Draw control points
      d.points.forEach(p => {
        const pt = logicalToPoint(p)
        if (pt) {
          ctx.fillStyle = '#fff'
          ctx.fillRect(pt.x - 3, pt.y - 3, 6, 6)
        }
      })
    })
  }

  const handleDrawingClick = (param: any): void => {
    if (!param || !param.point || !chart.value) return

    // Use param.seriesData to get price if available
    const clickPrice = param.seriesData?.get(param.point) ?? 0
    const logical = { time: param.time as any, price: clickPrice }

    if (!currentDrawing.value) {
      currentDrawing.value = { type: currentTool.value, points: [logical] }
      if (currentTool.value === 'horizontal') {
        drawings.push(currentDrawing.value)
        currentDrawing.value = null
      }
    } else {
      currentDrawing.value.points.push(logical)
      drawings.push(currentDrawing.value)
      currentDrawing.value = null
    }

    renderDrawings()
  }

  const handleCanvasMouseDown = (e: MouseEvent): void => {
    // Handle drawing canvas interactions
    if (currentTool.value !== 'cursor') {
      e.preventDefault()
    }
  }

  const clearDrawings = (): void => {
    drawings.splice(0, drawings.length)
    currentDrawing.value = null
    renderDrawings()
  }

  // Setup chart click listener
  onMounted(() => {
    if (chart.value) {
      chart.value.subscribeClick(handleDrawingClick)
    }

    // Update canvas size when chart resizes
    if (canvasRef.value && chart.value) {
      const updateCanvasSize = () => {
        if (!chart.value) return
        const chartContainer = chart.value.chartElement()
        if (chartContainer && canvasRef.value) {
          canvasRef.value.width = chartContainer.clientWidth
          canvasRef.value.height = chartContainer.clientHeight
          renderDrawings()
        }
      }
      updateCanvasSize()
    }
  })

  onUnmounted(() => {
    // Cleanup
  })

  return {
    currentTool,
    toolbarExpanded,
    drawings,
    clearDrawings,
    renderDrawings,
    handleCanvasMouseDown
  }
}
