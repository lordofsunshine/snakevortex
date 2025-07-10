
class Game {
    constructor() {
        this.canvas = document.getElementById('game-canvas');
        this.ctx = this.canvas.getContext('2d');
        this.gameState = null;
        this.playerId = null;
        this.ws = null;
        this.camera = { x: 0, y: 0 };
        this.mouse = { x: 0, y: 0 };
        this.isAccelerating = false;
        this.lastUpdateTime = 0;
        this.frameCount = 0;
        this.lastFpsTime = 0;
        this.fps = 0;
        this.spectatorMode = false;
        this.spectatorTarget = null;
        this.lastDirection = null;
        this.directionSendTime = 0;
        this.pingStartTime = 0;
        this.ping = 0;
        this.selectedColor = '#ff6b6b';
        this.connectionLost = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.connectionCheckInterval = null;
        this.lastRenderTime = 0;
        this.targetFPS = 60;
        this.frameInterval = 1000 / this.targetFPS;
        
        this.renderCache = {
            visibleEntities: { food: [], powerFood: [] },
            lastCameraUpdate: 0,
            gridPattern: null,
            backgroundPattern: null,
            viewBounds: { left: 0, right: 0, top: 0, bottom: 0 }
        };
        
        this.performanceSettings = {
            maxFoodRender: 150,
            maxPowerRender: 20,
            skipFrames: 0,
            lowDetailMode: false,
            cullingMargin: 50
        };

        this.objectPools = {
            gradients: new Map(),
            patterns: new Map()
        };

        this.animationCache = {
            time: 0,
            sin: new Float32Array(360),
            cos: new Float32Array(360)
        };

        this.initAnimationCache();
        this.setupCanvas();
        this.setupEventListeners();
        this.connectWebSocket();
        this.startRenderLoop();
        this.startConnectionMonitor();
        this.createBackgroundPattern();
    }

    initAnimationCache() {
        for (let i = 0; i < 360; i++) {
            const rad = (i * Math.PI) / 180;
            this.animationCache.sin[i] = Math.sin(rad);
            this.animationCache.cos[i] = Math.cos(rad);
        }
    }

    setupCanvas() {
        const updateCanvasSize = () => {
            const width = window.innerWidth;
            const height = window.innerHeight;
            
            if (this.canvas.width !== width || this.canvas.height !== height) {
                this.canvas.width = width;
                this.canvas.height = height;
                this.createBackgroundPattern();
                this.objectPools.gradients.clear();
            }
        };
        
        updateCanvasSize();
        window.addEventListener('resize', updateCanvasSize, { passive: true });
    }

    createBackgroundPattern() {
        if (this.renderCache.backgroundPattern) return;
        
        const patternCanvas = document.createElement('canvas');
        patternCanvas.width = 50;
        patternCanvas.height = 50;
        const patternCtx = patternCanvas.getContext('2d');
        
        patternCtx.strokeStyle = 'rgba(255, 255, 255, 0.03)';
        patternCtx.lineWidth = 1;
        patternCtx.beginPath();
        patternCtx.moveTo(0, 25);
        patternCtx.lineTo(50, 25);
        patternCtx.moveTo(25, 0);
        patternCtx.lineTo(25, 50);
        patternCtx.stroke();
        
        this.renderCache.backgroundPattern = this.ctx.createPattern(patternCanvas, 'repeat');
    }

    setupEventListeners() {
        const mouseMoveHandler = (e) => {
            this.mouse.x = e.clientX;
            this.mouse.y = e.clientY;
        };

        const keyDownHandler = (e) => {
            if (e.code === 'Space') {
                e.preventDefault();
                this.isAccelerating = true;
            }
        };

        const keyUpHandler = (e) => {
            if (e.code === 'Space') {
                e.preventDefault();
                this.isAccelerating = false;
            }
        };

        document.addEventListener('mousemove', mouseMoveHandler, { passive: true });
        document.addEventListener('keydown', keyDownHandler);
        document.addEventListener('keyup', keyUpHandler);

        const colorOptions = document.querySelectorAll('.color-option');
        colorOptions.forEach(option => {
            option.addEventListener('click', (e) => {
                colorOptions.forEach(opt => opt.classList.remove('selected'));
                e.target.classList.add('selected');
                this.selectedColor = e.target.dataset.color;
            }, { passive: true });
        });

        document.getElementById('join-button').addEventListener('click', () => this.joinGame());
        document.getElementById('restart-button').addEventListener('click', () => this.resetGame());
        document.getElementById('spectate-button').addEventListener('click', () => {
            this.spectatorMode = true;
            document.getElementById('death-screen').style.display = 'none';
            document.getElementById('spectator-mode').style.display = 'block';
        });
    }

    connectWebSocket() {
        if (this.connectionLost) {
            this.showConnectionLost();
        }

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;
        this.ws = new WebSocket(wsUrl);
        
        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.hideConnectionLost();
            this.reconnectAttempts = 0;
            this.startPing();
        };

        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };

        this.ws.onclose = () => {
            console.log('WebSocket disconnected');
            this.connectionLost = true;
            if (this.reconnectAttempts < this.maxReconnectAttempts) {
                this.reconnectAttempts++;
                setTimeout(() => this.connectWebSocket(), 2000);
            }
        };
    }

    startConnectionMonitor() {
        this.connectionCheckInterval = setInterval(() => {
            if (this.ws?.readyState !== WebSocket.OPEN) {
                this.connectionLost = true;
                this.connectWebSocket();
            }
        }, 10000);
    }

    showConnectionLost() {
        document.getElementById('connection-lost').style.display = 'flex';
    }

    hideConnectionLost() {
        document.getElementById('connection-lost').style.display = 'none';
        this.connectionLost = false;
    }

    handleMessage(data) {
        switch (data.type) {
            case 'player_id':
                this.playerId = data.player_id;
                if (data.assigned_name) {
                    const nameInput = document.getElementById('nickname-input');
                    if (nameInput.value !== data.assigned_name) {
                        nameInput.value = data.assigned_name;
                        console.log(`Name changed to: ${data.assigned_name}`);
                    }
                }
                break;
            case 'game_state':
                this.gameState = data;
                this.updateUI();
                this.updateVisibleEntities();
                break;
            case 'error':
                alert(data.message);
                break;
            case 'pong':
                this.ping = Date.now() - this.pingStartTime;
                break;
        }
    }

    updateVisibleEntities() {
        if (!this.gameState) return;
        
        const margin = this.performanceSettings.cullingMargin;
        const bounds = this.renderCache.viewBounds;
        bounds.left = this.camera.x - margin;
        bounds.right = this.camera.x + this.canvas.width + margin;
        bounds.top = this.camera.y - margin;
        bounds.bottom = this.camera.y + this.canvas.height + margin;
        
        const isVisible = (obj) => 
            obj.x >= bounds.left && obj.x <= bounds.right &&
            obj.y >= bounds.top && obj.y <= bounds.bottom &&
            (obj.scale || 1.0) > 0;
        
        this.renderCache.visibleEntities.food = this.gameState.food
            .filter(isVisible)
            .slice(0, this.performanceSettings.maxFoodRender);
            
        this.renderCache.visibleEntities.powerFood = this.gameState.power_food
            .filter(isVisible)
            .slice(0, this.performanceSettings.maxPowerRender);
    }

    startPing() {
        setInterval(() => {
            if (this.ws?.readyState === WebSocket.OPEN) {
                this.pingStartTime = Date.now();
                this.ws.send(JSON.stringify({
                    type: 'ping',
                    player_id: this.playerId,
                    ping: this.ping
                }));
            }
        }, 1000);
    }

    joinGame() {
        const nameInput = document.getElementById('nickname-input');
        const name = nameInput.value.trim();
        
        if (!name) {
            alert('Please enter a nickname');
            return;
        }

        this.ws.send(JSON.stringify({
            type: 'join',
            name,
            color: this.selectedColor
        }));

        document.getElementById('login-screen').classList.remove('active');
        document.getElementById('game-screen').classList.add('active');
    }

    resetGame() {
        this.spectatorMode = false;
        this.spectatorTarget = null;
        document.getElementById('death-screen').style.display = 'none';
        document.getElementById('spectator-mode').style.display = 'none';
        document.getElementById('game-screen').classList.remove('active');
        document.getElementById('login-screen').classList.add('active');
        document.getElementById('nickname-input').value = '';
    }

    updateCamera() {
        if (!this.gameState) return;

        let targetX = this.canvas.width / 2;
        let targetY = this.canvas.height / 2;

        if (this.spectatorMode) {
            let targetEntity = this.spectatorTarget ? 
                this.findEntityByName(this.spectatorTarget) : null;
            
            if (!targetEntity && this.gameState.leaderboard?.length > 0) {
                targetEntity = this.findEntityByName(this.gameState.leaderboard[0].name);
            }
            
            if (targetEntity?.snake?.length > 0) {
                targetX = targetEntity.snake[0].x;
                targetY = targetEntity.snake[0].y;
            }
        } else {
            const player = this.gameState.players[this.playerId];
            if (player?.snake?.length > 0) {
                targetX = player.snake[0].x;
                targetY = player.snake[0].y;
            }
        }

        const smoothing = 0.08;
        this.camera.x += (targetX - this.canvas.width / 2 - this.camera.x) * smoothing;
        this.camera.y += (targetY - this.canvas.height / 2 - this.camera.y) * smoothing;
    }

    findEntityByName(name) {
        for (const player of Object.values(this.gameState.players)) {
            if (player.name === name) return player;
        }
        for (const bot of Object.values(this.gameState.bots)) {
            if (bot.name === name) return bot;
        }
        return null;
    }

    updateMovement() {
        if (!this.gameState || !this.playerId) return;

        const player = this.gameState.players[this.playerId];
        if (!player?.alive) {
            if (player && !this.spectatorMode) {
                this.spectatorMode = true;
                this.showDeathScreen(player);
            }
            return;
        }

        const centerX = this.canvas.width / 2;
        const centerY = this.canvas.height / 2;
        
        const dx = this.mouse.x - centerX;
        const dy = this.mouse.y - centerY;
        const direction = Math.atan2(dy, dx);

        const currentTime = Date.now();
        if (currentTime - this.directionSendTime > 100) {
            this.ws.send(JSON.stringify({
                type: 'move',
                player_id: this.playerId,
                direction,
                accelerating: this.isAccelerating
            }));
            this.directionSendTime = currentTime;
        }
    }

    showDeathScreen(player) {
        const deathScreen = document.getElementById('death-screen');
        document.getElementById('final-score').textContent = player.score;
        document.getElementById('final-length').textContent = player.length;
        deathScreen.style.display = 'flex';
    }

    updateUI() {
        if (!this.gameState) return;

        const player = this.gameState.players[this.playerId];
        if (player) {
            document.getElementById('player-score').textContent = player.score;
            document.getElementById('player-length').textContent = player.length;
            
            const rank = this.gameState.leaderboard.findIndex(entry => entry.name === player.name) + 1;
            document.getElementById('player-rank').textContent = rank > 0 ? rank : '-';
        }

        this.updateLeaderboard();
    }

    updateLeaderboard() {
        const leaderboard = document.getElementById('leaderboard-list');
        const fragment = document.createDocumentFragment();

        if (this.gameState.leaderboard) {
            this.gameState.leaderboard.slice(0, 10).forEach((entry, index) => {
                const item = document.createElement('div');
                item.className = 'leaderboard-item';
                item.innerHTML = `
                    <span class="leader-rank">${index + 1}</span>
                    <span class="leader-name">${entry.name}</span>
                    <span class="leader-score">${entry.score}</span>
                `;
                
                if (this.spectatorMode) {
                    item.addEventListener('click', () => {
                        this.spectatorTarget = entry.name;
                    }, { passive: true });
                }
                
                fragment.appendChild(item);
            });
        }
        
        leaderboard.innerHTML = '';
        leaderboard.appendChild(fragment);
    }

    render(currentTime) {
        if (currentTime - this.lastRenderTime < this.frameInterval) {
            return;
        }
        
        this.lastRenderTime = currentTime;
        
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        
        if (!this.gameState) return;

        this.animationCache.time = currentTime;
        
        this.ctx.save();
        this.ctx.translate(-this.camera.x, -this.camera.y);

        this.renderGridOptimized();
        this.renderFoodOptimized();
        this.renderPowerFoodOptimized();
        this.renderSnakes();

        this.ctx.restore();

        this.renderUI();
        this.updateFPS();
    }

    renderGridOptimized() {
        if (!this.renderCache.backgroundPattern) return;
        
        this.ctx.save();
        this.ctx.fillStyle = this.renderCache.backgroundPattern;
        this.ctx.fillRect(this.camera.x, this.camera.y, this.canvas.width, this.canvas.height);
        this.ctx.restore();
    }

    renderFoodOptimized() {
        const food = this.renderCache.visibleEntities.food;
        if (!food.length) return;
        
        this.ctx.save();
        
        for (let i = 0; i < food.length; i++) {
            const item = food[i];
            const scale = item.scale || 1.0;
            
            if (scale > 0) {
                this.ctx.fillStyle = item.color;
                this.ctx.globalAlpha = Math.min(1.0, scale);
                this.ctx.beginPath();
                this.ctx.arc(item.x, item.y, item.size * scale, 0, Math.PI * 2);
                this.ctx.fill();
            }
        }
        
        this.ctx.restore();
    }

    renderPowerFoodOptimized() {
        const powerFood = this.renderCache.visibleEntities.powerFood;
        if (!powerFood.length) return;
        
        this.ctx.save();
        const time = this.animationCache.time;
        
        for (let i = 0; i < powerFood.length; i++) {
            const power = powerFood[i];
            const scale = power.scale || 1.0;
            
            if (scale > 0) {
                const pulse = Math.sin(time * 0.005) * 0.2 + 0.8;
                this.ctx.fillStyle = power.color;
                this.ctx.globalAlpha = Math.min(1.0, scale) * pulse;
                this.ctx.beginPath();
                this.ctx.arc(power.x, power.y, power.size * scale * pulse, 0, Math.PI * 2);
                this.ctx.fill();
            }
        }
        
        this.ctx.restore();
    }

    renderSnakes() {
        const renderSnake = (snake, color, powers = {}, name = '', isPlayer = false, playerId = null) => {
            if (!snake?.length) return;

            let hasSpawnProtection = false;
            if (isPlayer && playerId && this.gameState.players[playerId]) {
                const player = this.gameState.players[playerId];
                hasSpawnProtection = player.spawn_protection && Date.now() < player.spawn_protection;
            }

            const segments = snake.length;
            const currentTime = this.animationCache.time;
            
            this.ctx.save();
            
            for (let i = segments - 1; i >= 0; i--) {
                const segment = snake[i];
                if (!this.isInViewport(segment)) continue;
                
                const isHead = i === 0;
                const segmentSize = isHead ? 12 : Math.max(6, 10 - Math.min(i * 0.03, 3));
                const opacity = Math.max(0.7, 1 - (i * 0.008));

                if ('ghost' in powers || hasSpawnProtection) {
                    const flicker = Math.sin(currentTime * 0.01) * 0.2 + 0.6;
                    this.ctx.globalAlpha = opacity * flicker;
                } else {
                    this.ctx.globalAlpha = opacity;
                }
                
                this.ctx.fillStyle = isHead ? this.lightenColor(color, 30) : color;
                this.ctx.beginPath();
                this.ctx.arc(segment.x, segment.y, segmentSize, 0, Math.PI * 2);
                this.ctx.fill();
                
                if (isHead) {
                    this.ctx.fillStyle = 'rgba(255, 255, 255, 0.8)';
                    this.ctx.beginPath();
                    this.ctx.arc(segment.x - 3, segment.y - 2, 2, 0, Math.PI * 2);
                    this.ctx.fill();
                    this.ctx.beginPath();
                    this.ctx.arc(segment.x + 3, segment.y - 2, 2, 0, Math.PI * 2);
                    this.ctx.fill();
                }
            }
            
            this.ctx.restore();
            
            if (snake.length > 0 && name) {
                this.renderPlayerName(snake[0], name, color);
            }
            
            this.renderPowerEffects(snake[0], powers, hasSpawnProtection, currentTime);
        };

        if (this.gameState.players) {
            Object.entries(this.gameState.players).forEach(([playerId, player]) => {
                if (player.alive && player.snake) {
                    renderSnake(player.snake, player.color, player.powers, player.name, true, playerId);
                }
            });
        }

        if (this.gameState.bots) {
            Object.values(this.gameState.bots).forEach(bot => {
                if (bot.alive && bot.snake) {
                    renderSnake(bot.snake, bot.color, bot.powers, bot.name, false);
                }
            });
        }
    }

    renderPlayerName(head, name, color) {
        if (!this.isInViewport(head)) return;
        
        this.ctx.save();
        this.ctx.font = 'bold 14px Inter, sans-serif';
        this.ctx.textAlign = 'center';
        this.ctx.textBaseline = 'bottom';
        
        const nameY = head.y - 20;
        const textWidth = this.ctx.measureText(name).width;
        
        this.ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
        this.ctx.fillRect(head.x - textWidth/2 - 4, nameY - 16, textWidth + 8, 18);
        
        this.ctx.strokeStyle = 'rgba(0, 0, 0, 0.8)';
        this.ctx.lineWidth = 3;
        this.ctx.strokeText(name, head.x, nameY);
        
        this.ctx.fillStyle = '#ffffff';
        this.ctx.fillText(name, head.x, nameY);
        
        this.ctx.restore();
    }

    renderPowerEffects(head, powers, hasSpawnProtection, currentTime) {
        if (hasSpawnProtection) {
            const pulse = Math.sin(currentTime * 0.01) * 0.3 + 0.7;
            const radius = 20 + Math.sin(currentTime * 0.008) * 5;
            
            this.ctx.strokeStyle = `rgba(0, 255, 100, ${pulse})`;
            this.ctx.lineWidth = 3;
            this.ctx.setLineDash([8, 4]);
            this.ctx.beginPath();
            this.ctx.arc(head.x, head.y, radius, 0, Math.PI * 2);
            this.ctx.stroke();
            this.ctx.setLineDash([]);
        }

        if ('shield' in powers) {
            const pulse = Math.sin(currentTime * 0.004) * 0.3 + 0.7;
            const radius = 18;
            
            this.ctx.strokeStyle = `rgba(0, 150, 255, ${pulse})`;
            this.ctx.lineWidth = 2;
            this.ctx.beginPath();
            this.ctx.arc(head.x, head.y, radius, 0, Math.PI * 2);
            this.ctx.stroke();
        }

        if ('speed' in powers) {
            const particles = 6;
            for (let i = 0; i < particles; i++) {
                const angle = (i / particles) * Math.PI * 2 + currentTime * 0.01;
                const distance = 25 + Math.sin(currentTime * 0.008 + i) * 8;
                const x = head.x + Math.cos(angle) * distance;
                const y = head.y + Math.sin(angle) * distance;
                
                const alpha = (Math.sin(currentTime * 0.01 + i) + 1) * 0.25;
                this.ctx.fillStyle = `rgba(255, 200, 0, ${alpha})`;
                this.ctx.beginPath();
                this.ctx.arc(x, y, 2, 0, Math.PI * 2);
                this.ctx.fill();
            }
        }

        if ('magnet' in powers) {
            const pulse = Math.sin(currentTime * 0.006) * 0.3 + 0.4;
            this.ctx.strokeStyle = `rgba(255, 120, 0, ${pulse})`;
            this.ctx.lineWidth = 2;
            this.ctx.beginPath();
            this.ctx.arc(head.x, head.y, 22, 0, Math.PI * 2);
            this.ctx.stroke();
        }

        if ('double_score' in powers) {
            const sparkles = 8;
            for (let i = 0; i < sparkles; i++) {
                const angle = (i / sparkles) * Math.PI * 2 + currentTime * 0.015;
                const distance = 18 + Math.sin(currentTime * 0.012 + i) * 6;
                const x = head.x + Math.cos(angle) * distance;
                const y = head.y + Math.sin(angle) * distance;
                
                const alpha = (Math.sin(currentTime * 0.01 + i) + 1) * 0.3;
                this.ctx.fillStyle = `rgba(255, 255, 0, ${alpha})`;
                this.ctx.beginPath();
                this.ctx.arc(x, y, 1.5, 0, Math.PI * 2);
                this.ctx.fill();
            }
        }
    }

    isInViewport(obj) {
        const bounds = this.renderCache.viewBounds;
        return obj.x >= bounds.left && obj.x <= bounds.right &&
               obj.y >= bounds.top && obj.y <= bounds.bottom;
    }

    renderUI() {
        const spectatorMode = document.getElementById('spectator-mode');
        const targetElement = document.getElementById('spectator-target');
        
        if (this.spectatorMode) {
            spectatorMode.style.display = 'block';
            if (this.spectatorTarget) {
                targetElement.textContent = `Watching: ${this.spectatorTarget}`;
                targetElement.style.display = 'block';
            } else {
                targetElement.style.display = 'none';
            }
        } else {
            spectatorMode.style.display = 'none';
        }
    }

    updateFPS() {
        this.frameCount++;
        const currentTime = Date.now();
        
        if (currentTime - this.lastFpsTime >= 1000) {
            this.fps = this.frameCount;
            this.frameCount = 0;
            this.lastFpsTime = currentTime;
        }
    }

    startRenderLoop() {
        const gameLoop = (currentTime) => {
            this.updateMovement();
            this.updateCamera();
            this.render(currentTime);
            requestAnimationFrame(gameLoop);
        };
        requestAnimationFrame(gameLoop);
    }

    lightenColor(color, percent) {
        const num = parseInt(color.replace("#", ""), 16);
        const amt = Math.round(2.55 * percent);
        const R = Math.min(255, Math.max(0, (num >> 16) + amt));
        const G = Math.min(255, Math.max(0, (num >> 8 & 0x00FF) + amt));
        const B = Math.min(255, Math.max(0, (num & 0x0000FF) + amt));
        return "#" + (0x1000000 + R * 0x10000 + G * 0x100 + B).toString(16).slice(1);
    }

    darkenColor(color, percent) {
        const num = parseInt(color.replace("#", ""), 16);
        const amt = Math.round(2.55 * percent);
        const R = Math.min(255, Math.max(0, (num >> 16) - amt));
        const G = Math.min(255, Math.max(0, (num >> 8 & 0x00FF) - amt));
        const B = Math.min(255, Math.max(0, (num & 0x0000FF) - amt));
        return "#" + (0x1000000 + R * 0x10000 + G * 0x100 + B).toString(16).slice(1);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new Game();
});