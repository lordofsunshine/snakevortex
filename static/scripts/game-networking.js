Game.prototype.connectWebSocket = function () {
  if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
    return
  }

  if (this.connectionLost) {
    this.showConnectionLost()
  }

  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:"
  const wsUrl = `${protocol}//${window.location.host}/ws`
  this.ws = new WebSocket(wsUrl)

  this.ws.onopen = () => {
    this.hideConnectionLost()
    this.reconnectAttempts = 0
    this.startPing()
  }

  this.ws.onmessage = (event) => {
    let data
    try {
      data = JSON.parse(event.data)
    } catch (_error) {
      return
    }

    if (!data || typeof data !== "object") {
      return
    }

    this.handleMessage(data)
  }

  this.ws.onerror = () => {
    this.connectionLost = true
  }

  this.ws.onclose = () => {
    this.connectionLost = true
    this.showConnectionLost()

    if (this.pingInterval) {
      clearInterval(this.pingInterval)
      this.pingInterval = null
    }

    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts += 1
      setTimeout(() => this.connectWebSocket(), 2000)
    }
  }
}

Game.prototype.startConnectionMonitor = function () {
  if (this.connectionCheckInterval) {
    clearInterval(this.connectionCheckInterval)
  }

  this.connectionCheckInterval = setInterval(() => {
    if (!this.ws || this.ws.readyState === WebSocket.CLOSED) {
      this.connectionLost = true
      this.connectWebSocket()
    }
  }, 10000)
}

Game.prototype.showConnectionLost = function () {
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
  if (this.pingInterval) {
    clearInterval(this.pingInterval)
  }

  this.pingInterval = setInterval(() => {
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
