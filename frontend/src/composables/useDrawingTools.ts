import { ref, reactive, onMounted, onUnmounted, watch, toRaw, type Ref } from 'vue'
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
  const previewPoint = ref<LogicalPoint | null>(null)
  const editingDrawing = ref<Drawing | null>(null) // 正在编辑的线条
  const editingPointIndex = ref<number>(-1) // 正在编辑的控制点索引
  const isDragging = ref<boolean>(false) // 是否正在拖拽
  let suppressNextClick = false
  const DELETE_TOLERANCE = 8
  type PriceLineHandle = ReturnType<NonNullable<ISeriesApi<'Candlestick'>['createPriceLine']>>
  interface HorizontalPriceLineRef {
    series: ISeriesApi<'Candlestick'> | ISeriesApi<'Line'>
    priceLine: PriceLineHandle
  }

  const horizontalPriceLines = new Map<Drawing, HorizontalPriceLineRef>()
  const horizontalPriceLabels = new Map<Drawing, HTMLDivElement>()

  const distanceSquared = (a: ScreenPoint, b: ScreenPoint): number => {
    const dx = a.x - b.x
    const dy = a.y - b.y
    return dx * dx + dy * dy
  }

  const distanceToSegmentSquared = (p: ScreenPoint, a: ScreenPoint, b: ScreenPoint): number => {
    const lengthSquared = distanceSquared(a, b)
    if (lengthSquared === 0) return distanceSquared(p, a)
    let t = ((p.x - a.x) * (b.x - a.x) + (p.y - a.y) * (b.y - a.y)) / lengthSquared
    t = Math.max(0, Math.min(1, t))
    const projection: ScreenPoint = {
      x: a.x + t * (b.x - a.x),
      y: a.y + t * (b.y - a.y)
    }
    return distanceSquared(p, projection)
  }

  const findDrawingNearPoint = (point: ScreenPoint, tolerance = DELETE_TOLERANCE): Drawing | null => {
    const toleranceSquared = tolerance * tolerance
    for (let i = drawings.length - 1; i >= 0; i -= 1) {
      const drawing = drawings[i]
      if (drawing.type === 'delete') continue

      const screenPoints = drawing.points
        .map(pt => logicalToPoint(pt))
        .filter((p): p is ScreenPoint => p !== null)

      if (screenPoints.length === 0) continue

      if (screenPoints.some(p => distanceSquared(p, point) <= toleranceSquared)) {
        return drawing
      }

      if (drawing.type === 'horizontal' && screenPoints[0]) {
        if (Math.abs(screenPoints[0].y - point.y) <= tolerance) {
          return drawing
        }
      }

      for (let j = 0; j < screenPoints.length - 1; j += 1) {
        const a = screenPoints[j]
        const b = screenPoints[j + 1]
        if (distanceToSegmentSquared(point, a, b) <= toleranceSquared) {
          return drawing
        }
      }
    }
    return null
  }

  const findControlPoint = (point: ScreenPoint, drawingType: DrawingType): { drawing: Drawing, pointIndex: number } | null => {
    const tolerance = 20 // 增加到 20px,更容易点击
    const toleranceSquared = tolerance * tolerance
    
    for (let i = drawings.length - 1; i >= 0; i--) {
      const drawing = drawings[i]
      if (drawing.type !== drawingType) {
        continue
      }
      
      const screenPoints = drawing.points
        .map(pt => logicalToPoint(pt))
        .filter((p): p is ScreenPoint => p !== null)
      
      for (let j = 0; j < screenPoints.length; j++) {
        const dist = distanceSquared(screenPoints[j], point)
        if (dist <= toleranceSquared) {
          return { drawing, pointIndex: j }
        }
      }
    }
    return null
  }

  const beginControlPointEdit = (
    controlPoint: { drawing: Drawing, pointIndex: number },
    toolType: DrawingType,
    suppressUpcomingClick: boolean
  ): void => {
    currentTool.value = toolType
    isDragging.value = true
    editingDrawing.value = controlPoint.drawing
    editingPointIndex.value = controlPoint.pointIndex
    previewPoint.value = null
    suppressNextClick = suppressUpcomingClick

    if (chart.value) {
      chart.value.applyOptions({
        handleScroll: false,
        handleScale: false
      })
    }
  }

  const activateControlPointAt = (
    screenPoint: ScreenPoint,
    options?: {
      originalEvent?: { stopPropagation?: () => void, preventDefault?: () => void }
      suppressUpcomingClick?: boolean
      startEdit?: boolean
    }
  ): { drawing: Drawing, pointIndex: number, toolType: DrawingType } | null => {
    const suppressClick = options?.suppressUpcomingClick ?? false
    const shouldStartEdit = options?.startEdit ?? true
    for (const toolType of ['line', 'ray', 'horizontal'] as DrawingType[]) {
      const controlPoint = findControlPoint(screenPoint, toolType)
      if (controlPoint) {
        if (shouldStartEdit) {
          beginControlPointEdit(controlPoint, toolType, suppressClick)
        } else if (suppressClick) {
          suppressNextClick = true
        }
        options?.originalEvent?.stopPropagation?.()
        options?.originalEvent?.preventDefault?.()
        return { drawing: controlPoint.drawing, pointIndex: controlPoint.pointIndex, toolType }
      }
    }
    return null
  }

  const getActiveSeries = (): ISeriesApi<'Candlestick'> | ISeriesApi<'Line'> | null => {
    return isTimelineMode.value ? lineSeries.value : candleSeries.value
  }

  const getLatestPriceLabelColors = () => {
    if (typeof window === 'undefined') {
      return { background: '#FFD54F', text: '#000000' }
    }
    const styles = getComputedStyle(document.documentElement)
    const background = styles.getPropertyValue('--latest-price-label-bg').trim() || '#FFD54F'
    const text = styles.getPropertyValue('--latest-price-label-text').trim() || '#000000'
    return { background, text }
  }
  const removeHorizontalLabel = (drawing: Drawing): void => {
    const key = toRaw(drawing)
    const label = horizontalPriceLabels.get(key)
    if (label && label.parentElement) {
      label.parentElement.removeChild(label)
    }
    horizontalPriceLabels.delete(key)
  }

  const ensureHorizontalLabel = (drawing: Drawing): HTMLDivElement | null => {
    if (!chart.value) return null
    const container = chart.value.chartElement()
    if (!container) return null

    const key = toRaw(drawing)
    let label = horizontalPriceLabels.get(key)
    if (label && label.parentElement !== container) {
      label.parentElement?.removeChild(label)
      horizontalPriceLabels.delete(key)
      label = undefined
    }

    if (!label) {
      label = document.createElement('div')
      label.className = 'horizontal-price-label'
      label.style.display = 'none'
      container.appendChild(label)
      horizontalPriceLabels.set(key, label)
    }

    return label
  }

  const formatLabelPrice = (price: number): string => {
    if (!Number.isFinite(price)) return '--'
    if (price >= 100000) return price.toLocaleString()
    if (price >= 1000) return price.toLocaleString(undefined, { maximumFractionDigits: 2 })
    if (price >= 1) return price.toFixed(2)
    return price.toPrecision(4)
  }

  const updateHorizontalLabelPosition = (drawing: Drawing): void => {
    if (drawing.type !== 'horizontal') return
    const price = drawing.points[0]?.price
    if (price === undefined) {
      removeHorizontalLabel(drawing)
      return
    }

    const activeSeries = getActiveSeries()
    if (!activeSeries || !chart.value) return

    const coordinate = activeSeries.priceToCoordinate(price)
    const label = ensureHorizontalLabel(drawing)
    if (!label) return

    if (coordinate === null || coordinate === undefined) {
      label.style.display = 'none'
      return
    }

    const container = chart.value.chartElement()
    if (!container) {
      label.style.display = 'none'
      return
    }

    const chartHeight = container.clientHeight
    const timeScaleHeight = chart.value.timeScale().height()
    const labelHeight = label.offsetHeight || 20
    const topMargin = 5
    const bottomMargin = timeScaleHeight + 5
    const rawTop = (coordinate as number) - labelHeight / 2
    const clampedTop = Math.max(topMargin, Math.min(chartHeight - bottomMargin - labelHeight, rawTop))

    label.style.top = `${clampedTop}px`
    label.textContent = formatLabelPrice(price)
    label.style.display = 'block'
  }

  const removeHorizontalPriceLine = (drawing: Drawing): void => {
    const rawDrawing = toRaw(drawing)
    const refEntry = horizontalPriceLines.get(rawDrawing)
    if (!refEntry) return
    try {
      refEntry.series.removePriceLine(refEntry.priceLine)
    } catch (error) {
      console.warn('Failed to remove horizontal price line', error)
    }
    horizontalPriceLines.delete(rawDrawing)
    removeHorizontalLabel(drawing)
  }

  const ensureHorizontalPriceLine = (drawing: Drawing): void => {
    if (drawing.type !== 'horizontal' || drawing.points.length === 0) return
    const price = drawing.points[0]?.price
    if (price === undefined) return

    const activeSeries = getActiveSeries()
    if (!activeSeries) return

    const rawDrawing = toRaw(drawing)
    const existing = horizontalPriceLines.get(rawDrawing)
    if (existing && existing.series !== activeSeries) {
      removeHorizontalPriceLine(rawDrawing)
    }

    const target = horizontalPriceLines.get(rawDrawing)
    const { background, text } = getLatestPriceLabelColors()

    if (target) {
      target.priceLine.applyOptions({ price, color: '#2962FF', lineStyle: 2, lineWidth: 1, axisLabelVisible: true, axisLabelColor: background, axisLabelTextColor: text, title: '' })
      updateHorizontalLabelPosition(drawing)
      return
    }

    try {
      const priceLine = activeSeries.createPriceLine({
        price,
        color: '#2962FF',
        lineStyle: 2,
        lineWidth: 1,
        axisLabelVisible: true,
        axisLabelColor: background,
        axisLabelTextColor: text,
        title: ''
      })
      horizontalPriceLines.set(rawDrawing, { series: activeSeries, priceLine })
      updateHorizontalLabelPosition(drawing)
    } catch (error) {
      console.warn('Failed to create horizontal price line', error)
    }
  }

  const syncHorizontalPriceLines = (): void => {
    const activeSeries = getActiveSeries()
    if (!activeSeries) return

    drawings.forEach(d => {
      if (d.type !== 'horizontal') return
      ensureHorizontalPriceLine(d)
      updateHorizontalLabelPosition(d)
    })
    const labelKeys = Array.from(horizontalPriceLabels.keys())
    labelKeys.forEach(key => {
      const stillExists = drawings.some(d => toRaw(d) === key)
      if (!stillExists) {
        removeHorizontalPriceLine(key)
      }
    })
  }

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
  const activeSeries = getActiveSeries()
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

    syncHorizontalPriceLines()

    const drawList = [...drawings]
    if (currentDrawing.value) {
      drawList.push(currentDrawing.value)
    }

    drawList.forEach(d => {
      const isCurrent = currentDrawing.value && d === currentDrawing.value
      const basePoints = d.points
      let pointsForRendering = basePoints

      if (
        isCurrent &&
        previewPoint.value &&
        (d.type === 'line' || d.type === 'ray') &&
        basePoints.length >= 1
      ) {
        pointsForRendering = [basePoints[0], previewPoint.value]
      }

      ctx.beginPath()
      ctx.strokeStyle = '#2962FF'
      ctx.lineWidth = 2

      if (d.type === 'line' || d.type === 'ray') {
        if (pointsForRendering.length >= 2) {
          const p1 = logicalToPoint(pointsForRendering[0])
          const p2 = logicalToPoint(pointsForRendering[1])
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
        const p1 = logicalToPoint(pointsForRendering[0])
        if (p1) {
          ctx.moveTo(0, p1.y)
          ctx.lineTo(width, p1.y)
        }
      }

      ctx.stroke()

      const shouldRenderControlPoints =
        d.type !== 'delete' &&
        (currentTool.value === 'delete' || currentTool.value === d.type || isCurrent)

      if (shouldRenderControlPoints) {
        const controlPoints = basePoints
        controlPoints.forEach(point => {
          const pt = logicalToPoint(point)
          if (pt) {
            ctx.beginPath()
            ctx.arc(pt.x, pt.y, 8, 0, 2 * Math.PI)
            ctx.fillStyle = '#2962FF'
            ctx.fill()
            ctx.strokeStyle = '#ffffff'
            ctx.lineWidth = 2
            ctx.stroke()
          }
        })
      }
    })
    
    // Restore context state (remove clipping)
    ctx.restore()
  }

  const removeDrawing = (drawing: Drawing): void => {
    removeHorizontalPriceLine(drawing)
    const index = drawings.indexOf(drawing)
    if (index !== -1) {
      drawings.splice(index, 1)
    }
    renderDrawings()
  }

  const handleDrawingClick = (param: any): void => {
    if (suppressNextClick) {
      suppressNextClick = false
      return
    }

    if (isDragging.value) {
      return
    }
    
    // Check for control point dragging BEFORE checking cursor mode
    if (param && param.point && chart.value) {
      const screenPoint: ScreenPoint = { x: param.point.x, y: param.point.y }
      const activated = activateControlPointAt(screenPoint, {
        originalEvent: param.originalEvent,
        startEdit: currentTool.value !== 'delete'
      })
      if (activated) {
        if (currentTool.value === 'delete' && activated.drawing) {
          removeDrawing(activated.drawing)
        }
        return
      }
    }
    
    // Only handle clicks when in drawing mode (not cursor mode)
    if (currentTool.value === 'cursor') return
    if (!param || !param.point || !chart.value) return

    const screenPoint: ScreenPoint = { x: param.point.x, y: param.point.y }

    if (currentTool.value === 'delete') {
      const activated = activateControlPointAt(screenPoint, { originalEvent: param.originalEvent, startEdit: false })
      if (activated) {
        removeDrawing(activated.drawing)
        return
      }
      const target = findDrawingNearPoint(screenPoint)
      if (target) {
        removeDrawing(target)
      }
      return
    }

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

    // 正常画线逻辑
    if (!currentDrawing.value) {
      currentDrawing.value = { type: currentTool.value, points: [logical] }
      previewPoint.value = logical
      if (currentTool.value === 'horizontal') {
        const finalized = currentDrawing.value
        drawings.push(finalized)
        ensureHorizontalPriceLine(finalized)
        updateHorizontalLabelPosition(finalized)
        currentDrawing.value = null
        previewPoint.value = null
      }
    } else {
      currentDrawing.value.points.push(logical)
      drawings.push(currentDrawing.value)
      currentDrawing.value = null
      previewPoint.value = null
    }

    renderDrawings()
  }

  const handleChartPointerDown = (event: PointerEvent): void => {
    if (!chart.value) return
    if (isDragging.value) return
    if (event.isPrimary === false) return
    if (event.button !== undefined && event.button !== 0 && event.button !== -1) return

    const container = chart.value.chartElement()
    if (!container) return

    const rect = container.getBoundingClientRect()
    const screenPoint: ScreenPoint = {
      x: event.clientX - rect.left,
      y: event.clientY - rect.top
    }

    const activated = activateControlPointAt(screenPoint, {
      originalEvent: event,
      suppressUpcomingClick: true,
      startEdit: currentTool.value !== 'delete'
    })
    if (activated) {
      if (currentTool.value === 'delete') {
        removeDrawing(activated.drawing)
      }
      return
    }
  }

  const handleChartPointerMove = (event: PointerEvent): void => {
    if (!chart.value) return
    if (isDragging.value) return
    if (!currentDrawing.value) return
    if (event.isPrimary === false) return

    updatePreviewFromPointer(event.clientX, event.clientY)
  }

  const handleChartPointerLeave = (): void => {
    if (previewPoint.value !== null) {
      previewPoint.value = null
      renderDrawings()
    }
  }

  const handleCanvasMouseDown = (): void => {
    // Canvas is always pointer-events: none, interactions handled by chart subscribeClick
  }

  const clearDrawings = (): void => {
    horizontalPriceLines.forEach(({ series, priceLine }) => {
      try {
        series.removePriceLine(priceLine)
      } catch (error) {
        console.warn('Failed to remove price line during clear', error)
      }
    })
    horizontalPriceLines.clear()
    horizontalPriceLabels.forEach(label => {
      label.parentElement?.removeChild(label)
    })
    horizontalPriceLabels.clear()
    drawings.splice(0, drawings.length)
    currentDrawing.value = null
    previewPoint.value = null
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

  // 全局鼠标事件处理器(在外部定义一次,避免闭包问题)
  const handleGlobalMouseUp = () => {
    if (isDragging.value) {
      isDragging.value = false
      editingDrawing.value = null
      editingPointIndex.value = -1
      
      // 重新启用图表交互
      if (chart.value) {
        chart.value.applyOptions({
          handleScroll: true,
          handleScale: true
        })
      }
    }
  }
  
  const getLogicalFromClient = (clientX: number, clientY: number): LogicalPoint | null => {
    if (!chart.value) return null
    const chartElement = chart.value.chartElement()
    if (!chartElement) return null
    const rect = chartElement.getBoundingClientRect()
    const x = clientX - rect.left
    const y = clientY - rect.top

    const timeScale = chart.value.timeScale()
    const activeSeries = isTimelineMode.value ? lineSeries.value : candleSeries.value
    if (!activeSeries) return null

    const time = timeScale.coordinateToTime(x)
    const price = activeSeries.coordinateToPrice(y)

    if (time === null || price === null) return null
    const timeValue = typeof time === 'number' ? time : Number(time)
    if (Number.isNaN(timeValue)) return null
    return { time: timeValue, price: price as number }
  }

  const updateDraggedControlPointPosition = (clientX: number, clientY: number) => {
    if (!isDragging.value) return
    if (!chart.value || !canvasRef.value) {
      return
    }
    
    const logical = getLogicalFromClient(clientX, clientY)

    if (logical && editingDrawing.value && editingPointIndex.value !== -1) {
  editingDrawing.value.points[editingPointIndex.value] = logical

      if (editingDrawing.value.type === 'horizontal') {
        ensureHorizontalPriceLine(editingDrawing.value)
        updateHorizontalLabelPosition(editingDrawing.value)
      }

      renderDrawings()
    }
  }

  const updatePreviewFromPointer = (clientX: number, clientY: number) => {
    if (!currentDrawing.value) return
    if (isDragging.value) return
    if (currentDrawing.value.type !== 'line' && currentDrawing.value.type !== 'ray') return

    const logical = getLogicalFromClient(clientX, clientY)
    if (logical) {
      previewPoint.value = logical
      renderDrawings()
    } else if (previewPoint.value !== null) {
      previewPoint.value = null
      renderDrawings()
    }
  }

  const handleGlobalMouseMove = (e: MouseEvent) => {
    updateDraggedControlPointPosition(e.clientX, e.clientY)
  }

  const handleGlobalPointerMove = (e: PointerEvent) => {
    updateDraggedControlPointPosition(e.clientX, e.clientY)
  }

  const handleGlobalPointerUp = () => {
    handleGlobalMouseUp()
  }

  const setupChartListener = (): void => {
    if (chart.value) {
      chart.value.subscribeClick(handleDrawingClick)
      
      // 获取图表容器元素
      const chartContainer = chart.value.chartElement()
      
      // 移除旧的事件监听器(如果存在)
      window.removeEventListener('mouseup', handleGlobalMouseUp)
      window.removeEventListener('mousemove', handleGlobalMouseMove)
      window.removeEventListener('pointerup', handleGlobalPointerUp)
      window.removeEventListener('pointercancel', handleGlobalPointerUp)
      window.removeEventListener('pointermove', handleGlobalPointerMove)
      if (chartContainer) {
        chartContainer.removeEventListener('pointerdown', handleChartPointerDown, true)
        chartContainer.removeEventListener('pointermove', handleChartPointerMove)
        chartContainer.removeEventListener('pointerleave', handleChartPointerLeave)
      }
      
      // 添加全局鼠标事件监听器
      window.addEventListener('mouseup', handleGlobalMouseUp)
      window.addEventListener('mousemove', handleGlobalMouseMove)
      window.addEventListener('pointerup', handleGlobalPointerUp)
      window.addEventListener('pointercancel', handleGlobalPointerUp)
      window.addEventListener('pointermove', handleGlobalPointerMove)
      
      // 在图表容器上监听 pointerdown,提前捕获控制点拖拽
      if (chartContainer) {
        chartContainer.addEventListener('pointerdown', handleChartPointerDown, true)
        chartContainer.addEventListener('pointermove', handleChartPointerMove)
        chartContainer.addEventListener('pointerleave', handleChartPointerLeave)
      }
      
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

  watch(currentTool, () => {
    if (currentDrawing.value) {
      currentDrawing.value = null
    }
    previewPoint.value = null
    renderDrawings()
  })

  onUnmounted(() => {
    stopWatch()
    stopContinuousRendering()
    // 清理全局事件监听器
    window.removeEventListener('mouseup', handleGlobalMouseUp)
    window.removeEventListener('mousemove', handleGlobalMouseMove)
    window.removeEventListener('pointerup', handleGlobalPointerUp)
    window.removeEventListener('pointercancel', handleGlobalPointerUp)
    window.removeEventListener('pointermove', handleGlobalPointerMove)
    const container = chart.value?.chartElement()
    if (container) {
      container.removeEventListener('pointerdown', handleChartPointerDown, true)
      container.removeEventListener('pointermove', handleChartPointerMove)
      container.removeEventListener('pointerleave', handleChartPointerLeave)
    }
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
