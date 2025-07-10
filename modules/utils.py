import math
import random
import time
from .game_state import game_state, WORLD_WIDTH, WORLD_HEIGHT

def distance_squared(pos1, pos2):
    dx = pos1['x'] - pos2['x']
    dy = pos1['y'] - pos2['y']
    return dx * dx + dy * dy

def distance(pos1, pos2):
    return math.sqrt(distance_squared(pos1, pos2))

def find_safe_spawn_position():
    max_attempts = 50
    min_distance = 150
    
    for _ in range(max_attempts):
        position = {
            'x': random.randint(100, WORLD_WIDTH - 100),
            'y': random.randint(100, WORLD_HEIGHT - 100)
        }
        
        if is_position_safe(position, min_distance):
            return position
    
    return {
        'x': random.randint(100, WORLD_WIDTH - 100),
        'y': random.randint(100, WORLD_HEIGHT - 100)
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

def lerp(start, end, factor):
    return start + (end - start) * factor

def get_random_color():
    colors = ['#ff6b6b', '#4ecdc4', '#45b7d1', '#f9ca24', '#f0932b', '#eb4d4b', '#6c5ce7', '#a29bfe']
    return random.choice(colors)

def format_time(milliseconds):
    seconds = milliseconds // 1000
    minutes = seconds // 60
    seconds = seconds % 60
    return f"{minutes}:{seconds:02d}"

def calculate_score(length, time_alive):
    base_score = (length - 4) * 10
    time_bonus = time_alive // 1000
    return base_score + time_bonus
