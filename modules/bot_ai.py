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
MAX_CACHE_SIZE = 1000

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
    
    bot_type = random.choice(['aggressive', 'hunter', 'defensive', 'collector'])
    personality = generate_personality(bot_type)
    
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
        'decision_cooldown': 0,
        'bot_type': bot_type,
        'personality': personality,
        'target_player': None,
        'hunt_duration': 0,
        'mistake_chance': personality['mistake_rate'],
        'reaction_delay': personality['reaction_time'],
        'last_mistake': 0,
        'hunting_range': personality['hunt_range']
    }
    
    game_state['bots'][bot_id] = bot
    return bot

def generate_personality(bot_type):
    personalities = {
        'aggressive': {
            'hunt_range': 300,
            'chase_priority': 0.8,
            'mistake_rate': 0.05,
            'reaction_time': random.randint(50, 150),
            'risk_tolerance': 0.9
        },
        'hunter': {
            'hunt_range': 400,
            'chase_priority': 0.9,
            'mistake_rate': 0.03,
            'reaction_time': random.randint(30, 100),
            'risk_tolerance': 0.7
        },
        'defensive': {
            'hunt_range': 150,
            'chase_priority': 0.3,
            'mistake_rate': 0.08,
            'reaction_time': random.randint(100, 250),
            'risk_tolerance': 0.3
        },
        'collector': {
            'hunt_range': 200,
            'chase_priority': 0.4,
            'mistake_rate': 0.06,
            'reaction_time': random.randint(80, 200),
            'risk_tolerance': 0.5
        }
    }
    return personalities[bot_type]

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
        cache_validity = 200 + bot.get('reaction_delay', 100)
        if current_time - cache_time < cache_validity:
            bot['target_direction'] = cached_decision
            update_bot_direction(bot)
            return
    
    if current_time - bot['last_food_scan'] > 250:
        bot['cached_nearby_food'] = get_nearby_food_spatial(head, 180)
        bot['last_food_scan'] = current_time
    
    target_direction = calculate_target_direction(bot, head, current_time)
    
    if len(_bot_decision_cache) > MAX_CACHE_SIZE:
        oldest_keys = sorted(_bot_decision_cache.keys(), key=lambda k: _bot_decision_cache[k][0])[:MAX_CACHE_SIZE//2]
        for key in oldest_keys:
            del _bot_decision_cache[key]
    
    _bot_decision_cache[cache_key] = (current_time, target_direction)
    bot['target_direction'] = target_direction
    
    decision_delay = bot.get('reaction_delay', 100)
    base_cooldown = random.randint(80, 150)
    bot['decision_cooldown'] = current_time + base_cooldown + decision_delay
    
    update_bot_direction(bot)

def calculate_target_direction(bot, head, current_time):
    personality = bot['personality']
    
    if should_make_mistake(bot, current_time):
        return bot['direction'] + random.uniform(-math.pi/4, math.pi/4)
    
    target_player = find_hunting_target(bot, head)
    if target_player and random.random() < personality['chase_priority']:
        bot['target_player'] = target_player['name']
        bot['hunt_duration'] = current_time + random.randint(3000, 8000)
        return calculate_hunting_direction(bot, head, target_player)
    
    if bot.get('target_player') and current_time < bot.get('hunt_duration', 0):
        current_target = find_player_by_name(bot['target_player'])
        if current_target and current_target['alive']:
            target_distance = math.sqrt(distance_squared(head, current_target['snake'][0]))
            
            if (bot['bot_type'] in ['hunter', 'aggressive'] and 
                target_distance < 150 and bot['length'] > current_target['length']):
                bot['speed'] = 3.0
            else:
                bot['speed'] = 2.0
                
            return calculate_hunting_direction(bot, head, current_target)
    
    bot['target_player'] = None
    bot['speed'] = 2.0
    
    nearest_power = find_nearest_power_food_cached(head)
    if nearest_power and distance_squared(head, nearest_power) < 22500:
        return math.atan2(nearest_power['y'] - head['y'], nearest_power['x'] - head['x'])
    
    if bot['cached_nearby_food']:
        if bot['bot_type'] == 'collector':
            sorted_food = sorted(bot['cached_nearby_food'], key=lambda f: f.get('size', 5) * 2 - distance_squared(head, f) * 0.1)
            target_food = sorted_food[0] if sorted_food else bot['cached_nearby_food'][0]
        else:
            target_food = min(bot['cached_nearby_food'], key=lambda f: distance_squared(head, f))
        return math.atan2(target_food['y'] - head['y'], target_food['x'] - head['x'])
    
    exploration_chance = {
        'aggressive': 0.2,
        'hunter': 0.15,
        'defensive': 0.1,
        'collector': 0.25
    }.get(bot['bot_type'], 0.15)
    
    if random.random() < exploration_chance:
        if bot['bot_type'] == 'defensive':
            center_x, center_y = 1000, 1000
            to_center = math.atan2(center_y - head['y'], center_x - head['x'])
            return to_center + random.uniform(-math.pi/3, math.pi/3)
        else:
            return random.uniform(0, 2 * math.pi)
    
    return bot.get('target_direction', bot['direction'])

def should_make_mistake(bot, current_time):
    if current_time - bot.get('last_mistake', 0) > 2000:
        if random.random() < bot['mistake_chance']:
            bot['last_mistake'] = current_time
            return True
    return False

def find_hunting_target(bot, head):
    if bot['bot_type'] == 'defensive':
        return None
    
    hunting_range = bot['hunting_range']
    best_target = None
    best_score = 0
    
    all_targets = []
    
    for player in game_state['players'].values():
        if player['alive'] and player['snake']:
            all_targets.append(('player', player))
    
    if bot['bot_type'] in ['hunter', 'aggressive'] and bot['length'] > 12:
        for other_bot in game_state['bots'].values():
            if (other_bot['alive'] and other_bot['snake'] and 
                other_bot['id'] != bot['id'] and other_bot['length'] < bot['length'] - 3):
                all_targets.append(('bot', other_bot))
    
    for target_type, target in all_targets:
        target_head = target['snake'][0]
        distance = math.sqrt(distance_squared(head, target_head))
        
        if distance > hunting_range:
            continue
        
        size_advantage = bot['length'] - target['length']
        if size_advantage < -5:
            continue
        
        score = calculate_hunting_score(bot, target, distance, size_advantage)
        
        if target_type == 'player':
            score *= 1.5
        
        if score > best_score:
            best_score = score
            best_target = target
    
    return best_target

def calculate_hunting_score(bot, player, distance, size_advantage):
    score = 0
    
    score += size_advantage * 10
    score += player['score'] * 0.1
    score -= distance * 0.5
    
    if bot['bot_type'] == 'hunter':
        score *= 1.5
    elif bot['bot_type'] == 'aggressive':
        score *= 1.3
    
    if 'speed' in bot.get('powers', {}):
        score += 20
    
    if bot['personality']['risk_tolerance'] < 0.5 and size_advantage < 3:
        score *= 0.5
    
    return max(0, score)

def calculate_hunting_direction(bot, head, target):
    if not target['snake']:
        return bot['direction']
    
    target_head = target['snake'][0]
    
    if bot['bot_type'] == 'hunter':
        return calculate_intercept_direction(bot, head, target)
    else:
        direct_angle = math.atan2(target_head['y'] - head['y'], target_head['x'] - head['x'])
        noise = random.uniform(-0.3, 0.3)
        return direct_angle + noise

def calculate_intercept_direction(bot, head, target):
    if len(target['snake']) < 2:
        target_head = target['snake'][0]
        return math.atan2(target_head['y'] - head['y'], target_head['x'] - head['x'])
    
    target_head = target['snake'][0]
    target_neck = target['snake'][1]
    
    target_direction = math.atan2(target_head['y'] - target_neck['y'], target_head['x'] - target_neck['x'])
    target_speed = target.get('speed', 2.0)
    
    predict_time = 0.5
    predicted_x = target_head['x'] + math.cos(target_direction) * target_speed * predict_time * 16
    predicted_y = target_head['y'] + math.sin(target_direction) * target_speed * predict_time * 16
    
    return math.atan2(predicted_y - head['y'], predicted_x - head['x'])

def find_player_by_name(name):
    for player in game_state['players'].values():
        if player['name'] == name:
            return player
    return None

def update_bot_direction(bot):
    angle_diff = bot['target_direction'] - bot['direction']
    
    while angle_diff > math.pi:
        angle_diff -= 2 * math.pi
    while angle_diff < -math.pi:
        angle_diff += 2 * math.pi
    
    base_turn_rate = 0.12
    
    if bot['bot_type'] == 'hunter':
        max_turn_rate = base_turn_rate * 1.2
    elif bot['bot_type'] == 'aggressive':
        max_turn_rate = base_turn_rate * 1.1
    elif bot['bot_type'] == 'defensive':
        max_turn_rate = base_turn_rate * 0.8
    else:
        max_turn_rate = base_turn_rate
    
    if bot.get('target_player') and 'speed' in bot.get('powers', {}):
        max_turn_rate *= 1.3
    
    human_variance = random.uniform(0.8, 1.2)
    max_turn_rate *= human_variance
    
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
    
    border_threshold = 100
    if (future_x < border_threshold or future_x > 2000 - border_threshold or 
        future_y < border_threshold or future_y > 2000 - border_threshold):
        find_safe_direction_from_border(bot, head)
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
    
    if len(_pathfinding_cache) > MAX_CACHE_SIZE:
        oldest_keys = sorted(_pathfinding_cache.keys(), key=lambda k: _pathfinding_cache[k][0])[:MAX_CACHE_SIZE//2]
        for key in oldest_keys:
            del _pathfinding_cache[key]
    
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

def find_safe_direction_from_border(bot, head):
    center_x, center_y = 1000, 1000
    
    to_center_direction = math.atan2(center_y - head['y'], center_x - head['x'])
    
    potential_directions = [
        to_center_direction,
        to_center_direction + math.pi/6,
        to_center_direction - math.pi/6,
        to_center_direction + math.pi/3,
        to_center_direction - math.pi/3
    ]
    
    check_distance = 80
    
    for direction in potential_directions:
        test_x = head['x'] + math.cos(direction) * check_distance
        test_y = head['y'] + math.sin(direction) * check_distance
        
        if is_safe_direction_optimized(test_x, test_y, bot['id']):
            bot['target_direction'] = direction
            return
    
    bot['target_direction'] = to_center_direction

def is_safe_direction_optimized(x, y, bot_id):
    if x < 50 or x > 1950 or y < 50 or y > 1950:
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
    current_time = time.time() * 1000
    
    expired_decision_keys = [k for k, (cache_time, _) in _bot_decision_cache.items() if current_time - cache_time > 5000]
    for key in expired_decision_keys:
        del _bot_decision_cache[key]
    
    expired_pathfinding_keys = [k for k, (cache_time, _) in _pathfinding_cache.items() if current_time - cache_time > 5000]
    for key in expired_pathfinding_keys:
        del _pathfinding_cache[key]
    
    if len(_bot_decision_cache) > MAX_CACHE_SIZE * 2:
        _bot_decision_cache.clear()
    
    if len(_pathfinding_cache) > MAX_CACHE_SIZE * 2:
        _pathfinding_cache.clear()
