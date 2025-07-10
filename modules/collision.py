import math
from .game_state import game_state, get_nearby_cells

_collision_cache = {}

def distance_squared(pos1, pos2):
    dx = pos1['x'] - pos2['x']
    dy = pos1['y'] - pos2['y']
    return dx * dx + dy * dy

def check_collision(snake, entity_id, entity_type):
    if not snake or len(snake) == 0:
        return False
    
    head = snake[0]
    
    if head['x'] < 0 or head['x'] > 2000 or head['y'] < 0 or head['y'] > 2000:
        return True
    
    nearby_cells = get_nearby_cells(head['x'], head['y'])
    
    for cell in nearby_cells:
        cell_entities = game_state['spatial_grid'].get(cell, [])
        
        for other_type, other_id, segment in cell_entities:
            if other_id == entity_id:
                continue
            
            if distance_squared(head, segment) < 400:
                return True
    
    return False

def check_food_collision(snake, entity_id):
    if not snake or len(snake) == 0:
        return []
    
    head = snake[0]
    consumed_food = []
    
    for i, food in enumerate(game_state['food']):
        if food.get('scale', 1.0) > 0 and distance_squared(head, food) < 400:
            consumed_food.append(i)
    
    return consumed_food

def check_power_food_collision(snake, entity_id):
    if not snake or len(snake) == 0:
        return []
    
    head = snake[0]
    consumed_power = []
    
    for i, power in enumerate(game_state['power_food']):
        if power.get('scale', 1.0) > 0 and distance_squared(head, power) < 625:
            consumed_power.append(i)
    
    return consumed_power

def clear_collision_cache():
    global _collision_cache
    _collision_cache.clear()
