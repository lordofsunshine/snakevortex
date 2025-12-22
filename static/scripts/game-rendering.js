Game.prototype.render = function (currentTime) {
  if (currentTime - this.lastRenderTime < this.frameInterval) {
    return
  }
  
  this.lastRenderTime = currentTime
  
  this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height)
  
  if (!this.gameState) return

  this.animationCache.time = currentTime
  
  this.ctx.save()
  this.ctx.translate(-this.camera.x, -this.camera.y)

  this.renderGridOptimized()
  this.renderMapBorders()
  this.renderFoodOptimized()
  this.renderPowerFoodOptimized()
  this.renderSnakes()

  this.ctx.restore()

  this.renderUI()
  this.updateFPS()
}

Game.prototype.createBackgroundPattern = function () {
  if (this.renderCache.backgroundPattern) return

  const patternCanvas = document.createElement("canvas")
  patternCanvas.width = 50
  patternCanvas.height = 50
  const patternCtx = patternCanvas.getContext("2d")

  patternCtx.strokeStyle = "rgba(255, 255, 255, 0.03)"
  patternCtx.lineWidth = 1
  patternCtx.beginPath()
  patternCtx.moveTo(0, 25)
  patternCtx.lineTo(50, 25)
  patternCtx.moveTo(25, 0)
  patternCtx.lineTo(25, 50)
  patternCtx.stroke()

  this.renderCache.backgroundPattern = this.ctx.createPattern(patternCanvas, "repeat")
}

Game.prototype.updateVisibleEntities = function () {
  if (!this.gameState) return

  const margin = this.performanceSettings.cullingMargin
  const bounds = this.renderCache.viewBounds
  bounds.left = this.camera.x - margin
  bounds.right = this.camera.x + this.canvas.width + margin
  bounds.top = this.camera.y - margin
  bounds.bottom = this.camera.y + this.canvas.height + margin
  const activeIds = new Set()

  const isVisible = (obj) =>
    obj.x >= bounds.left &&
    obj.x <= bounds.right &&
    obj.y >= bounds.top &&
    obj.y <= bounds.bottom &&
    (obj.scale || 1.0) > 0

  this.renderCache.visibleEntities.food = this.gameState.food
    .filter(isVisible)
    .slice(0, this.performanceSettings.maxFoodRender)

  this.renderCache.visibleEntities.powerFood = this.gameState.power_food
    .filter(isVisible)
    .slice(0, this.performanceSettings.maxPowerRender)

  const snakeMargin = margin + 160
  const snakeBounds = {
    left: this.camera.x - snakeMargin,
    right: this.camera.x + this.canvas.width + snakeMargin,
    top: this.camera.y - snakeMargin,
    bottom: this.camera.y + this.canvas.height + snakeMargin,
  }

  const isPointInSnakeBounds = (p) =>
    p.x >= snakeBounds.left && p.x <= snakeBounds.right && p.y >= snakeBounds.top && p.y <= snakeBounds.bottom

  const isSnakeVisible = (snake) => {
    if (!snake?.length) return false

    const len = snake.length
    if (len <= 3) {
      for (let i = 0; i < len; i++) {
        if (isPointInSnakeBounds(snake[i])) return true
      }
      return false
    }

    const samples = Math.min(12, len)
    const step = (len - 1) / (samples - 1)
    for (let i = 0; i < samples; i++) {
      const idx = Math.floor(i * step)
      if (isPointInSnakeBounds(snake[idx])) return true
    }
    return false
  }

  const visiblePlayers = []
  if (this.gameState.players) {
    for (const [playerId, player] of Object.entries(this.gameState.players)) {
      if (!player?.alive || !player.snake?.length) continue
      const entityId = player.id || playerId
      activeIds.add(entityId)
      if (isSnakeVisible(player.snake)) visiblePlayers.push([playerId, player])
    }
  }
  this.renderCache.visibleEntities.players = visiblePlayers

  const visibleBots = []
  if (this.gameState.bots) {
    for (const bot of Object.values(this.gameState.bots)) {
      if (!bot?.alive || !bot.snake?.length) continue
      if (bot.id) activeIds.add(bot.id)
      if (isSnakeVisible(bot.snake)) visibleBots.push(bot)
    }
  }
  this.renderCache.visibleEntities.bots = visibleBots

  for (const key of this.spawnCache.keys()) {
    if (!activeIds.has(key)) {
      this.spawnCache.delete(key)
    }
  }

  let totalSegments = 0
  for (let i = 0; i < visiblePlayers.length; i++) {
    totalSegments += visiblePlayers[i][1].snake.length
  }
  for (let i = 0; i < visibleBots.length; i++) {
    totalSegments += visibleBots[i].snake.length
  }

  const totalSnakes = visiblePlayers.length + visibleBots.length
  const heavy = totalSegments > 900 || totalSnakes > 12
  const light = totalSegments < 650 && totalSnakes < 9
  if (heavy) {
    this.performanceSettings.lowDetailMode = true
  } else if (light) {
    this.performanceSettings.lowDetailMode = false
  }
}

Game.prototype.renderGridOptimized = function () {
  if (!this.renderCache.backgroundPattern) return

  this.ctx.save()
  this.ctx.fillStyle = this.renderCache.backgroundPattern
  this.ctx.fillRect(this.camera.x, this.camera.y, this.canvas.width, this.canvas.height)
  this.ctx.restore()
}

Game.prototype.renderMapBorders = function () {
  const borderWidth = 5

  const getTargetBounds = () => {
    const arena = this.gameState?.arena
    if (arena && typeof arena.min_x === "number" && typeof arena.min_y === "number" && typeof arena.max_x === "number" && typeof arena.max_y === "number") {
      return { minX: arena.min_x, minY: arena.min_y, maxX: arena.max_x, maxY: arena.max_y, phase: arena.phase || "static" }
    }
    return { minX: 0, minY: 0, maxX: 2000, maxY: 2000, phase: "static" }
  }

  if (!this.arenaRender) {
    const t = getTargetBounds()
    this.arenaRender = { minX: t.minX, minY: t.minY, maxX: t.maxX, maxY: t.maxY, phase: t.phase, lastTime: 0 }
  }

  const target = getTargetBounds()
  const now = this.animationCache.time
  const dt = this.arenaRender.lastTime ? Math.min(50, now - this.arenaRender.lastTime) : 16
  this.arenaRender.lastTime = now

  const smoothing = target.phase === "shrinking" ? 0.18 : 0.12
  const f = 1 - Math.pow(1 - smoothing, dt / 16)

  this.arenaRender.minX += (target.minX - this.arenaRender.minX) * f
  this.arenaRender.minY += (target.minY - this.arenaRender.minY) * f
  this.arenaRender.maxX += (target.maxX - this.arenaRender.maxX) * f
  this.arenaRender.maxY += (target.maxY - this.arenaRender.maxY) * f
  this.arenaRender.phase = target.phase

  const worldMinX = 0
  const worldMinY = 0
  const worldMaxX = 2000
  const worldMaxY = 2000

  const minX = this.arenaRender.minX
  const minY = this.arenaRender.minY
  const maxX = this.arenaRender.maxX
  const maxY = this.arenaRender.maxY
  const w = maxX - minX
  const h = maxY - minY

  this.ctx.save()

  const shrinking = this.arenaRender.phase === "shrinking"
  const borderColor = shrinking ? "rgba(255, 120, 80, 1)" : "rgba(78, 205, 196, 1)"
  const glowA = shrinking ? 0.55 : 0.35
  const glowB = shrinking ? 0.18 : 0.2

  const overlayAlpha = shrinking ? 0.28 : 0.18
  this.ctx.fillStyle = `rgba(0, 0, 0, ${overlayAlpha})`
  this.ctx.fillRect(worldMinX - borderWidth, worldMinY - borderWidth, worldMaxX + 2 * borderWidth, minY - worldMinY + borderWidth)
  this.ctx.fillRect(worldMinX - borderWidth, maxY, worldMaxX + 2 * borderWidth, worldMaxY - maxY + borderWidth)
  this.ctx.fillRect(worldMinX - borderWidth, minY, minX - worldMinX + borderWidth, h)
  this.ctx.fillRect(maxX, minY, worldMaxX - maxX + borderWidth, h)

  const gradient = this.ctx.createLinearGradient(minX, minY, minX + borderWidth, minY)
  const glowColorA = shrinking ? `rgba(255, 120, 80, ${glowA})` : `rgba(78, 205, 196, ${glowA})`
  const glowColorB = shrinking ? `rgba(255, 120, 80, ${glowB})` : `rgba(78, 205, 196, ${glowB})`
  const glowColorC = shrinking ? "rgba(255, 120, 80, 0)" : "rgba(78, 205, 196, 0)"
  gradient.addColorStop(0, glowColorA)
  gradient.addColorStop(0.6, glowColorB)
  gradient.addColorStop(1, glowColorC)

  this.ctx.fillStyle = gradient
  this.ctx.fillRect(minX - borderWidth, minY - borderWidth, borderWidth, h + 2 * borderWidth)
  this.ctx.fillRect(maxX, minY - borderWidth, borderWidth, h + 2 * borderWidth)
  this.ctx.fillRect(minX - borderWidth, minY - borderWidth, w + 2 * borderWidth, borderWidth)
  this.ctx.fillRect(minX - borderWidth, maxY, w + 2 * borderWidth, borderWidth)

  this.ctx.strokeStyle = borderColor
  this.ctx.lineWidth = 2
  this.ctx.strokeRect(minX, minY, w, h)

  this.ctx.restore()
}

Game.prototype.renderFoodOptimized = function () {
  const food = this.renderCache.visibleEntities.food
  if (!food.length) return

  this.ctx.save()

  const limit = this.performanceSettings.lowDetailMode ? Math.min(food.length, 110) : food.length
  for (let i = 0; i < limit; i++) {
    const item = food[i]
    const scale = item.scale || 1.0

    if (scale > 0) {
      this.ctx.fillStyle = item.color
      this.ctx.globalAlpha = Math.min(1.0, scale)
      this.ctx.beginPath()
      this.ctx.arc(item.x, item.y, item.size * scale, 0, Math.PI * 2)
      this.ctx.fill()
    }
  }

  this.ctx.restore()
}

Game.prototype.renderPowerFoodOptimized = function () {
  const powerFood = this.renderCache.visibleEntities.powerFood
  if (!powerFood.length) return

  this.ctx.save()
  const time = this.animationCache.time

  const limit = this.performanceSettings.lowDetailMode ? Math.min(powerFood.length, 14) : powerFood.length
  for (let i = 0; i < limit; i++) {
    const power = powerFood[i]
    const scale = power.scale || 1.0

    if (scale > 0) {
      const pulse = Math.sin(time * 0.005) * 0.2 + 0.8
      this.ctx.fillStyle = power.color
      this.ctx.globalAlpha = Math.min(1.0, scale) * pulse
      this.ctx.beginPath()
      this.ctx.arc(power.x, power.y, power.size * scale * pulse, 0, Math.PI * 2)
      this.ctx.fill()
    }
  }

  this.ctx.restore()
}

Game.prototype.renderSnakes = function () {
  const renderSnake = (entity, isPlayer = false, playerId = null) => {
    const snake = entity?.snake
    if (!snake?.length) return

    let hasSpawnProtection = false
    if (isPlayer && playerId && this.gameState.players[playerId]) {
      const player = this.gameState.players[playerId]
      hasSpawnProtection = player.spawn_protection && Date.now() < player.spawn_protection
    }

    const currentTime = this.animationCache.time
    const isLocal = isPlayer && playerId === this.playerId
    const spawnProgress = this.getSpawnProgress(entity, isLocal)
    if (spawnProgress <= 0) return

    const head = snake[0]
    const neck = snake[1] || head
    const bodyWidth = Math.min(26, 8 + Math.min(snake.length, 200) * 0.09)
    const sizeScale = 0.7 + 0.3 * spawnProgress
    const maxPoints = this.performanceSettings.lowDetailMode ? 24 : 48
    const points = this.getSnakeRenderPoints(snake, maxPoints)

    this.ctx.save()

    let alpha = spawnProgress
    if ("ghost" in (entity.powers || {}) || hasSpawnProtection) {
      const flicker = Math.sin(currentTime * 0.01) * 0.2 + 0.6
      alpha *= flicker
    }
    this.ctx.globalAlpha = alpha

    this.drawSnakeBody(points, entity.color, bodyWidth * sizeScale, this.performanceSettings.lowDetailMode)
    this.drawSnakeHead(head, neck, entity.color, bodyWidth * sizeScale)

    this.ctx.restore()

    const headVisible = this.isInViewport(head)
    if (entity.name && headVisible && spawnProgress > 0.65) {
      this.renderPlayerName(head, entity.name, entity.color)
    }

    if (headVisible && spawnProgress > 0.35) {
      this.renderPowerEffects(head, entity.powers || {}, hasSpawnProtection, currentTime)
    }
  }

  const visiblePlayers = this.renderCache.visibleEntities.players || []
  for (let i = 0; i < visiblePlayers.length; i++) {
    const [playerId, player] = visiblePlayers[i]
    renderSnake(player, true, playerId)
  }

  const visibleBots = this.renderCache.visibleEntities.bots || []
  for (let i = 0; i < visibleBots.length; i++) {
    const bot = visibleBots[i]
    renderSnake(bot, false)
  }
}

Game.prototype.renderPlayerName = function (head, name, color) {
  if (!this.isInViewport(head)) return

  this.ctx.save()
  this.ctx.font = "bold 14px Inter, sans-serif"
  this.ctx.textAlign = "center"
  this.ctx.textBaseline = "bottom"

  const nameY = head.y - 20
  const textWidth = this.ctx.measureText(name).width

  this.ctx.fillStyle = "rgba(0, 0, 0, 0.7)"
  this.ctx.fillRect(head.x - textWidth / 2 - 4, nameY - 16, textWidth + 8, 18)

  this.ctx.strokeStyle = "rgba(0, 0, 0, 0.8)"
  this.ctx.lineWidth = 3
  this.ctx.strokeText(name, head.x, nameY)

  this.ctx.fillStyle = "#ffffff"
  this.ctx.fillText(name, head.x, nameY)

  this.ctx.restore()
}

Game.prototype.renderPowerEffects = function (head, powers, hasSpawnProtection, currentTime) {
  if (hasSpawnProtection) {
    const pulse = Math.sin(currentTime * 0.01) * 0.3 + 0.7
    const radius = 20 + Math.sin(currentTime * 0.008) * 5

    this.ctx.strokeStyle = `rgba(0, 255, 100, ${pulse})`
    this.ctx.lineWidth = 3
    this.ctx.setLineDash([8, 4])
    this.ctx.beginPath()
    this.ctx.arc(head.x, head.y, radius, 0, Math.PI * 2)
    this.ctx.stroke()
    this.ctx.setLineDash([])
  }

  if ("shield" in powers) {
    const pulse = Math.sin(currentTime * 0.004) * 0.3 + 0.7
    const radius = 18

    this.ctx.strokeStyle = `rgba(0, 150, 255, ${pulse})`
    this.ctx.lineWidth = 2
    this.ctx.beginPath()
    this.ctx.arc(head.x, head.y, radius, 0, Math.PI * 2)
    this.ctx.stroke()
  }

  if ("speed" in powers) {
    const particles = 6
    for (let i = 0; i < particles; i++) {
      const angle = (i / particles) * Math.PI * 2 + currentTime * 0.01
      const distance = 25 + Math.sin(currentTime * 0.008 + i) * 8
      const x = head.x + Math.cos(angle) * distance
      const y = head.y + Math.sin(angle) * distance

      const alpha = (Math.sin(currentTime * 0.01 + i) + 1) * 0.25
      this.ctx.fillStyle = `rgba(255, 200, 0, ${alpha})`
      this.ctx.beginPath()
      this.ctx.arc(x, y, 2, 0, Math.PI * 2)
      this.ctx.fill()
    }
  }

  if ("magnet" in powers) {
    const pulse = Math.sin(currentTime * 0.006) * 0.3 + 0.4
    this.ctx.strokeStyle = `rgba(255, 120, 0, ${pulse})`
    this.ctx.lineWidth = 2
    this.ctx.beginPath()
    this.ctx.arc(head.x, head.y, 22, 0, Math.PI * 2)
    this.ctx.stroke()
  }

  if ("double_score" in powers) {
    const sparkles = 8
    for (let i = 0; i < sparkles; i++) {
      const angle = (i / sparkles) * Math.PI * 2 + currentTime * 0.015
      const distance = 18 + Math.sin(currentTime * 0.012 + i) * 6
      const x = head.x + Math.cos(angle) * distance
      const y = head.y + Math.sin(angle) * distance

      const alpha = (Math.sin(currentTime * 0.01 + i) + 1) * 0.3
      this.ctx.fillStyle = `rgba(255, 255, 0, ${alpha})`
      this.ctx.beginPath()
      this.ctx.arc(x, y, 1.5, 0, Math.PI * 2)
      this.ctx.fill()
    }
  }
}

Game.prototype.getSpawnProgress = function (entity, isLocal) {
  if (isLocal) return 1
  const now = Date.now()
  let spawnTime = entity?.spawn_time_ms
  let duration = entity?.spawn_duration_ms || 700
  const key = entity?.id || entity?.name
  if (key != null) {
    let cached = this.spawnCache.get(key)
    if (!cached) {
      let baseStart = spawnTime != null ? spawnTime : now
      if (spawnTime != null && spawnTime <= now) {
        baseStart += Math.random() * 450
      }
      cached = { start: baseStart, duration }
      this.spawnCache.set(key, cached)
    }
    spawnTime = cached.start
    duration = cached.duration || duration
  } else if (spawnTime == null) {
    spawnTime = now
  }
  if (now < spawnTime) return 0
  if (duration <= 0) return 1
  let t = (now - spawnTime) / duration
  if (t <= 0) return 0
  if (t >= 1) return 1
  t = t * t * (3 - 2 * t)
  return t
}

Game.prototype.getSnakeRenderPoints = function (snake, maxPoints) {
  const len = snake.length
  if (len === 0) return []
  if (len === 1) return [snake[0]]

  const step = Math.max(1, Math.floor(len / maxPoints))
  const points = []
  for (let i = len - 1; i >= 0; i -= step) {
    points.push(snake[i])
  }
  if (points[points.length - 1] !== snake[0]) {
    points.push(snake[0])
  }
  return points
}

Game.prototype.drawSnakeBody = function (points, color, width, lowDetail) {
  if (points.length < 2) return

  const ctx = this.ctx
  ctx.save()
  ctx.lineCap = "round"
  ctx.lineJoin = "round"

  ctx.beginPath()
  ctx.moveTo(points[0].x, points[0].y)
  for (let i = 1; i < points.length - 2; i++) {
    const midX = (points[i].x + points[i + 1].x) * 0.5
    const midY = (points[i].y + points[i + 1].y) * 0.5
    ctx.quadraticCurveTo(points[i].x, points[i].y, midX, midY)
  }
  ctx.lineTo(points[points.length - 1].x, points[points.length - 1].y)

  ctx.strokeStyle = this.darkenColor(color, 14)
  ctx.lineWidth = width
  ctx.stroke()

  if (!lowDetail) {
    ctx.strokeStyle = this.lightenColor(color, 18)
    ctx.lineWidth = width * 0.55
    ctx.stroke()
  }

  ctx.restore()
}

Game.prototype.drawSnakeHead = function (head, neck, color, width) {
  const ctx = this.ctx
  const angle = Math.atan2(head.y - neck.y, head.x - neck.x)
  const headLength = width * 1.8
  const headWidth = width * 1.15

  ctx.save()
  ctx.translate(head.x, head.y)
  ctx.rotate(angle)

  const gradient = ctx.createRadialGradient(headLength * 0.2, -headWidth * 0.3, width * 0.2, 0, 0, headLength)
  gradient.addColorStop(0, this.lightenColor(color, 20))
  gradient.addColorStop(1, this.darkenColor(color, 12))

  ctx.fillStyle = gradient
  ctx.beginPath()
  ctx.moveTo(headLength * 0.75, 0)
  ctx.quadraticCurveTo(headLength * 0.25, headWidth * 0.9, -headLength * 0.65, 0)
  ctx.quadraticCurveTo(headLength * 0.25, -headWidth * 0.9, headLength * 0.75, 0)
  ctx.fill()

  ctx.strokeStyle = this.darkenColor(color, 25)
  ctx.lineWidth = Math.max(1, width * 0.12)
  ctx.stroke()

  const eyeX = headLength * 0.15
  const eyeY = headWidth * 0.32
  const eyeRX = Math.max(1.6, width * 0.16)
  const eyeRY = Math.max(1.2, width * 0.12)

  ctx.fillStyle = "rgba(255, 255, 255, 0.9)"
  ctx.beginPath()
  ctx.ellipse(eyeX, -eyeY, eyeRX, eyeRY, 0, 0, Math.PI * 2)
  ctx.ellipse(eyeX, eyeY, eyeRX, eyeRY, 0, 0, Math.PI * 2)
  ctx.fill()

  ctx.fillStyle = "rgba(20, 20, 20, 0.9)"
  ctx.beginPath()
  ctx.ellipse(eyeX + eyeRX * 0.35, -eyeY, eyeRX * 0.45, eyeRY * 0.45, 0, 0, Math.PI * 2)
  ctx.ellipse(eyeX + eyeRX * 0.35, eyeY, eyeRX * 0.45, eyeRY * 0.45, 0, 0, Math.PI * 2)
  ctx.fill()

  ctx.fillStyle = "rgba(40, 40, 40, 0.5)"
  ctx.beginPath()
  ctx.ellipse(headLength * 0.48, -headWidth * 0.12, eyeRX * 0.2, eyeRY * 0.2, 0, 0, Math.PI * 2)
  ctx.ellipse(headLength * 0.48, headWidth * 0.12, eyeRX * 0.2, eyeRY * 0.2, 0, 0, Math.PI * 2)
  ctx.fill()

  ctx.restore()
}

Game.prototype.isInViewport = function (obj) {
  const bounds = this.renderCache.viewBounds
  return obj.x >= bounds.left && obj.x <= bounds.right && obj.y >= bounds.top && obj.y <= bounds.bottom
}

Game.prototype.renderUI = function () {
  const spectatorMode = document.getElementById("spectator-mode")
  const targetElement = document.getElementById("spectator-target")

  if (this.spectatorMode) {
    spectatorMode.style.display = "block"
    if (this.spectatorTarget) {
      targetElement.textContent = `Watching: ${this.spectatorTarget}`
      targetElement.style.display = "block"
    } else {
      targetElement.style.display = "none"
    }
  } else {
    spectatorMode.style.display = "none"
  }
}

Game.prototype.updateFPS = function () {
  this.frameCount++
  const currentTime = Date.now()

  if (currentTime - this.lastFpsTime >= 1000) {
    this.fps = this.frameCount
    this.frameCount = 0
    this.lastFpsTime = currentTime
    if (this.fps < 45) {
      this.performanceSettings.lowDetailMode = true
    } else if (this.fps > 55) {
      this.performanceSettings.lowDetailMode = false
    }
  }
}
