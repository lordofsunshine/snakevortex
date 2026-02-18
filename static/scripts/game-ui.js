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

  for (let i = 0; i < data.length; i++) {
    const entry = data[i]
    const item = document.createElement("div")
    item.className = "leaderboard-item"

    const rank = document.createElement("span")
    rank.className = "leader-rank"
    rank.textContent = i + 1

    const name = document.createElement("span")
    name.className = "leader-name"
    name.textContent = entry.name

    const score = document.createElement("span")
    score.className = "leader-score"
    score.textContent = entry.score

    item.appendChild(rank)
    item.appendChild(name)
    item.appendChild(score)

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
  }

  leaderboard.textContent = ""
  leaderboard.appendChild(fragment)
}
