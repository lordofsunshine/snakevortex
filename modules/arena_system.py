import time
from .game_state import game_state, WORLD_WIDTH, WORLD_HEIGHT
from .utils import clamp

DEFAULT_SHRINK_DELAY_MS = 45000
DEFAULT_SHRINK_DURATION_MS = 120000
DEFAULT_MIN_SIZE = 750

def init_arena():
    if 'arena' in game_state:
        return
    now_ms = time.time() * 1000
    game_state['arena'] = {
        'start_time_ms': now_ms,
        'shrink_delay_ms': DEFAULT_SHRINK_DELAY_MS,
        'shrink_duration_ms': DEFAULT_SHRINK_DURATION_MS,
        'min_size': DEFAULT_MIN_SIZE,
        'active': False,
        'phase': 'static',
        'progress': 0.0,
        'min_x': 0.0,
        'min_y': 0.0,
        'max_x': float(WORLD_WIDTH),
        'max_y': float(WORLD_HEIGHT),
        'size': float(min(WORLD_WIDTH, WORLD_HEIGHT))
    }
    update_arena(now_ms)

def update_arena(now_ms):
    arena = game_state.get('arena')
    if not arena:
        init_arena()
        arena = game_state['arena']

    active_players = any(p.get('alive') for p in game_state.get('players', {}).values())
    if not active_players:
        arena['active'] = False
        arena['phase'] = 'static'
        arena['progress'] = 0.0
        arena['size'] = float(min(WORLD_WIDTH, WORLD_HEIGHT))
        arena['min_x'] = 0.0
        arena['min_y'] = 0.0
        arena['max_x'] = float(WORLD_WIDTH)
        arena['max_y'] = float(WORLD_HEIGHT)
        arena['start_time_ms'] = now_ms
        return

    if not arena.get('active'):
        arena['active'] = True
        arena['start_time_ms'] = now_ms

    start = arena.get('start_time_ms', now_ms)
    delay = arena.get('shrink_delay_ms', DEFAULT_SHRINK_DELAY_MS)
    duration = arena.get('shrink_duration_ms', DEFAULT_SHRINK_DURATION_MS)
    min_size = float(arena.get('min_size', DEFAULT_MIN_SIZE))

    full_size = float(min(WORLD_WIDTH, WORLD_HEIGHT))
    t = now_ms - (start + delay)

    if t <= 0:
        progress = 0.0
        phase = 'static'
    else:
        progress = clamp(t / max(1.0, float(duration)), 0.0, 1.0)
        phase = 'shrinking' if progress < 1.0 else 'final'

    size = full_size + (min_size - full_size) * progress
    cx = WORLD_WIDTH / 2.0
    cy = WORLD_HEIGHT / 2.0

    half = size / 2.0
    min_x = cx - half
    max_x = cx + half
    min_y = cy - half
    max_y = cy + half

    arena['phase'] = phase
    arena['progress'] = progress
    arena['size'] = size
    arena['min_x'] = float(min_x)
    arena['max_x'] = float(max_x)
    arena['min_y'] = float(min_y)
    arena['max_y'] = float(max_y)

def get_arena_bounds():
    arena = game_state.get('arena')
    if not arena:
        return 0.0, 0.0, float(WORLD_WIDTH), float(WORLD_HEIGHT)
    return arena['min_x'], arena['min_y'], arena['max_x'], arena['max_y']

def clamp_to_arena(x, y, margin=0.0):
    min_x, min_y, max_x, max_y = get_arena_bounds()
    return (
        clamp(x, min_x + margin, max_x - margin),
        clamp(y, min_y + margin, max_y - margin),
    )
