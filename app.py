import asyncio
import json
import math
import re
import time
import uuid
import random
from collections import defaultdict
from quart import Quart, render_template, websocket, request, abort

from modules.game_state import game_state, connected_clients, MAX_PLAYERS, FOOD_COUNT, POWER_FOOD_COUNT, INITIAL_SNAKE_LENGTH
from modules.snake_logic import create_snake
from modules.utils import find_safe_spawn_position
from modules.food_system import generate_food, generate_power_food, create_death_food
from modules.bot_ai import create_bot
from modules.game_loop import game_loop
from modules.arena_system import init_arena

app = Quart(__name__)

rate_limit_storage = defaultdict(list)
RATE_LIMIT_REQUESTS = 10
RATE_LIMIT_WINDOW = 60
MAX_WS_MESSAGE_SIZE = 4096
MIN_MOVE_INTERVAL_MS = 40
PING_INTERVAL_MS = 800
HEX_COLOR_RE = re.compile(r'^#[0-9a-fA-F]{6}$')

def check_rate_limit(client_ip):
    current_time = time.time()
    requests = rate_limit_storage[client_ip]
    
    requests[:] = [req_time for req_time in requests if current_time - req_time < RATE_LIMIT_WINDOW]
    
    if len(requests) >= RATE_LIMIT_REQUESTS:
        return False
    
    requests.append(current_time)
    
    if len(rate_limit_storage) > 1000:
        old_ips = [ip for ip, reqs in rate_limit_storage.items() 
                  if not reqs or current_time - max(reqs) > RATE_LIMIT_WINDOW * 2]
        for ip in old_ips[:500]:
            del rate_limit_storage[ip]
    
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

def is_same_origin():
    origin = websocket.headers.get('Origin')
    if not origin:
        return True
    host = websocket.headers.get('Host')
    if not host:
        return False
    return origin.startswith(f"http://{host}") or origin.startswith(f"https://{host}")

def sanitize_name(name):
    if not isinstance(name, str):
        return ""
    name = name.strip()
    cleaned = []
    for ch in name:
        if ch.isalnum() or ch in " _-":
            cleaned.append(ch)
    return "".join(cleaned)[:15].strip()

def sanitize_color(color):
    if isinstance(color, str) and HEX_COLOR_RE.match(color):
        return color
    return "#ff6b6b"

def parse_direction(value):
    try:
        direction = float(value)
    except Exception:
        return None
    if not math.isfinite(direction):
        return None
    return direction % (2 * math.pi)

def parse_ping(value):
    try:
        ping = int(value)
    except Exception:
        return 0
    return max(0, min(5000, ping))

def remove_player(player_id, drop_food=True):
    if not player_id:
        return
    player = game_state['players'].get(player_id)
    if not player:
        return
    if drop_food and player.get('alive') and player.get('snake'):
        death_food = create_death_food(player['snake'], player.get('score', 0))
        game_state['food'].extend(death_food)
    del game_state['players'][player_id]

async def send_error(message):
    await websocket.send(json.dumps({'type': 'error', 'message': message}))

async def handle_join(current_player_id, data):
    if current_player_id:
        remove_player(current_player_id, drop_food=False)

    if len(game_state['players']) >= MAX_PLAYERS:
        await send_error('Server is full')
        return None

    name = sanitize_name(data.get('name', ''))
    if not name:
        await send_error('Invalid nickname')
        return None

    player_id = str(uuid.uuid4())
    start_pos = find_safe_spawn_position()
    unique_name = get_unique_name(name)

    player = {
        'id': player_id,
        'name': unique_name,
        'snake': create_snake(start_pos),
        'direction': None,
        'speed': 2.0,
        'desired_speed': 2.0,
        'score': 0,
        'length': INITIAL_SNAKE_LENGTH,
        'alive': True,
        'color': sanitize_color(data.get('color')),
        'powers': {},
        'ping': 0,
        'spawn_time_ms': time.time() * 1000,
        'spawn_duration_ms': 700,
        'spawn_protection': time.time() * 1000 + 5000,
        'last_ping': time.time()
    }

    game_state['players'][player_id] = player

    await websocket.send(json.dumps({
        'type': 'player_id',
        'player_id': player_id,
        'assigned_name': unique_name
    }))

    return player_id

def handle_move(current_player_id, data, last_move_ms):
    if not current_player_id:
        return last_move_ms

    now_ms = time.time() * 1000
    if now_ms - last_move_ms < MIN_MOVE_INTERVAL_MS:
        return last_move_ms

    player = game_state['players'].get(current_player_id)
    if not player or not player.get('alive'):
        return now_ms

    direction = parse_direction(data.get('direction'))
    if direction is None:
        return now_ms

    player['direction'] = direction
    player['last_ping'] = time.time()
    player['desired_speed'] = 3.0 if bool(data.get('accelerating', False)) else 2.0

    return now_ms

def handle_ping(current_player_id, data, last_ping_ms):
    if not current_player_id:
        return last_ping_ms

    now_ms = time.time() * 1000
    if now_ms - last_ping_ms < PING_INTERVAL_MS:
        return last_ping_ms

    player = game_state['players'].get(current_player_id)
    if not player:
        return now_ms

    player['ping'] = parse_ping(data.get('ping'))
    player['last_ping'] = time.time()
    return now_ms

@app.route('/')
async def index():
    client_ip = request.remote_addr
    if not check_rate_limit(client_ip):
        abort(429)
    
    return await render_template('index.html')

@app.after_request
async def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Cross-Origin-Opener-Policy'] = 'same-origin'
    response.headers['Cross-Origin-Resource-Policy'] = 'same-origin'
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com data:; "
        "img-src 'self' data: https:; "
        "connect-src 'self' ws: wss:; "
        "frame-ancestors 'none'"
    )
    return response

@app.errorhandler(404)
async def not_found(error):
    return '''Page not found''', 404

@app.errorhandler(429)
async def rate_limit_exceeded(error):
    return '''Too many requests''', 429

@app.websocket('/ws')
async def websocket_endpoint():
    if not is_same_origin():
        return

    ws_obj = websocket._get_current_object()
    connected_clients.add(ws_obj)
    current_player_id = None
    last_move_ms = 0
    last_ping_ms = 0
    
    try:
        while True:
            message = await websocket.receive()
            if not isinstance(message, str) or len(message) > MAX_WS_MESSAGE_SIZE:
                continue

            try:
                data = json.loads(message)
            except Exception:
                continue

            if not isinstance(data, dict) or 'type' not in data:
                continue

            msg_type = data.get('type')
            
            if msg_type == 'join':
                current_player_id = await handle_join(current_player_id, data)
            elif msg_type == 'move':
                last_move_ms = handle_move(current_player_id, data, last_move_ms)
            
            elif msg_type == 'ping':
                last_ping_ms = handle_ping(current_player_id, data, last_ping_ms)
    
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        connected_clients.discard(ws_obj)
        remove_player(current_player_id, drop_food=True)

def initialize_game():
    init_arena()
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
    app.run(host='0.0.0.0', port=8081, debug=False)
