import random
import time
from .game_state import game_state, WORLD_WIDTH, WORLD_HEIGHT, get_random_position_cached
from .arena_system import clamp_to_arena

FOOD_COLORS = ['#ff6b6b', '#4ecdc4', '#45b7d1', '#f9ca24', '#f0932b', '#eb4d4b', '#6c5ce7', '#a29bfe']

POWER_TYPES = [
    {'type': 'speed', 'color': '#00ff00', 'duration': 5000},
    {'type': 'shield', 'color': '#0080ff', 'duration': 8000},
    {'type': 'magnet', 'color': '#ff8000', 'duration': 6000},
    {'type': 'ghost', 'color': '#ff00ff', 'duration': 4000},
    {'type': 'double_score', 'color': '#ffff00', 'duration': 7000}
]

_food_batch_cache = []
_power_batch_cache = []

def generate_food():
    position = get_random_position_cached()
    return {
        'x': position['x'],
        'y': position['y'],
        'size': random.randint(3, 7),
        'color': random.choice(FOOD_COLORS),
        'scale': 1.0,
        'created_at': time.time() * 1000
    }

def generate_power_food():
    position = get_random_position_cached()
    power_type = random.choice(POWER_TYPES)
    return {
        'x': position['x'],
        'y': position['y'],
        'size': random.randint(8, 12),
        'color': power_type['color'],
        'type': power_type['type'],
        'duration': power_type['duration'],
        'scale': 1.0,
        'created_at': time.time() * 1000
    }

def batch_generate_food(count):
    global _food_batch_cache
    
    if len(_food_batch_cache) < count:
        _food_batch_cache.extend([generate_food() for _ in range(count * 2)])
    
    result = _food_batch_cache[:count]
    _food_batch_cache = _food_batch_cache[count:]
    return result

def batch_generate_power_food(count):
    global _power_batch_cache
    
    if len(_power_batch_cache) < count:
        _power_batch_cache.extend([generate_power_food() for _ in range(count * 2)])
    
    result = _power_batch_cache[:count]
    _power_batch_cache = _power_batch_cache[count:]
    return result

def create_death_food(snake, score):
    if not snake or len(snake) < 2:
        return []
    
    food_count = min(len(snake) // 2, 15)
    death_food = []
    
    for i in range(food_count):
        if i < len(snake):
            segment = snake[i]
            x, y = clamp_to_arena(segment['x'] + random.randint(-20, 20), segment['y'] + random.randint(-20, 20), margin=10.0)
            death_food.append({
                'x': x,
                'y': y,
                'size': random.randint(4, 8),
                'color': random.choice(FOOD_COLORS),
                'scale': 1.0,
                'created_at': time.time() * 1000
            })
    
    return death_food

def animate_food_scaling():
    current_time = time.time() * 1000
    
    for food in game_state['food']:
        if 'scale' in food:
            age = current_time - food.get('created_at', current_time)
            if age < 200:
                food['scale'] = min(1.0, age / 200.0)
    
    for power in game_state['power_food']:
        if 'scale' in power:
            age = current_time - power.get('created_at', current_time)
            if age < 300:
                power['scale'] = min(1.0, age / 300.0)

def remove_consumed_food(consumed_indices):
    if not consumed_indices:
        return
    
    for index in sorted(consumed_indices, reverse=True):
        if 0 <= index < len(game_state['food']):
            game_state['food'].pop(index)

def remove_consumed_power_food(consumed_indices):
    if not consumed_indices:
        return
    
    for index in sorted(consumed_indices, reverse=True):
        if 0 <= index < len(game_state['power_food']):
            game_state['power_food'].pop(index)
