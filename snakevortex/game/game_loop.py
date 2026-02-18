import asyncio
import json
import time
from .game_state import game_state, connected_clients, FOOD_COUNT, POWER_FOOD_COUNT, update_spatial_grid, get_cached_leaderboard
from .snake_logic import move_snake, grow_snake, apply_power_effects, clean_expired_powers, update_entity_speed
from .collision import check_collision, check_food_collision, check_power_food_collision
from .food_system import generate_food, generate_power_food, create_death_food, animate_food_scaling, remove_consumed_food, remove_consumed_power_food, batch_generate_food, batch_generate_power_food
from .bot_ai import bot_ai, update_food_cache, clear_bot_caches, create_bot
from .arena_system import update_arena

FRAME_TIME = 1000 / 60
last_frame_time = 0
last_bot_check = 0

async def game_loop():
    global last_frame_time
    
    while True:
        current_time = time.time() * 1000
        
        if current_time - last_frame_time >= FRAME_TIME:
            try:
                await update_game_state()
                await broadcast_game_state()
                last_frame_time = current_time
            except Exception as e:
                print(f"Game loop error: {e}")
        
        await asyncio.sleep(0.005)

async def update_game_state():
    current_time = time.time() * 1000
    
    update_arena(current_time)
    if not game_state['spatial_grid']:
        update_spatial_grid()
    update_food_cache()

    await move_all_entities(current_time)
    update_spatial_grid()
    await resolve_collisions_and_consumptions(current_time)
    cull_items_outside_arena()
    
    animate_food_scaling()
    maintain_food_count()
    maintain_bot_count()
    
    if current_time % 10000 < 50:
        clear_bot_caches()
        cleanup_inactive_players()
        cleanup_dead_entities()

async def move_all_entities(current_time):
    for _, player in list(game_state['players'].items()):
        if not player.get('alive'):
            continue
        spawn_time = player.get('spawn_time_ms')
        if spawn_time is not None and current_time < spawn_time:
            continue
        update_entity_speed(player, current_time)
        if player.get('direction') is not None:
            move_snake(player['snake'], player['direction'], player['speed'])

    for _, bot in list(game_state['bots'].items()):
        if not bot.get('alive'):
            continue
        spawn_time = bot.get('spawn_time_ms')
        if spawn_time is not None and current_time < spawn_time:
            continue
        bot_ai(bot)
        update_entity_speed(bot, current_time)
        if bot.get('direction') is not None:
            move_snake(bot['snake'], bot['direction'], bot['speed'])

async def resolve_collisions_and_consumptions(current_time):
    to_kill_players = []
    to_kill_bots = []

    for player_id, player in list(game_state['players'].items()):
        if not player.get('alive'):
            continue
        spawn_time = player.get('spawn_time_ms')
        if spawn_time is not None and current_time < spawn_time:
            continue
        if check_collision(player.get('snake', []), player_id, 'player'):
            to_kill_players.append((player_id, player))

    for bot_id, bot in list(game_state['bots'].items()):
        if not bot.get('alive'):
            continue
        spawn_time = bot.get('spawn_time_ms')
        if spawn_time is not None and current_time < spawn_time:
            continue
        if check_collision(bot.get('snake', []), bot_id, 'bot'):
            to_kill_bots.append((bot_id, bot))

    for player_id, player in to_kill_players:
        if player.get('alive'):
            await kill_player(player_id, player)

    for bot_id, bot in to_kill_bots:
        if bot.get('alive'):
            await kill_bot(bot_id, bot)

    for _, player in list(game_state['players'].items()):
        if not player.get('alive'):
            continue
        spawn_time = player.get('spawn_time_ms')
        if spawn_time is not None and current_time < spawn_time:
            continue
        consumed_food = check_food_collision(player['snake'], player['id'])
        consumed_power = check_power_food_collision(player['snake'], player['id'])

        if consumed_food:
            await process_food_consumption_for_entity(player, consumed_food)

        if consumed_power:
            await process_power_consumption_for_entity(player, consumed_power)

        apply_power_effects(player)
        clean_expired_powers(player)

    for _, bot in list(game_state['bots'].items()):
        if not bot.get('alive'):
            continue
        spawn_time = bot.get('spawn_time_ms')
        if spawn_time is not None and current_time < spawn_time:
            continue
        consumed_food = check_food_collision(bot['snake'], bot['id'])
        consumed_power = check_power_food_collision(bot['snake'], bot['id'])

        if consumed_food:
            await process_food_consumption_for_entity(bot, consumed_food)

        if consumed_power:
            await process_power_consumption_for_entity(bot, consumed_power)

        apply_power_effects(bot)
        clean_expired_powers(bot)

def cull_items_outside_arena():
    arena = game_state.get('arena')
    if not arena:
        return
    if not all(k in arena for k in ('min_x', 'min_y', 'max_x', 'max_y')):
        return

    min_x = float(arena['min_x'])
    min_y = float(arena['min_y'])
    max_x = float(arena['max_x'])
    max_y = float(arena['max_y'])

    margin = 20.0
    game_state['food'] = [f for f in game_state['food'] if (f.get('scale', 1.0) > 0) and (min_x - margin <= f['x'] <= max_x + margin) and (min_y - margin <= f['y'] <= max_y + margin)]
    game_state['power_food'] = [p for p in game_state['power_food'] if (p.get('scale', 1.0) > 0) and (min_x - margin <= p['x'] <= max_x + margin) and (min_y - margin <= p['y'] <= max_y + margin)]

async def process_food_consumption_for_entity(entity, consumed_indices):
    if not consumed_indices:
        return
    
    growth_amount = 0
    score_gain = 0
    
    for index in consumed_indices:
        if 0 <= index < len(game_state['food']):
            food = game_state['food'][index]
            base_value = food.get('size', 5)
            
            if 'double_score' in entity.get('powers', {}):
                score_gain += base_value * 2
            else:
                score_gain += base_value
            
            growth_amount += 1
    
    entity['score'] += score_gain
    entity['length'] += growth_amount

    segment_multiplier = 1
    if entity['length'] >= 300:
        segment_multiplier = 3
    elif entity['length'] >= 150:
        segment_multiplier = 2

    growth_segments = growth_amount * segment_multiplier
    for _ in range(growth_segments):
        grow_snake(entity['snake'])
    
    remove_consumed_food(consumed_indices)

async def process_power_consumption_for_entity(entity, consumed_indices):
    if not consumed_indices:
        return
    
    current_time = time.time() * 1000
    
    for index in consumed_indices:
        if 0 <= index < len(game_state['power_food']):
            power = game_state['power_food'][index]
            power_type = power.get('type', 'speed')
            duration = power.get('duration', 5000)
            
            entity['powers'][power_type] = current_time + duration
            entity['score'] += 20
    
    remove_consumed_power_food(consumed_indices)

async def kill_player(player_id, player):
    player['alive'] = False
    player['death_time'] = time.time() * 1000
    
    death_food = create_death_food(player['snake'], player['score'])
    game_state['food'].extend(death_food)
    
    player['snake'] = []
    player['powers'] = {}

async def kill_bot(bot_id, bot):
    bot['alive'] = False
    bot['death_time'] = time.time() * 1000
    
    death_food = create_death_food(bot['snake'], bot['score'])
    game_state['food'].extend(death_food)
    
    bot['snake'] = []
    bot['powers'] = {}

def maintain_food_count():
    current_food = len([f for f in game_state['food'] if f.get('scale', 1.0) > 0])
    current_power = len([p for p in game_state['power_food'] if p.get('scale', 1.0) > 0])
    
    if current_food < FOOD_COUNT:
        needed = FOOD_COUNT - current_food
        new_food = batch_generate_food(needed)
        game_state['food'].extend(new_food)
    
    if current_power < POWER_FOOD_COUNT:
        needed = POWER_FOOD_COUNT - current_power
        new_power = batch_generate_power_food(needed)
        game_state['power_food'].extend(new_power)

def maintain_bot_count():
    global last_bot_check
    current_time = time.time() * 1000
    
    if current_time - last_bot_check < 5000:
        return
    
    alive_bots = sum(1 for bot in game_state['bots'].values() if bot['alive'])
    
    if alive_bots < 8:
        for _ in range(8 - alive_bots):
            create_bot()
    
    last_bot_check = current_time

async def broadcast_game_state():
    if not connected_clients:
        return
    
    try:
        leaderboard = get_cached_leaderboard()
        
        message = {
            'type': 'game_state',
            'players': game_state['players'],
            'bots': game_state['bots'],
            'food': game_state['food'],
            'power_food': game_state['power_food'],
            'leaderboard': leaderboard,
            'arena': game_state.get('arena')
        }
        
        message_json = json.dumps(message)
        clients_copy = connected_clients.copy()
        
        tasks = []
        for client in clients_copy:
            tasks.append(send_to_client(client, message_json))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    except Exception as e:
        print(f"Broadcast error: {e}")

async def send_to_client(client, message):
    try:
        await client.send(message)
    except Exception as e:
        connected_clients.discard(client)

def cleanup_inactive_players():
    current_time = time.time()
    inactive_players = []
    
    for player_id, player in game_state['players'].items():
        if 'last_ping' in player and current_time - player['last_ping'] > 30:
            inactive_players.append(player_id)
    
    for player_id in inactive_players:
        if player_id in game_state['players']:
            player = game_state['players'][player_id]
            if player['alive']:
                death_food = create_death_food(player['snake'], player['score'])
                game_state['food'].extend(death_food)
            del game_state['players'][player_id]

def cleanup_dead_entities():
    current_time = time.time() * 1000
    
    dead_players = [pid for pid, player in game_state['players'].items() 
                   if not player['alive'] and current_time - player.get('death_time', current_time) > 60000]
    for pid in dead_players:
        del game_state['players'][pid]
    
    dead_bots = [bid for bid, bot in game_state['bots'].items() 
                if not bot['alive'] and current_time - bot.get('death_time', current_time) > 60000]
    for bid in dead_bots:
        del game_state['bots'][bid]
    
    game_state['food'] = [f for f in game_state['food'] 
                         if f.get('scale', 1.0) > 0.1 or current_time - f.get('created_at', current_time) < 120000]
    
    game_state['power_food'] = [p for p in game_state['power_food'] 
                               if p.get('scale', 1.0) > 0.1]
    
    if len(game_state['food']) > FOOD_COUNT * 3:
        game_state['food'] = game_state['food'][-FOOD_COUNT * 2:]
    
    if len(game_state['power_food']) > POWER_FOOD_COUNT * 3:
        game_state['power_food'] = game_state['power_food'][-POWER_FOOD_COUNT * 2:]
