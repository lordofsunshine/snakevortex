import random
import time
import uuid

from snakevortex.game.food_system import create_death_food
from snakevortex.game.game_state import INITIAL_SNAKE_LENGTH, MAX_PLAYERS, game_state
from snakevortex.game.snake_logic import create_snake
from snakevortex.game.utils import find_safe_spawn_position


class PlayerService:
    def can_join(self):
        return len(game_state["players"]) < MAX_PLAYERS

    def is_name_unique(self, name):
        lowered = name.lower()

        for player in game_state["players"].values():
            if player["name"].lower() == lowered:
                return False

        for bot in game_state["bots"].values():
            if bot["name"].lower() == lowered:
                return False

        return True

    def get_unique_name(self, base_name):
        if self.is_name_unique(base_name):
            return base_name

        for counter in range(1, 1000):
            candidate = f"{base_name}_{counter}"
            if self.is_name_unique(candidate):
                return candidate

        return f"{base_name}_{random.randint(1000, 9999)}"

    def register_player(self, name, color):
        player_id = str(uuid.uuid4())
        unique_name = self.get_unique_name(name)
        start_position = find_safe_spawn_position()
        now_ms = time.time() * 1000

        game_state["players"][player_id] = {
            "id": player_id,
            "name": unique_name,
            "snake": create_snake(start_position),
            "direction": None,
            "speed": 2.0,
            "desired_speed": 2.0,
            "score": 0,
            "length": INITIAL_SNAKE_LENGTH,
            "alive": True,
            "color": color,
            "powers": {},
            "ping": 0,
            "spawn_time_ms": now_ms,
            "spawn_duration_ms": 700,
            "spawn_protection": now_ms + 5000,
            "last_ping": time.time(),
        }

        return player_id, unique_name

    def remove_player(self, player_id, drop_food=True):
        if not player_id:
            return

        player = game_state["players"].get(player_id)
        if not player:
            return

        if drop_food and player.get("alive") and player.get("snake"):
            death_food = create_death_food(player["snake"], player.get("score", 0))
            game_state["food"].extend(death_food)

        del game_state["players"][player_id]

    def handle_move(self, player_id, direction, accelerating, last_move_ms, min_interval_ms):
        if not player_id:
            return last_move_ms

        now_ms = time.time() * 1000
        if now_ms - last_move_ms < min_interval_ms:
            return last_move_ms

        player = game_state["players"].get(player_id)
        if not player or not player.get("alive"):
            return now_ms

        player["direction"] = direction
        player["desired_speed"] = 3.0 if accelerating else 2.0
        player["last_ping"] = time.time()

        return now_ms

    def handle_ping(self, player_id, ping_value, last_ping_ms, min_interval_ms):
        if not player_id:
            return last_ping_ms

        now_ms = time.time() * 1000
        if now_ms - last_ping_ms < min_interval_ms:
            return last_ping_ms

        player = game_state["players"].get(player_id)
        if not player:
            return now_ms

        player["ping"] = ping_value
        player["last_ping"] = time.time()
        return now_ms
