Game.prototype.updateUI = function () {
  if (!this.gameState) return

  const player = this.gameState.players[this.playerId]
  if (player) {
    document.getElementById("player-score").textContent = player.score
    document.getElementById("player-length").textContent = player.length
  }

  const currentTime = Date.now()
  if (currentTime - this.lastLeaderboardUpdate > this.leaderboardUpdateInterval) {
    this.updateLeaderboard()
    this.lastLeaderboardUpdate = currentTime
  }
}

Game.prototype.updateLeaderboard = function () {
  const leaderboard = document.getElementById("leaderboard-list")

  if (!this.gameState.leaderboard) return

  const currentData = this.gameState.leaderboard.slice(0, 10)
  const existingItems = leaderboard.children

  if (existingItems.length !== currentData.length) {
    this.rebuildLeaderboard(leaderboard, currentData)
    return
  }

  for (let i = 0; i < existingItems.length; i++) {
    const item = existingItems[i]
    const entry = currentData[i]

    const rankSpan = item.querySelector(".leader-rank")
    const nameSpan = item.querySelector(".leader-name")
    const scoreSpan = item.querySelector(".leader-score")

    if (rankSpan.textContent !== (i + 1).toString()) {
      rankSpan.textContent = i + 1
    }
    if (nameSpan.textContent !== entry.name) {
      nameSpan.textContent = entry.name
    }
    if (scoreSpan.textContent !== entry.score.toString()) {
      scoreSpan.textContent = entry.score
    }
  }
}

Game.prototype.rebuildLeaderboard = function (leaderboard, data) {
  const fragment = document.createDocumentFragment()

  data.forEach((entry, index) => {
    const item = document.createElement("div")
    item.className = "leaderboard-item"
    item.innerHTML = `
            <span class="leader-rank">${index + 1}</span>
            <span class="leader-name">${entry.name}</span>
            <span class="leader-score">${entry.score}</span>
        `

    if (this.spectatorMode) {
      item.addEventListener(
        "click",
        () => {
          this.spectatorTarget = entry.name
        },
        { passive: true },
      )
    }

    fragment.appendChild(item)
  })

  leaderboard.innerHTML = ""
  leaderboard.appendChild(fragment)
}
