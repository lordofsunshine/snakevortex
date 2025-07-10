import asyncio
import json
import time
import copy
from .game_state import game_state, connected_clients, FOOD_COUNT, POWER_FOOD_COUNT, update_spatial_grid, get_cached_leaderboard
from .snake_logic import move_snake, grow_snake, apply_power_effects, clean_expired_powers
from .collision import check_collision, check_food_collision, check_power_food_collision, clear_collision_cache
from .food_system import generate_food, generate_power_food, create_death_food, animate_food_scaling, remove_consumed_food, remove_consumed_power_food, batch_generate_food, batch_generate_power_food
from .bot_ai import bot_ai, update_food_cache, clear_bot_caches, create_bot
from .utils import distance_squared

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
    
    update_spatial_grid()
    update_food_cache()
    
    await process_all_entities()
    
    animate_food_scaling()
    maintain_food_count()
    maintain_bot_count()
    
    if current_time % 10000 < 50:
        clear_collision_cache()
        clear_bot_caches()

async def process_all_entities():
    player_tasks = []
    bot_tasks = []
    
    for player_id, player in list(game_state['players'].items()):
        if player['alive']:
            player_tasks.append(process_player(player_id, player))
    
    for bot_id, bot in list(game_state['bots'].items()):
        if bot['alive']:
            bot_tasks.append(process_bot(bot_id, bot))
    
    if player_tasks or bot_tasks:
        await asyncio.gather(*(player_tasks + bot_tasks), return_exceptions=True)

async def process_player(player_id, player):
    try:
        if player['direction'] is not None:
            move_snake(player['snake'], player['direction'], player['speed'])
        
        if check_collision(player['snake'], player_id, 'player'):
            await kill_player(player_id, player)
            return
        
        consumed_food = check_food_collision(player['snake'], player_id)
        consumed_power = check_power_food_collision(player['snake'], player_id)
        
        if consumed_food:
            await process_food_consumption_for_entity(player, consumed_food)
        
        if consumed_power:
            await process_power_consumption_for_entity(player, consumed_power)
        
        apply_power_effects(player)
        clean_expired_powers(player)
        
    except Exception as e:
        print(f"Error processing player {player_id}: {e}")

async def process_bot(bot_id, bot):
    try:
        bot_ai(bot)
        
        if bot['direction'] is not None:
            move_snake(bot['snake'], bot['direction'], bot['speed'])
        
        if check_collision(bot['snake'], bot_id, 'bot'):
            await kill_bot(bot_id, bot)
            return
        
        consumed_food = check_food_collision(bot['snake'], bot_id)
        consumed_power = check_power_food_collision(bot['snake'], bot_id)
        
        if consumed_food:
            await process_food_consumption_for_entity(bot, consumed_food)
        
        if consumed_power:
            await process_power_consumption_for_entity(bot, consumed_power)
        
        apply_power_effects(bot)
        clean_expired_powers(bot)
        
    except Exception as e:
        print(f"Error processing bot {bot_id}: {e}")

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
    
    for _ in range(growth_amount):
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
    
    death_food = create_death_food(player['snake'], player['score'])
    game_state['food'].extend(death_food)
    
    player['snake'] = []
    player['powers'] = {}

async def kill_bot(bot_id, bot):
    bot['alive'] = False
    
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
            'leaderboard': leaderboard
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
