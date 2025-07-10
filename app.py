import asyncio
import json
import time
import uuid
import random
from collections import defaultdict
from quart import Quart, render_template, websocket, request, abort
from quart_cors import cors

from modules.game_state import game_state, connected_clients, MAX_PLAYERS, FOOD_COUNT, POWER_FOOD_COUNT, INITIAL_SNAKE_LENGTH
from modules.snake_logic import create_snake
from modules.utils import find_safe_spawn_position
from modules.food_system import generate_food, generate_power_food
from modules.bot_ai import create_bot
from modules.game_loop import game_loop

app = Quart(__name__)
app = cors(app)

rate_limit_storage = defaultdict(list)
RATE_LIMIT_REQUESTS = 10
RATE_LIMIT_WINDOW = 60

def check_rate_limit(client_ip):
    current_time = time.time()
    requests = rate_limit_storage[client_ip]
    
    requests[:] = [req_time for req_time in requests if current_time - req_time < RATE_LIMIT_WINDOW]
    
    if len(requests) >= RATE_LIMIT_REQUESTS:
        return False
    
    requests.append(current_time)
    return True

def is_name_unique(name):
    for player in game_state['players'].values():
        if player['name'].lower() == name.lower():
            return False
    
    for bot in game_state['bots'].values():
        if bot['name'].lower() == name.lower():
            return False
    
    return True

def get_unique_name(base_name):
    if is_name_unique(base_name):
        return base_name
    
    counter = 1
    while counter <= 999:
        new_name = f"{base_name}_{counter}"
        if is_name_unique(new_name):
            return new_name
        counter += 1
    
    return f"{base_name}_{random.randint(1000, 9999)}"

@app.route('/')
async def index():
    client_ip = request.remote_addr
    if not check_rate_limit(client_ip):
        abort(429)
    
    return await render_template('index.html')

@app.errorhandler(404)
async def not_found(error):
    return '''Page not found''', 404

@app.errorhandler(429)
async def rate_limit_exceeded(error):
    return '''Too many requests''', 429

@app.websocket('/ws')
async def websocket_endpoint():
    connected_clients.add(websocket._get_current_object())
    
    try:
        while True:
            message = await websocket.receive()
            data = json.loads(message)
            
            if data['type'] == 'join':
                if len(game_state['players']) >= MAX_PLAYERS:
                    await websocket.send(json.dumps({
                        'type': 'error',
                        'message': 'Server is full'
                    }))
                    continue
                
                player_id = str(uuid.uuid4())
                start_pos = find_safe_spawn_position()
                unique_name = get_unique_name(data['name'])
                
                player = {
                    'id': player_id,
                    'name': unique_name,
                    'snake': create_snake(start_pos),
                    'direction': None,
                    'speed': 2.0,
                    'score': 0,
                    'length': INITIAL_SNAKE_LENGTH,
                    'alive': True,
                    'color': data.get('color', '#ff6b6b'),
                    'powers': {},
                    'ping': 0,
                    'spawn_protection': time.time() * 1000 + 5000
                }
                
                game_state['players'][player_id] = player
                
                await websocket.send(json.dumps({
                    'type': 'player_id',
                    'player_id': player_id,
                    'assigned_name': unique_name
                }))
                
            elif data['type'] == 'move':
                player_id = data['player_id']
                if player_id in game_state['players']:
                    player = game_state['players'][player_id]
                    if player['alive']:
                        player['direction'] = data['direction']
                        if data.get('accelerating', False):
                            player['speed'] = 3.0
                        else:
                            player['speed'] = 2.0
            
            elif data['type'] == 'ping':
                player_id = data['player_id']
                if player_id in game_state['players']:
                    game_state['players'][player_id]['ping'] = data['ping']
    
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        connected_clients.discard(websocket._get_current_object())

def initialize_game():
    for _ in range(FOOD_COUNT):
        game_state['food'].append(generate_food())
    
    for _ in range(POWER_FOOD_COUNT):
        game_state['power_food'].append(generate_power_food())
    
    for _ in range(8):
        create_bot()

@app.before_serving
async def startup():
    initialize_game()
    asyncio.create_task(game_loop())

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)
