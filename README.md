# 🐍 SnakeVortex - Multiplayer Snake Arena

## About

I've created SnakeVortex, a multiplayer snake game that brings the classic gameplay to the web with real-time multiplayer capabilities. This is a fully-featured snake arena where players compete against each other and intelligent AI bots in a dynamic environment. ***This is my first time working with AI bots and on such a game in general, so don't hit me too hard)***

<img alt="Banner" src="https://i.postimg.cc/C1rSDw8Q/image.png">

## Features

I've implemented a comprehensive set of features to make the game engaging and competitive:

### Core Gameplay
- **Real-time Multiplayer**: Up to 20 players can join simultaneously
- **Smooth Movement**: Mouse-controlled snake movement with acceleration
- **Live Leaderboard**: Real-time ranking system showing top players
- **Spectator Mode**: Watch other players after elimination
- **Unique Names**: Automatic name generation ensures no duplicate nicknames

### Power-ups & Abilities

I've designed 5 distinct power-ups that add strategic depth to the gameplay:

#### 🟢 Speed Boost
- **Effect**: Increases movement speed by 50% for 5 seconds
- **Visual**: Golden particles orbit around the snake's head
- **Strategy**: Perfect for escaping dangerous situations or chasing down food

#### 🔵 Shield Protection
- **Effect**: Grants temporary invincibility against collisions for 8 seconds
- **Visual**: Blue pulsing energy shield surrounds the snake
- **Strategy**: Allows aggressive play through enemy territory

#### 🟠 Magnet Power
- **Effect**: Automatically attracts nearby food for 6 seconds
- **Visual**: Orange energy rings pulse around the snake
- **Strategy**: Efficient food collection without precise movement

#### 🟣 Ghost Mode
- **Effect**: Ability to pass through other snakes for 4 seconds
- **Visual**: Snake becomes semi-transparent with flickering effect
- **Strategy**: Escape from enclosed spaces or surprise attacks

#### 🟡 Double Score
- **Effect**: All food consumed gives double points for 7 seconds
- **Visual**: Yellow sparkles and stars dance around the snake
- **Strategy**: Maximize scoring during high-food density periods

### AI & Bots
- **Smart AI Opponents**: 8 intelligent bots with advanced pathfinding
- **Dynamic Behavior**: Bots adapt their strategies based on game state
- **Collision Avoidance**: Sophisticated algorithms to prevent bot collisions
- **Creative Names**: Bots use realistic names like "Alex", "SwiftHunter", "Phoenix"

### Security & Performance
- **Rate Limiting**: Protection against spam and DDoS attacks
- **Error Handling**: Custom 404 and 429 error pages
- **Connection Monitoring**: Automatic reconnection on network issues

## Game Mechanics

### Scoring System
- **Small Food**: 3-7 points based on size
- **Power Food**: 20 points + special ability
- **Double Score**: Multiplies all food points by 2
- **Death Food**: When snakes die, they drop food equal to their segments

### Power-up Spawn
- Power-ups appear randomly across the map
- Each power-up has a unique color and pulsing animation
- Multiple power-ups can be active simultaneously
- Effects stack and have independent timers

### Bot Intelligence
- Bots prioritize power-ups over regular food
- Advanced pathfinding avoids collisions
- Spatial awareness for efficient food collection
- Adaptive behavior based on game state

<img alt="Banner" src="https://i.postimg.cc/yNB1CQBv/image.png">
<img alt="Banner" src="https://i.postimg.cc/Jn0WRSFc/image.png">
