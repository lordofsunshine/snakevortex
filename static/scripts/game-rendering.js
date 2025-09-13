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
}

Game.prototype.renderGridOptimized = function () {
  if (!this.renderCache.backgroundPattern) return

  this.ctx.save()
  this.ctx.fillStyle = this.renderCache.backgroundPattern
  this.ctx.fillRect(this.camera.x, this.camera.y, this.canvas.width, this.canvas.height)
  this.ctx.restore()
}

Game.prototype.renderMapBorders = function () {
  const worldWidth = 2000
  const worldHeight = 2000
  const borderWidth = 5

  this.ctx.save()

  const gradient = this.ctx.createLinearGradient(0, 0, borderWidth, 0)
  gradient.addColorStop(0, "rgba(78, 205, 196, 0.8)")
  gradient.addColorStop(0.5, "rgba(78, 205, 196, 0.6)")
  gradient.addColorStop(1, "rgba(78, 205, 196, 0.2)")

  this.ctx.fillStyle = gradient
  this.ctx.fillRect(-borderWidth, -borderWidth, borderWidth, worldHeight + 2 * borderWidth)
  this.ctx.fillRect(worldWidth, -borderWidth, borderWidth, worldHeight + 2 * borderWidth)
  this.ctx.fillRect(-borderWidth, -borderWidth, worldWidth + 2 * borderWidth, borderWidth)
  this.ctx.fillRect(-borderWidth, worldHeight, worldWidth + 2 * borderWidth, borderWidth)

  this.ctx.strokeStyle = "rgba(78, 205, 196, 1)"
  this.ctx.lineWidth = 2
  this.ctx.strokeRect(0, 0, worldWidth, worldHeight)

  this.ctx.restore()
}

Game.prototype.renderFoodOptimized = function () {
  const food = this.renderCache.visibleEntities.food
  if (!food.length) return

  this.ctx.save()

  for (let i = 0; i < food.length; i++) {
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

  for (let i = 0; i < powerFood.length; i++) {
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
  const renderSnake = (snake, color, powers = {}, name = "", isPlayer = false, playerId = null) => {
    if (!snake?.length) return

    let hasSpawnProtection = false
    if (isPlayer && playerId && this.gameState.players[playerId]) {
      const player = this.gameState.players[playerId]
      hasSpawnProtection = player.spawn_protection && Date.now() < player.spawn_protection
    }

    const segments = snake.length
    const currentTime = this.animationCache.time

    this.ctx.save()

    for (let i = segments - 1; i >= 0; i--) {
      const segment = snake[i]
      if (!this.isInViewport(segment)) continue

      const isHead = i === 0
      const segmentSize = isHead ? 12 : Math.max(6, 10 - Math.min(i * 0.03, 3))
      const opacity = Math.max(0.7, 1 - i * 0.008)

      if ("ghost" in powers || hasSpawnProtection) {
        const flicker = Math.sin(currentTime * 0.01) * 0.2 + 0.6
        this.ctx.globalAlpha = opacity * flicker
      } else {
        this.ctx.globalAlpha = opacity
      }

      this.ctx.fillStyle = isHead ? this.lightenColor(color, 30) : color
      this.ctx.beginPath()
      this.ctx.arc(segment.x, segment.y, segmentSize, 0, Math.PI * 2)
      this.ctx.fill()

      if (isHead) {
        this.ctx.fillStyle = "rgba(255, 255, 255, 0.8)"
        this.ctx.beginPath()
        this.ctx.arc(segment.x - 3, segment.y - 2, 2, 0, Math.PI * 2)
        this.ctx.fill()
        this.ctx.beginPath()
        this.ctx.arc(segment.x + 3, segment.y - 2, 2, 0, Math.PI * 2)
        this.ctx.fill()
      }
    }

    this.ctx.restore()

    if (snake.length > 0 && name) {
      this.renderPlayerName(snake[0], name, color)
    }

    this.renderPowerEffects(snake[0], powers, hasSpawnProtection, currentTime)
  }

  if (this.gameState.players) {
    Object.entries(this.gameState.players).forEach(([playerId, player]) => {
      if (player.alive && player.snake) {
        renderSnake(player.snake, player.color, player.powers, player.name, true, playerId)
      }
    })
  }

  if (this.gameState.bots) {
    Object.values(this.gameState.bots).forEach((bot) => {
      if (bot.alive && bot.snake) {
        renderSnake(bot.snake, bot.color, bot.powers, bot.name, false)
      }
    })
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
  }
}

Game.prototype.lightenColor = (color, amount) =>
  "#" +
  color
    .slice(1)
    .split("")
    .map((c, i) => {
      const hex = Number.parseInt(c + c, 16)
      return (i % 2 === 0 ? hex + amount : hex).toString(16).slice(-2)
    })
    .join("")
