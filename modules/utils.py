import math
import random
from .game_state import game_state, WORLD_WIDTH, WORLD_HEIGHT

def distance_squared(pos1, pos2):
    dx = pos1['x'] - pos2['x']
    dy = pos1['y'] - pos2['y']
    return dx * dx + dy * dy


def find_safe_spawn_position():
    max_attempts = 50
    min_distance = 150

    arena = game_state.get('arena')
    if arena and all(k in arena for k in ('min_x', 'min_y', 'max_x', 'max_y')):
        min_x = int(float(arena['min_x']) + 100)
        min_y = int(float(arena['min_y']) + 100)
        max_x = int(float(arena['max_x']) - 100)
        max_y = int(float(arena['max_y']) - 100)
    else:
        min_x = 100
        min_y = 100
        max_x = WORLD_WIDTH - 100
        max_y = WORLD_HEIGHT - 100

    if min_x >= max_x:
        min_x = 0
        max_x = WORLD_WIDTH
    if min_y >= max_y:
        min_y = 0
        max_y = WORLD_HEIGHT
    
    for _ in range(max_attempts):
        position = {
            'x': random.randint(min_x, max_x),
            'y': random.randint(min_y, max_y)
        }
        
        if is_position_safe(position, min_distance):
            return position
    
    return {
        'x': random.randint(min_x, max_x),
        'y': random.randint(min_y, max_y)
    }

def is_position_safe(position, min_distance):
    min_distance_squared = min_distance * min_distance
    
    for player in game_state['players'].values():
        if player['alive'] and player['snake']:
            for segment in player['snake']:
                if distance_squared(position, segment) < min_distance_squared:
                    return False
    
    for bot in game_state['bots'].values():
        if bot['alive'] and bot['snake']:
            for segment in bot['snake']:
                if distance_squared(position, segment) < min_distance_squared:
                    return False
    
    return True

def clamp(value, min_value, max_value):
    return max(min_value, min(max_value, value))

def normalize_angle(angle):
    while angle > math.pi:
        angle -= 2 * math.pi
    while angle < -math.pi:
        angle += 2 * math.pi
    return angle
