import math
import random
import time
import uuid
from .game_state import game_state, INITIAL_SNAKE_LENGTH, get_nearby_cells
from .snake_logic import create_snake
from .utils import find_safe_spawn_position, distance_squared, normalize_angle

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
_danger_cache = {'bucket': -1, 'data': {}}
MAX_CACHE_SIZE = 1000

def _get_arena_bounds():
    arena = game_state.get('arena')
    if arena and all(k in arena for k in ('min_x', 'min_y', 'max_x', 'max_y')):
        return arena['min_x'], arena['min_y'], arena['max_x'], arena['max_y']
    return 0, 0, 2000, 2000

def _get_arena_center():
    min_x, min_y, max_x, max_y = _get_arena_bounds()
    return (min_x + max_x) / 2.0, (min_y + max_y) / 2.0

def _arena_phase():
    arena = game_state.get('arena', {})
    return arena.get('phase', 'static')

def _arena_time_to_shrink_ms(now_ms):
    arena = game_state.get('arena', {})
    start = arena.get('start_time_ms')
    delay = arena.get('shrink_delay_ms')
    if start is None or delay is None:
        return None
    return (start + delay) - now_ms

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
    now_ms = time.time() * 1000
    spawn_delay = random.randint(250, 1600)
    
    bot_type = random.choice(['aggressive', 'hunter', 'defensive', 'collector'])
    personality = generate_personality(bot_type)
    
    bot = {
        'id': bot_id,
        'name': get_unique_bot_name(),
        'snake': create_snake(start_pos),
        'direction': random.uniform(0, 2 * math.pi),
        'target_direction': random.uniform(0, 2 * math.pi),
        'speed': 2.0,
        'desired_speed': 2.0,
        'score': 0,
        'length': INITIAL_SNAKE_LENGTH,
        'alive': True,
        'color': f"#{random.randint(100, 255):02x}{random.randint(100, 255):02x}{random.randint(100, 255):02x}",
        'powers': {},
        'spawn_time_ms': now_ms + spawn_delay,
        'spawn_duration_ms': 900,
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
        'hunting_range': personality['hunt_range'],
        'intent': {'type': 'roam', 'until_ms': 0, 'target': None},
        'intent_seed': random.random(),
        'last_intent_change': 0
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
            'risk_tolerance': 0.9,
            'commitment_ms': random.randint(700, 1300),
            'arena_awareness': 0.8,
            'food_focus': 0.4,
            'power_focus': 0.6
        },
        'hunter': {
            'hunt_range': 400,
            'chase_priority': 0.9,
            'mistake_rate': 0.03,
            'reaction_time': random.randint(30, 100),
            'risk_tolerance': 0.7,
            'commitment_ms': random.randint(900, 1600),
            'arena_awareness': 0.9,
            'food_focus': 0.35,
            'power_focus': 0.7
        },
        'defensive': {
            'hunt_range': 150,
            'chase_priority': 0.3,
            'mistake_rate': 0.08,
            'reaction_time': random.randint(100, 250),
            'risk_tolerance': 0.3,
            'commitment_ms': random.randint(1100, 1900),
            'arena_awareness': 1.0,
            'food_focus': 0.7,
            'power_focus': 0.5
        },
        'collector': {
            'hunt_range': 200,
            'chase_priority': 0.4,
            'mistake_rate': 0.06,
            'reaction_time': random.randint(80, 200),
            'risk_tolerance': 0.5,
            'commitment_ms': random.randint(900, 1600),
            'arena_awareness': 0.9,
            'food_focus': 0.85,
            'power_focus': 0.65
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
        bot['cached_nearby_food'] = get_nearby_food_spatial(head, 220)
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

    intent = bot.get('intent')
    if not intent or current_time >= intent.get('until_ms', 0):
        bot['intent'] = choose_intent(bot, head, current_time)
        intent = bot['intent']
    
    target_player = find_hunting_target(bot, head)
    if target_player and random.random() < personality['chase_priority']:
        bot['target_player'] = target_player['name']
        bot['hunt_duration'] = current_time + random.randint(3000, 8000)
        bot['intent'] = {'type': 'hunt', 'until_ms': current_time + min(2500, personality.get('commitment_ms', 1200)), 'target': target_player['name']}
        return plan_direction(bot, head, current_time, bot['intent'])
    
    if bot.get('target_player') and current_time < bot.get('hunt_duration', 0):
        current_target = find_player_by_name(bot['target_player'])
        if current_target and current_target['alive']:
            target_distance = math.sqrt(distance_squared(head, current_target['snake'][0]))
            
            if (bot['bot_type'] in ['hunter', 'aggressive'] and 
                target_distance < 150 and bot['length'] > current_target['length']):
                bot['desired_speed'] = 3.0
                bot['speed'] = 3.0
            else:
                bot['desired_speed'] = 2.0
                bot['speed'] = 2.0
                
            return plan_direction(bot, head, current_time, {'type': 'hunt', 'until_ms': bot.get('hunt_duration', current_time + 1000), 'target': bot['target_player']})
    
    bot['target_player'] = None
    bot['desired_speed'] = 2.0
    bot['speed'] = 2.0

    dense_target = pick_dense_food_target(bot, head, bot.get('cached_nearby_food', []))
    if dense_target and (intent.get('type') not in ('return_safe', 'hunt')):
        bot['intent'] = {'type': 'food', 'until_ms': current_time + min(900, personality.get('commitment_ms', 1200)), 'target': {'x': dense_target['x'], 'y': dense_target['y']}}
        intent = bot['intent']

    return plan_direction(bot, head, current_time, intent)

def choose_intent(bot, head, now_ms):
    personality = bot['personality']
    min_x, min_y, max_x, max_y = _get_arena_bounds()
    center_x, center_y = _get_arena_center()

    dist_left = head['x'] - min_x
    dist_right = max_x - head['x']
    dist_top = head['y'] - min_y
    dist_bottom = max_y - head['y']
    dist_to_edge = min(dist_left, dist_right, dist_top, dist_bottom)

    phase = _arena_phase()
    time_to_shrink = _arena_time_to_shrink_ms(now_ms)

    urgent_margin = 120 if phase == 'shrinking' else 85
    if time_to_shrink is not None and time_to_shrink < 7000:
        urgent_margin = 130

    if dist_to_edge < urgent_margin:
        return {'type': 'return_safe', 'until_ms': now_ms + personality.get('commitment_ms', 1200), 'target': {'x': center_x, 'y': center_y}}

    nearest_power = find_nearest_power_food_cached(head)
    if nearest_power and distance_squared(head, nearest_power) < 80000:
        return {'type': 'power', 'until_ms': now_ms + personality.get('commitment_ms', 1200), 'target': {'x': nearest_power['x'], 'y': nearest_power['y']}}

    if bot.get('cached_nearby_food'):
        target_food = pick_food_target(bot, head, bot['cached_nearby_food'])
        if target_food:
            return {'type': 'food', 'until_ms': now_ms + personality.get('commitment_ms', 1200), 'target': {'x': target_food['x'], 'y': target_food['y']}}

    roam_bias = (bot.get('intent_seed', 0.5) - 0.5) * 0.4
    to_center = math.atan2(center_y - head['y'], center_x - head['x'])
    return {'type': 'roam', 'until_ms': now_ms + personality.get('commitment_ms', 1200), 'target': {'angle': to_center + roam_bias}}

def plan_direction(bot, head, now_ms, intent):
    intent_type = intent.get('type', 'roam')
    base_direction = bot.get('target_direction', bot['direction'])

    if intent_type == 'hunt':
        target = find_player_by_name(intent.get('target')) or find_bot_by_name(intent.get('target'))
        if target and target.get('alive') and target.get('snake'):
            base_direction = calculate_hunting_direction(bot, head, target)

    elif intent_type in ('return_safe', 'power', 'food'):
        target_pos = intent.get('target') or {}
        if 'x' in target_pos and 'y' in target_pos:
            base_direction = math.atan2(target_pos['y'] - head['y'], target_pos['x'] - head['x'])

    elif intent_type == 'roam':
        angle = (intent.get('target') or {}).get('angle')
        if angle is not None:
            base_direction = angle

    candidate_directions = build_candidate_directions(bot, base_direction)
    best_direction = select_best_direction(bot, head, now_ms, intent, candidate_directions)
    return best_direction

def pick_food_target(bot, head, foods):
    if not foods:
        return None
    if bot['bot_type'] == 'collector':
        return max(foods, key=lambda f: (f.get('size', 5) * 3.0) - (distance_squared(head, f) * 0.02))
    return min(foods, key=lambda f: distance_squared(head, f))

def pick_dense_food_target(bot, head, foods, radius=220, min_count=6, min_total=30.0):
    if not foods:
        return None
    radius_sq = radius * radius
    total = 0.0
    count = 0
    close_foods = []
    for food in foods:
        if distance_squared(head, food) <= radius_sq:
            close_foods.append(food)
            count += 1
            total += float(food.get('size', 5))
    if not close_foods:
        return None
    if count < min_count and total < min_total:
        return None
    return pick_food_target(bot, head, close_foods)

def build_candidate_directions(bot, base_direction):
    offsets = [-math.pi/2, -math.pi/3, -math.pi/4, -math.pi/6, -math.pi/12, 0, math.pi/12, math.pi/6, math.pi/4, math.pi/3, math.pi/2]
    candidates = []
    for off in offsets:
        candidates.append(base_direction + off)
    candidates.append(bot['direction'])
    candidates.append(base_direction + math.pi)
    return candidates

def select_best_direction(bot, head, now_ms, intent, candidates):
    scored = []
    for direction in candidates:
        scored.append((score_direction(bot, head, now_ms, intent, direction), direction))
    scored.sort(key=lambda x: x[0], reverse=True)
    if not scored:
        return bot.get('target_direction', bot['direction'])

    if random.random() < bot['mistake_chance'] * 0.35 and len(scored) > 1:
        return scored[min(2, len(scored) - 1)][1]
    return scored[0][1]

def score_direction(bot, head, now_ms, intent, direction):
    min_x, min_y, max_x, max_y = _get_arena_bounds()
    center_x, center_y = _get_arena_center()

    dx = math.cos(direction)
    dy = math.sin(direction)

    speed = float(bot.get('desired_speed', bot.get('speed', 2.0)))
    lookahead = 5
    step = max(14.0, speed * 14.0)

    risk = bot['personality'].get('risk_tolerance', 0.5)
    arena_awareness = bot['personality'].get('arena_awareness', 0.9)
    phase = _arena_phase()

    margin = 55.0 + (1.0 - risk) * 35.0
    if phase == 'shrinking':
        margin += 40.0 * arena_awareness

    score = 0.0

    turn_cost = abs(normalize_angle(direction - bot['direction']))
    score -= turn_cost * 14.0

    for i in range(1, lookahead + 1):
        px = head['x'] + dx * step * i
        py = head['y'] + dy * step * i

        if px < min_x or px > max_x or py < min_y or py > max_y:
            return -1e9

        edge_dist = min(px - min_x, max_x - px, py - min_y, max_y - py)
        if edge_dist < margin:
            score -= (margin - edge_dist) * (7.0 + 6.0 * arena_awareness)

        danger = collision_danger(px, py, bot['id'], now_ms)
        if danger > 0:
            score -= danger * (11.0 + (1.0 - risk) * 9.0)

    intent_type = intent.get('type', 'roam')

    if intent_type in ('food', 'roam'):
        score += food_attraction_score(head, direction, bot.get('cached_nearby_food', [])) * bot['personality'].get('food_focus', 0.6)

    if intent_type in ('power', 'roam'):
        power_target = find_nearest_power_food_cached(head)
        if power_target:
            score += target_alignment_score(head, direction, power_target) * 55.0 * bot['personality'].get('power_focus', 0.6)

    if intent_type == 'return_safe':
        score += target_alignment_score(head, direction, {'x': center_x, 'y': center_y}) * 65.0

    if intent_type == 'hunt':
        target_name = intent.get('target')
        target = find_player_by_name(target_name) or find_bot_by_name(target_name)
        if target and target.get('alive') and target.get('snake'):
            score += target_alignment_score(head, direction, target['snake'][0]) * 70.0

    time_to_shrink = _arena_time_to_shrink_ms(now_ms)
    if time_to_shrink is not None and time_to_shrink < 8000:
        score += target_alignment_score(head, direction, {'x': center_x, 'y': center_y}) * 35.0

    score += random.uniform(-1.3, 1.3)
    return score

def collision_danger(x, y, bot_id, now_ms=None):
    if now_ms is None:
        now_ms = time.time() * 1000
    bucket = int(now_ms // 80)
    if _danger_cache['bucket'] != bucket:
        _danger_cache['bucket'] = bucket
        _danger_cache['data'] = {}
    key = (bot_id, int(x // 40), int(y // 40))
    cached = _danger_cache['data'].get(key)
    if cached is not None:
        return cached

    nearby_cells = get_nearby_cells(x, y)
    test_pos = {'x': x, 'y': y}
    closest = None
    for cell in nearby_cells:
        for _, entity_id, segment in game_state['spatial_grid'].get(cell, []):
            if entity_id == bot_id:
                continue
            d = distance_squared(test_pos, segment)
            if closest is None or d < closest:
                closest = d
                if closest < 225:
                    _danger_cache['data'][key] = 3.0
                    return 3.0
    if closest is None:
        _danger_cache['data'][key] = 0.0
        return 0.0
    if closest < 625:
        _danger_cache['data'][key] = 2.0
        return 2.0
    if closest < 1225:
        _danger_cache['data'][key] = 1.0
        return 1.0
    _danger_cache['data'][key] = 0.0
    return 0.0

def target_alignment_score(head, direction, target_pos):
    vx = target_pos['x'] - head['x']
    vy = target_pos['y'] - head['y']
    dist_sq = vx * vx + vy * vy
    if dist_sq <= 1e-6:
        return 0.0
    dist = math.sqrt(dist_sq)
    vx /= dist
    vy /= dist
    dx = math.cos(direction)
    dy = math.sin(direction)
    dot = dx * vx + dy * vy
    return max(0.0, dot) / (1.0 + dist * 0.002)

def food_attraction_score(head, direction, foods):
    if not foods:
        return 0.0
    dx = math.cos(direction)
    dy = math.sin(direction)
    best = 0.0
    for food in foods:
        vx = food['x'] - head['x']
        vy = food['y'] - head['y']
        dist_sq = vx * vx + vy * vy
        if dist_sq <= 1e-6:
            continue
        dist = math.sqrt(dist_sq)
        vx /= dist
        vy /= dist
        dot = dx * vx + dy * vy
        if dot <= 0:
            continue
        value = float(food.get('size', 5))
        s = (value * 10.0) * dot / (1.0 + dist * 0.015)
        if s > best:
            best = s
    return best

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

def find_bot_by_name(name):
    for bot in game_state['bots'].values():
        if bot['name'] == name:
            return bot
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

    cell_radius = max(1, int(math.ceil(radius / 100)))
    for dx in range(-cell_radius, cell_radius + 1):
        for dy in range(-cell_radius, cell_radius + 1):
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
    min_x, min_y, max_x, max_y = _get_arena_bounds()
    if (future_x < min_x + border_threshold or future_x > max_x - border_threshold or 
        future_y < min_y + border_threshold or future_y > max_y - border_threshold):
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
    center_x, center_y = _get_arena_center()
    
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
    min_x, min_y, max_x, max_y = _get_arena_bounds()
    if x < min_x + 25 or x > max_x - 25 or y < min_y + 25 or y > max_y - 25:
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
