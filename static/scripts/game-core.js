class Game {
  constructor() {
    this.canvas = document.getElementById("game-canvas")
    this.ctx = this.canvas.getContext("2d")
    this.gameState = null
    this.playerId = null
    this.ws = null
    this.camera = { x: 0, y: 0 }
    this.mouse = { x: 0, y: 0 }
    this.isAccelerating = false
    this.lastUpdateTime = 0
    this.frameCount = 0
    this.lastFpsTime = 0
    this.fps = 0
    this.spectatorMode = false
    this.spectatorTarget = null
    this.lastDirection = null
    this.directionSendTime = 0
    this.pingStartTime = 0
    this.ping = 0
    this.selectedColor = "#ff6b6b"
    this.connectionLost = false
    this.reconnectAttempts = 0
    this.maxReconnectAttempts = 5
    this.connectionCheckInterval = null
    this.lastRenderTime = 0
    this.targetFPS = 60
    this.frameInterval = 1000 / this.targetFPS
    this.lastLeaderboardUpdate = 0
    this.leaderboardUpdateInterval = 500

    this.renderCache = {
      visibleEntities: { food: [], powerFood: [], players: [], bots: [] },
      lastCameraUpdate: 0,
      gridPattern: null,
      backgroundPattern: null,
      viewBounds: { left: 0, right: 0, top: 0, bottom: 0 },
    }

    this.spawnCache = new Map()

    this.performanceSettings = {
      maxFoodRender: 150,
      maxPowerRender: 20,
      skipFrames: 0,
      lowDetailMode: false,
      cullingMargin: 50,
    }

    this.objectPools = {
      gradients: new Map(),
      patterns: new Map(),
    }

    this.animationCache = {
      time: 0,
      sin: new Float32Array(360),
      cos: new Float32Array(360),
    }

    this.initAnimationCache()
    this.setupCanvas()
    this.setupEventListeners()
    this.connectWebSocket()
    this.startRenderLoop()
    this.startConnectionMonitor()
    this.createBackgroundPattern()

    document.body.classList.add("menu-active")
  }

  initAnimationCache() {
    for (let i = 0; i < 360; i++) {
      const rad = (i * Math.PI) / 180
      this.animationCache.sin[i] = Math.sin(rad)
      this.animationCache.cos[i] = Math.cos(rad)
    }
  }

  setupCanvas() {
    const updateCanvasSize = () => {
      const width = window.innerWidth
      const height = window.innerHeight

      if (this.canvas.width !== width || this.canvas.height !== height) {
        this.canvas.width = width
        this.canvas.height = height
        this.createBackgroundPattern()
        this.objectPools.gradients.clear()
      }
    }

    updateCanvasSize()
    window.addEventListener("resize", updateCanvasSize, { passive: true })
  }

  setupEventListeners() {
    const mouseMoveHandler = (e) => {
      this.mouse.x = e.clientX
      this.mouse.y = e.clientY
    }

    const keyDownHandler = (e) => {
      if (e.code === "Space") {
        e.preventDefault()
        this.isAccelerating = true
      }
    }

    const keyUpHandler = (e) => {
      if (e.code === "Space") {
        e.preventDefault()
        this.isAccelerating = false
      }
    }

    document.addEventListener("mousemove", mouseMoveHandler, { passive: true })
    document.addEventListener("keydown", keyDownHandler)
    document.addEventListener("keyup", keyUpHandler)

    const colorOptions = document.querySelectorAll(".color-option")
    colorOptions.forEach((option) => {
      option.addEventListener(
        "click",
        (e) => {
          colorOptions.forEach((opt) => opt.classList.remove("selected"))
          e.target.classList.add("selected")
          this.selectedColor = e.target.dataset.color
        },
        { passive: true },
      )
    })

    document.getElementById("join-button").addEventListener("click", () => this.joinGame())
    document.getElementById("restart-button").addEventListener("click", () => this.resetGame())
    document.getElementById("spectate-button").addEventListener("click", () => {
      this.spectatorMode = true
      document.getElementById("death-screen").style.display = "none"
      document.getElementById("spectator-mode").style.display = "block"
    })
  }

  joinGame() {
    const nameInput = document.getElementById("nickname-input")
    const name = nameInput.value.trim()

    if (!name) {
      alert("Please enter a nickname")
      return
    }

    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      alert("Connection is not ready yet")
      return
    }

    this.ws.send(
      JSON.stringify({
        type: "join",
        name,
        color: this.selectedColor,
      }),
    )

    document.getElementById("login-screen").classList.remove("active")
    document.getElementById("game-screen").classList.add("active")
    document.body.classList.remove("menu-active")
  }

  resetGame() {
    const nameInput = document.getElementById("nickname-input")
    const name = nameInput.value.trim()

    if (!name) {
      this.spectatorMode = false
      this.spectatorTarget = null
      document.getElementById("death-screen").style.display = "none"
      document.getElementById("spectator-mode").style.display = "none"
      document.getElementById("game-screen").classList.remove("active")
      document.getElementById("login-screen").classList.add("active")
      document.body.classList.add("menu-active")
      return
    }

    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      alert("Connection is not ready yet")
      return
    }

    this.spectatorMode = false
    this.spectatorTarget = null
    document.getElementById("death-screen").style.display = "none"
    document.getElementById("spectator-mode").style.display = "none"

    this.ws.send(
      JSON.stringify({
        type: "join",
        name,
        color: this.selectedColor,
      }),
    )

    document.body.classList.remove("menu-active")
  }

  updateMovement() {
    if (!this.gameState || !this.playerId) return

    const player = this.gameState.players[this.playerId]
    if (!player?.alive) {
      if (player && !this.spectatorMode && document.getElementById("death-screen").style.display !== "flex") {
        this.showDeathScreen(player)
      }
      return
    }

    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      return
    }

    const centerX = this.canvas.width / 2
    const centerY = this.canvas.height / 2

    const dx = this.mouse.x - centerX
    const dy = this.mouse.y - centerY
    const direction = Math.atan2(dy, dx)

    const currentTime = Date.now()
    if (currentTime - this.directionSendTime > 100) {
      this.ws.send(
        JSON.stringify({
          type: "move",
          player_id: this.playerId,
          direction,
          accelerating: this.isAccelerating,
        }),
      )
      this.directionSendTime = currentTime
    }
  }

  showDeathScreen(player) {
    const deathScreen = document.getElementById("death-screen")
    document.getElementById("final-score").textContent = player.score
    document.getElementById("final-length").textContent = player.length
    deathScreen.style.display = "flex"
  }

  updateCamera() {
    if (!this.gameState) return

    let targetX = this.canvas.width / 2
    let targetY = this.canvas.height / 2

    if (this.spectatorMode) {
      let targetEntity = this.spectatorTarget ? this.findEntityByName(this.spectatorTarget) : null

      if (!targetEntity || !targetEntity.alive) {
        this.switchToNextPlayer()
        targetEntity = this.spectatorTarget ? this.findEntityByName(this.spectatorTarget) : null
      }

      if (!targetEntity && this.gameState.leaderboard?.length > 0) {
        targetEntity = this.findEntityByName(this.gameState.leaderboard[0].name)
        if (targetEntity) {
          this.spectatorTarget = targetEntity.name
        }
      }

      if (targetEntity?.snake?.length > 0) {
        targetX = targetEntity.snake[0].x
        targetY = targetEntity.snake[0].y
      }
    } else {
      const player = this.playerId ? this.gameState.players[this.playerId] : null
      if (player?.alive && player?.snake?.length > 0) {
        targetX = player.snake[0].x
        targetY = player.snake[0].y
      } else if (this.gameState.leaderboard?.length > 0) {
        const entity = this.findEntityByName(this.gameState.leaderboard[0].name)
        if (entity?.snake?.length > 0) {
          targetX = entity.snake[0].x
          targetY = entity.snake[0].y
        }
      }
    }

    const smoothing = 0.08
    this.camera.x += (targetX - this.canvas.width / 2 - this.camera.x) * smoothing
    this.camera.y += (targetY - this.canvas.height / 2 - this.camera.y) * smoothing
  }

  findEntityByName(name) {
    for (const player of Object.values(this.gameState.players)) {
      if (player.name === name) return player
    }
    for (const bot of Object.values(this.gameState.bots)) {
      if (bot.name === name) return bot
    }
    return null
  }

  switchToNextPlayer() {
    if (!this.gameState.leaderboard || this.gameState.leaderboard.length === 0) {
      this.spectatorTarget = null
      return
    }

    const aliveEntities = this.gameState.leaderboard.filter((entry) => {
      const entity = this.findEntityByName(entry.name)
      return entity && entity.alive
    })

    if (aliveEntities.length === 0) {
      this.spectatorTarget = null
      return
    }

    if (!this.spectatorTarget) {
      this.spectatorTarget = aliveEntities[0].name
      return
    }

    const currentIndex = aliveEntities.findIndex((entry) => entry.name === this.spectatorTarget)
    if (currentIndex === -1) {
      this.spectatorTarget = aliveEntities[0].name
    } else {
      const nextIndex = (currentIndex + 1) % aliveEntities.length
      this.spectatorTarget = aliveEntities[nextIndex].name
    }
  }

  startRenderLoop() {
    const gameLoop = (currentTime) => {
      this.updateMovement()
      this.updateCamera()
      this.render(currentTime)
      requestAnimationFrame(gameLoop)
    }
    requestAnimationFrame(gameLoop)
  }
}

document.addEventListener('DOMContentLoaded', () => {
  new Game()
})
