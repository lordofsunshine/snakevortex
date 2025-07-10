import time
import random
from collections import defaultdict

MAX_PLAYERS = 20
FOOD_COUNT = 200
POWER_FOOD_COUNT = 25
INITIAL_SNAKE_LENGTH = 4
WORLD_WIDTH = 2000
WORLD_HEIGHT = 2000
GRID_SIZE = 100

game_state = {
    'players': {},
    'bots': {},
    'food': [],
    'power_food': [],
    'leaderboard': [],
    'spatial_grid': defaultdict(list),
    'last_leaderboard_update': 0,
    'leaderboard_cache': []
}

connected_clients = set()

_position_pool = []
_pool_refill_time = 0

def get_grid_key(x, y):
    return (int(x // GRID_SIZE), int(y // GRID_SIZE))

def get_nearby_cells(x, y, radius=1):
    center_x, center_y = get_grid_key(x, y)
    cells = []
    for dx in range(-radius, radius + 1):
        for dy in range(-radius, radius + 1):
            cells.append((center_x + dx, center_y + dy))
    return cells

def update_spatial_grid():
    game_state['spatial_grid'].clear()
    
    for player_id, player in game_state['players'].items():
        if player['alive'] and player['snake']:
            for i, segment in enumerate(player['snake']):
                cell = get_grid_key(segment['x'], segment['y'])
                game_state['spatial_grid'][cell].append(('player', player_id, segment))
    
    for bot_id, bot in game_state['bots'].items():
        if bot['alive'] and bot['snake']:
            for i, segment in enumerate(bot['snake']):
                cell = get_grid_key(segment['x'], segment['y'])
                game_state['spatial_grid'][cell].append(('bot', bot_id, segment))

def get_cached_leaderboard():
    current_time = time.time() * 1000
    
    if current_time - game_state['last_leaderboard_update'] > 500:
        all_entities = []
        
        for player in game_state['players'].values():
            if player['alive']:
                all_entities.append({
                    'name': player['name'],
                    'score': player['score'],
                    'length': player['length']
                })
        
        for bot in game_state['bots'].values():
            if bot['alive']:
                all_entities.append({
                    'name': bot['name'],
                    'score': bot['score'],
                    'length': bot['length']
                })
        
        game_state['leaderboard_cache'] = sorted(all_entities, key=lambda x: x['score'], reverse=True)
        game_state['last_leaderboard_update'] = current_time
    
    return game_state['leaderboard_cache']

def get_random_position_cached():
    global _position_pool, _pool_refill_time
    
    current_time = time.time() * 1000
    
    if current_time - _pool_refill_time > 1000 or len(_position_pool) < 10:
        _position_pool = []
        for _ in range(50):
            _position_pool.append({
                'x': random.randint(50, WORLD_WIDTH - 50),
                'y': random.randint(50, WORLD_HEIGHT - 50)
            })
        _pool_refill_time = current_time
    
    if _position_pool:
        return _position_pool.pop()
    
    return {
        'x': random.randint(50, WORLD_WIDTH - 50),
        'y': random.randint(50, WORLD_HEIGHT - 50)
    }
