import math
import time
from .utils import distance_squared

def create_snake(position):
    return [
        {'x': position['x'], 'y': position['y']},
        {'x': position['x'] - 10, 'y': position['y']},
        {'x': position['x'] - 20, 'y': position['y']},
        {'x': position['x'] - 30, 'y': position['y']}
    ]

def move_snake(snake, direction, speed):
    if not snake or direction is None:
        return
    
    dx = math.cos(direction) * speed
    dy = math.sin(direction) * speed
    
    new_head = {
        'x': snake[0]['x'] + dx,
        'y': snake[0]['y'] + dy
    }
    
    snake.insert(0, new_head)
    
    if len(snake) > 1:
        snake.pop()

def grow_snake(snake):
    if len(snake) < 2:
        return
    
    tail = snake[-1]
    prev_tail = snake[-2]
    
    dx = tail['x'] - prev_tail['x']
    dy = tail['y'] - prev_tail['y']
    
    length = math.sqrt(dx * dx + dy * dy)
    if length > 0:
        dx /= length
        dy /= length
    
    new_segment = {
        'x': tail['x'] + dx * 8,
        'y': tail['y'] + dy * 8
    }
    
    snake.append(new_segment)

def apply_power_effects(entity):
    current_time = time.time() * 1000

    if 'magnet' in entity.get('powers', {}):
        if current_time < entity['powers']['magnet']:
            apply_magnet_effect(entity)

def update_entity_speed(entity, current_time=None):
    if current_time is None:
        current_time = time.time() * 1000

    desired = float(entity.get('desired_speed', entity.get('speed', 2.0)))
    speed = desired

    powers = entity.get('powers', {})
    if 'speed' in powers and current_time < powers['speed']:
        speed *= 1.35

    entity['speed'] = min(4.0, max(0.5, speed))

def apply_magnet_effect(entity):
    if not entity['snake']:
        return
    
    head = entity['snake'][0]
    magnet_range = 80
    
    from .game_state import game_state
    
    for food in game_state['food']:
        if food.get('scale', 1.0) > 0:
            dist_sq = distance_squared(head, food)
            if dist_sq < magnet_range * magnet_range:
                dx = head['x'] - food['x']
                dy = head['y'] - food['y']
                
                if dist_sq > 0:
                    dist = math.sqrt(dist_sq)
                    move_factor = 2.0 / dist
                    
                    food['x'] += dx * move_factor
                    food['y'] += dy * move_factor

def clean_expired_powers(entity):
    current_time = time.time() * 1000
    expired_powers = []
    
    for power_type, expiry_time in entity.get('powers', {}).items():
        if current_time >= expiry_time:
            expired_powers.append(power_type)
    
    for power_type in expired_powers:
        del entity['powers'][power_type]
