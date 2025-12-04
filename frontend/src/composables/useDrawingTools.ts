import { ref, reactive, onMounted, onUnmounted, type Ref } from 'vue'
import type { IChartApi, ISeriesApi } from 'lightweight-charts'
import type { Drawing, DrawingType, LogicalPoint, ScreenPoint } from '@/types'

export function useDrawingTools(
  canvasRef: Ref<HTMLCanvasElement | null>,
  chart: Ref<IChartApi | null>,
  candleSeries: Ref<ISeriesApi<'Candlestick'> | null>,
  lineSeries: Ref<ISeriesApi<'Line'> | null>,
  isTimelineMode: Ref<boolean>
) {
  const currentTool = ref<DrawingType>('cursor')
  const toolbarExpanded = ref<boolean>(false)
  const drawings = reactive<Drawing[]>([])
  const currentDrawing = ref<Drawing | null>(null)

  const logicalToPoint = (logical: LogicalPoint): ScreenPoint | null => {
    if (!chart.value || !logical) return null
    if (!logical.time && logical.time !== 0) return null
    
    const timeScale = chart.value.timeScale()
    const activeSeries = isTimelineMode.value ? lineSeries.value : candleSeries.value
    if (!activeSeries) return null
    
    const x = timeScale.timeToCoordinate(logical.time as any)
    const y = activeSeries.priceToCoordinate(logical.price)
    
    if (x === null || y === null) return null
    return { x, y: y as number }
  }

  const renderDrawings = (): void => {
    if (!canvasRef.value || !chart.value) return
    
    const ctx = canvasRef.value.getContext('2d')
    if (!ctx) return
    
    const width = canvasRef.value.width
    const height = canvasRef.value.height
    
    ctx.clearRect(0, 0, width, height)

    // Get price scale width (right side) and time scale height (bottom)
    const timeScale = chart.value.timeScale()
    const activeSeries = isTimelineMode.value ? lineSeries.value : candleSeries.value
    if (!activeSeries) return
    
    const priceScale = activeSeries.priceScale()
    const priceScaleWidth = priceScale.width()
    const timeScaleHeight = timeScale.height()
    
    // Calculate drawable area (excluding axes)
    const drawableX = 0
    const drawableY = 0
    const drawableWidth = width - priceScaleWidth
    const drawableHeight = height - timeScaleHeight
    
    // Save context state
    ctx.save()
    
    // Clip to drawable area only (exclude axes)
    ctx.beginPath()
    ctx.rect(drawableX, drawableY, drawableWidth, drawableHeight)
    ctx.clip()

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
    
    // Restore context state (remove clipping)
    ctx.restore()
  }

  const handleDrawingClick = (param: any): void => {
    // Only handle clicks when in drawing mode (not cursor mode)
    if (currentTool.value === 'cursor') return
    if (!param || !param.point || !chart.value) return
    
    // Validate time parameter
    if (!param.time && param.time !== 0) {
      console.warn('Drawing click: invalid time parameter', param)
      return
    }

    // Get price from y coordinate
    const activeSeries = isTimelineMode.value ? lineSeries.value : candleSeries.value
    if (!activeSeries) return
    
    const clickPrice = activeSeries.coordinateToPrice(param.point.y)
    if (clickPrice === null) return
    
    // Ensure time is a number (Unix timestamp)
    const timeValue = typeof param.time === 'number' ? param.time : Number(param.time)
    if (isNaN(timeValue)) {
      console.warn('Drawing click: time is not a number', param.time)
      return
    }
    
    const logical = { time: timeValue, price: clickPrice as number }

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

  const handleCanvasMouseDown = (): void => {
    // Canvas is always pointer-events: none, interactions handled by chart subscribeClick
  }

  const clearDrawings = (): void => {
    drawings.splice(0, drawings.length)
    currentDrawing.value = null
    renderDrawings()
  }

  let animationFrameId: number | null = null
  let lastCanvasWidth = 0
  let lastCanvasHeight = 0

  const startContinuousRendering = (): void => {
    const render = () => {
      if (canvasRef.value && chart.value) {
        const chartContainer = chart.value.chartElement()
        if (chartContainer) {
          const currentWidth = chartContainer.clientWidth
          const currentHeight = chartContainer.clientHeight
          
          // Update canvas size if changed
          if (currentWidth !== lastCanvasWidth || currentHeight !== lastCanvasHeight) {
            canvasRef.value.width = currentWidth
            canvasRef.value.height = currentHeight
            lastCanvasWidth = currentWidth
            lastCanvasHeight = currentHeight
          }
          
          // Always render to track price scale changes
          renderDrawings()
        }
      }
      animationFrameId = requestAnimationFrame(render)
    }
    render()
  }

  const stopContinuousRendering = (): void => {
    if (animationFrameId !== null) {
      cancelAnimationFrame(animationFrameId)
      animationFrameId = null
    }
  }

  const setupChartListener = (): void => {
    if (chart.value) {
      chart.value.subscribeClick(handleDrawingClick)
      
      // Update canvas size initially
      if (canvasRef.value) {
        const chartContainer = chart.value.chartElement()
        if (chartContainer) {
          canvasRef.value.width = chartContainer.clientWidth
          canvasRef.value.height = chartContainer.clientHeight
          lastCanvasWidth = chartContainer.clientWidth
          lastCanvasHeight = chartContainer.clientHeight
          renderDrawings()
        }
      }
      
      // Start continuous rendering to track all changes
      startContinuousRendering()
    }
  }

  // Setup chart click listener
  onMounted(() => {
    setupChartListener()
  })

  // Watch for chart changes and re-setup listener
  const unwatchChart = () => {
    let lastChart: IChartApi | null = null
    const checkChart = setInterval(() => {
      if (chart.value && chart.value !== lastChart) {
        lastChart = chart.value
        stopContinuousRendering() // Stop old rendering loop
        setupChartListener() // Start new one
      }
    }, 100)
    
    return () => clearInterval(checkChart)
  }
  
  const stopWatch = unwatchChart()

  onUnmounted(() => {
    stopWatch()
    stopContinuousRendering()
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
