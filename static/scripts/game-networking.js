Game.prototype.connectWebSocket = function () {
  if (this.connectionLost) {
    this.showConnectionLost()
  }

  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:"
  const wsUrl = `${protocol}//${window.location.host}/ws`
  this.ws = new WebSocket(wsUrl)

  this.ws.onopen = () => {
    console.log("WebSocket connected")
    this.hideConnectionLost()
    this.reconnectAttempts = 0
    this.startPing()
  }

  this.ws.onmessage = (event) => {
    const data = JSON.parse(event.data)
    this.handleMessage(data)
  }

  this.ws.onerror = (error) => {
    console.error("WebSocket error:", error)
  }

  this.ws.onclose = () => {
    console.log("WebSocket disconnected")
    this.connectionLost = true
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++
      setTimeout(() => this.connectWebSocket(), 2000)
    }
  }
}

Game.prototype.startConnectionMonitor = function () {
  this.connectionCheckInterval = setInterval(() => {
    if (this.ws?.readyState !== WebSocket.OPEN) {
      this.connectionLost = true
      this.connectWebSocket()
    }
  }, 10000)
}

Game.prototype.showConnectionLost = () => {
  document.getElementById("connection-lost").style.display = "flex"
}

Game.prototype.hideConnectionLost = function () {
  document.getElementById("connection-lost").style.display = "none"
  this.connectionLost = false
}

Game.prototype.handleMessage = function (data) {
  switch (data.type) {
    case "player_id":
      this.playerId = data.player_id
      if (data.assigned_name) {
        const nameInput = document.getElementById("nickname-input")
        if (nameInput.value !== data.assigned_name) {
          nameInput.value = data.assigned_name
          console.log(`Name changed to: ${data.assigned_name}`)
        }
      }
      break
    case "game_state":
      this.gameState = data
      this.updateUI()
      this.updateVisibleEntities()
      break
    case "error":
      alert(data.message)
      break
    case "pong":
      this.ping = Date.now() - this.pingStartTime
      break
  }
}

Game.prototype.startPing = function () {
  setInterval(() => {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.pingStartTime = Date.now()
      this.ws.send(
        JSON.stringify({
          type: "ping",
          player_id: this.playerId,
          ping: this.ping,
        }),
      )
    }
  }, 1000)
}
