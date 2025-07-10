import math
import random
import time
import uuid
from .game_state import game_state, INITIAL_SNAKE_LENGTH, get_nearby_cells
from .snake_logic import create_snake
from .utils import find_safe_spawn_position, distance_squared

BOT_NAMES = [
    "Viper", "Anaconda", "Python", "Cobra", "Boa",
    "Adder", "Asp", "Mamba", "Serpent", "Rattler",
    "Venom", "Striker", "Fang", "Coil", "Slither",
    "Shadow", "Vortex", "Titan", "Fury", "Blaze",
    "Storm", "Nexus", "Phantom", "Razor", "Chaos"
]

HUMAN_NAMES = [
    "Alex", "Blake", "Casey", "Dylan", "Eden", "Finley", "Gray",
    "Hunter", "Ivan", "Jack", "Kyle", "Luna", "Max", "Nova",
    "Oliver", "Phoenix", "Quinn", "River", "Sage", "Tyler",
    "Uma", "Victor", "Wade", "Xavier", "Yuki", "Zara",
    "Ace", "Blaze", "Cruz", "Dash", "Echo", "Felix", "Ghost",
    "Hawk", "Iris", "Jax", "Knox", "Leo", "Milo", "Neo",
    "Orion", "Piper", "Raven", "Sky", "Tara", "Zoe"
]

ADJECTIVES = [
    "Swift", "Silent", "Mighty", "Clever", "Bold", "Quick",
    "Fierce", "Brave", "Sharp", "Wild", "Fast", "Strong",
    "Agile", "Sly", "Rapid", "Keen", "Smooth", "Stealth",
    "Lightning", "Thunder", "Frost", "Fire", "Storm", "Wind"
]

NOUNS = [
    "Hunter", "Warrior", "Rider", "Master", "King", "Queen",
    "Legend", "Hero", "Champion", "Guardian", "Phantom", "Spirit",
    "Wolf", "Eagle", "Tiger", "Dragon", "Falcon", "Panther",
    "Viper", "Shark", "Lion", "Bear", "Fox", "Raven"
]

food_cache = {'data': [], 'timestamp': 0, 'spatial_index': {}}
power_food_cache = {'data': [], 'timestamp': 0}
_bot_decision_cache = {}
_pathfinding_cache = {}

def generate_creative_name():
    patterns = [
        lambda: random.choice(HUMAN_NAMES),
        lambda: random.choice(BOT_NAMES),
        lambda: f"{random.choice(ADJECTIVES)}{random.choice(NOUNS)}",
        lambda: f"{random.choice(ADJECTIVES)}_{random.choice(NOUNS)}",
        lambda: f"{random.choice(HUMAN_NAMES)}{random.choice(['X', 'Z', 'Pro', 'Max', ''])}"
    ]
    
    return random.choice(patterns)()

def get_unique_bot_name():
    used_names = set()
    
    for player in game_state['players'].values():
        used_names.add(player['name'].lower())
    
    for bot in game_state['bots'].values():
        used_names.add(bot['name'].lower())
    
    max_attempts = 50
    for _ in range(max_attempts):
        name = generate_creative_name()
        if name.lower() not in used_names:
            return name
    
    suffix = random.randint(100, 999)
    base_name = random.choice(HUMAN_NAMES)
    return f"{base_name}{suffix}"

def create_bot():
    bot_id = str(uuid.uuid4())
    start_pos = find_safe_spawn_position()
    
    bot = {
        'id': bot_id,
        'name': get_unique_bot_name(),
        'snake': create_snake(start_pos),
        'direction': random.uniform(0, 2 * math.pi),
        'target_direction': random.uniform(0, 2 * math.pi),
        'speed': 2.0,
        'score': 0,
        'length': INITIAL_SNAKE_LENGTH,
        'alive': True,
        'color': f"#{random.randint(100, 255):02x}{random.randint(100, 255):02x}{random.randint(100, 255):02x}",
        'powers': {},
        'last_direction_change': 0,
        'cached_nearby_food': [],
        'last_food_scan': 0,
        'decision_cooldown': 0
    }
    
    game_state['bots'][bot_id] = bot
    return bot

def update_food_cache():
    current_time = time.time() * 1000
    
    if current_time - food_cache['timestamp'] > 150:
        active_food = [food for food in game_state['food'] if food.get('scale', 1.0) > 0.5]
        food_cache['data'] = active_food
        food_cache['timestamp'] = current_time
        
        spatial_index = {}
        for food in active_food:
            key = (int(food['x'] // 100), int(food['y'] // 100))
            if key not in spatial_index:
                spatial_index[key] = []
            spatial_index[key].append(food)
        food_cache['spatial_index'] = spatial_index
    
    if current_time - power_food_cache['timestamp'] > 150:
        power_food_cache['data'] = [power for power in game_state['power_food'] if power.get('scale', 1.0) > 0.5]
        power_food_cache['timestamp'] = current_time

def bot_ai(bot):
    if not bot['alive'] or not bot['snake']:
        return
    
    current_time = time.time() * 1000
    head = bot['snake'][0]
    
    if current_time < bot.get('decision_cooldown', 0):
        return
    
    bot_id = bot['id']
    cache_key = (bot_id, int(head['x'] // 50), int(head['y'] // 50))
    
    if cache_key in _bot_decision_cache:
        cache_time, cached_decision = _bot_decision_cache[cache_key]
        if current_time - cache_time < 200:
            bot['target_direction'] = cached_decision
            update_bot_direction(bot)
            return
    
    if current_time - bot['last_food_scan'] > 250:
        bot['cached_nearby_food'] = get_nearby_food_spatial(head, 180)
        bot['last_food_scan'] = current_time
    
    target_direction = calculate_target_direction(bot, head, current_time)
    
    _bot_decision_cache[cache_key] = (current_time, target_direction)
    bot['target_direction'] = target_direction
    bot['decision_cooldown'] = current_time + random.randint(80, 150)
    
    update_bot_direction(bot)

def calculate_target_direction(bot, head, current_time):
    nearest_power = find_nearest_power_food_cached(head)
    if nearest_power and distance_squared(head, nearest_power) < 22500:
        return math.atan2(nearest_power['y'] - head['y'], nearest_power['x'] - head['x'])
    
    if bot['cached_nearby_food']:
        target_food = min(bot['cached_nearby_food'], key=lambda f: distance_squared(head, f))
        return math.atan2(target_food['y'] - head['y'], target_food['x'] - head['x'])
    
    if random.random() < 0.15:
        return random.uniform(0, 2 * math.pi)
    
    return bot.get('target_direction', bot['direction'])

def update_bot_direction(bot):
    angle_diff = bot['target_direction'] - bot['direction']
    
    while angle_diff > math.pi:
        angle_diff -= 2 * math.pi
    while angle_diff < -math.pi:
        angle_diff += 2 * math.pi
    
    max_turn_rate = 0.12
    if abs(angle_diff) > max_turn_rate:
        bot['direction'] += max_turn_rate if angle_diff > 0 else -max_turn_rate
    else:
        bot['direction'] = bot['target_direction']
    
    bot['direction'] = bot['direction'] % (2 * math.pi)
    
    collision_avoidance_optimized(bot)

def get_nearby_food_spatial(position, radius):
    center_key = (int(position['x'] // 100), int(position['y'] // 100))
    nearby_food = []
    radius_squared = radius * radius
    
    for dx in range(-2, 3):
        for dy in range(-2, 3):
            key = (center_key[0] + dx, center_key[1] + dy)
            if key in food_cache['spatial_index']:
                for food in food_cache['spatial_index'][key]:
                    if distance_squared(position, food) < radius_squared:
                        nearby_food.append(food)
    
    return nearby_food

def find_nearest_power_food_cached(position):
    if not power_food_cache['data']:
        return None
    
    return min(power_food_cache['data'], key=lambda f: distance_squared(position, f))

def collision_avoidance_optimized(bot):
    head = bot['snake'][0]
    check_distance = 70
    
    future_x = head['x'] + math.cos(bot['direction']) * check_distance
    future_y = head['y'] + math.sin(bot['direction']) * check_distance
    
    if future_x < 60 or future_x > 1940 or future_y < 60 or future_y > 1940:
        find_safe_direction_optimized(bot, head)
        return
    
    cache_key = (bot['id'], int(future_x // 50), int(future_y // 50))
    if cache_key in _pathfinding_cache:
        cache_time, is_safe = _pathfinding_cache[cache_key]
        if time.time() * 1000 - cache_time < 300:
            if not is_safe:
                find_safe_direction_optimized(bot, head)
            return
    
    nearby_cells = get_nearby_cells(future_x, future_y)
    danger_detected = False
    future_pos = {'x': future_x, 'y': future_y}
    
    for cell in nearby_cells:
        cell_entities = game_state['spatial_grid'].get(cell, [])
        for entity_type, entity_id, segment in cell_entities:
            if entity_id == bot['id']:
                continue
            
            if distance_squared(future_pos, segment) < 900:
                danger_detected = True
                break
        if danger_detected:
            break
    
    _pathfinding_cache[cache_key] = (time.time() * 1000, not danger_detected)
    
    if danger_detected:
        find_safe_direction_optimized(bot, head)

def find_safe_direction_optimized(bot, head):
    avoidance_angles = [-math.pi/3, math.pi/3, -math.pi/2, math.pi/2, -2*math.pi/3, 2*math.pi/3]
    check_distance = 60
    
    for angle_offset in avoidance_angles:
        new_direction = bot['direction'] + angle_offset
        test_x = head['x'] + math.cos(new_direction) * check_distance
        test_y = head['y'] + math.sin(new_direction) * check_distance
        
        if is_safe_direction_optimized(test_x, test_y, bot['id']):
            bot['target_direction'] = new_direction
            return
    
    bot['target_direction'] = bot['direction'] + math.pi

def is_safe_direction_optimized(x, y, bot_id):
    if x < 60 or x > 1940 or y < 60 or y > 1940:
        return False
    
    nearby_cells = get_nearby_cells(x, y)
    test_pos = {'x': x, 'y': y}
    
    for cell in nearby_cells:
        cell_entities = game_state['spatial_grid'].get(cell, [])
        for entity_type, entity_id, segment in cell_entities:
            if entity_id == bot_id:
                continue
            
            if distance_squared(test_pos, segment) < 625:
                return False
    
    return True

def clear_bot_caches():
    global _bot_decision_cache, _pathfinding_cache
    _bot_decision_cache.clear()
    _pathfinding_cache.clear()
