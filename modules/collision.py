import time
from .game_state import game_state, get_nearby_cells
from .utils import distance_squared

def check_collision(snake, entity_id, entity_type):
    if not snake or len(snake) == 0:
        return False
    
    head = snake[0]
    
    arena = game_state.get('arena')
    if arena and all(k in arena for k in ('min_x', 'min_y', 'max_x', 'max_y')):
        min_x = float(arena['min_x'])
        min_y = float(arena['min_y'])
        max_x = float(arena['max_x'])
        max_y = float(arena['max_y'])
    else:
        min_x, min_y, max_x, max_y = 0.0, 0.0, 2000.0, 2000.0

    if head['x'] < min_x or head['x'] > max_x or head['y'] < min_y or head['y'] > max_y:
        return True

    entity = None
    if entity_type == 'player':
        entity = game_state['players'].get(entity_id)
    elif entity_type == 'bot':
        entity = game_state['bots'].get(entity_id)

    now_ms = time.time() * 1000
    if entity:
        powers = entity.get('powers', {})
        if 'shield' in powers and now_ms < powers['shield']:
            return False
        if 'ghost' in powers and now_ms < powers['ghost']:
            return False
        if entity_type == 'player' and entity.get('spawn_protection') and now_ms < entity['spawn_protection']:
            return False
    
    nearby_cells = get_nearby_cells(head['x'], head['y'])
    
    for cell in nearby_cells:
        cell_entities = game_state['spatial_grid'].get(cell, [])
        
        for other_type, other_id, segment in cell_entities:
            if other_id == entity_id:
                continue

            other_entity = None
            if other_type == 'player':
                other_entity = game_state['players'].get(other_id)
            elif other_type == 'bot':
                other_entity = game_state['bots'].get(other_id)
            if other_entity:
                other_powers = other_entity.get('powers', {})
                if 'ghost' in other_powers and now_ms < other_powers['ghost']:
                    continue
            
            if distance_squared(head, segment) < 625:
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
