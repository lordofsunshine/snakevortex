import asyncio
from pathlib import Path

from quart import Quart

from snakevortex.config import RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW
from snakevortex.game.arena_system import init_arena
from snakevortex.game.bot_ai import create_bot
from snakevortex.game.food_system import generate_food, generate_power_food
from snakevortex.game.game_loop import game_loop
from snakevortex.game.game_state import FOOD_COUNT, POWER_FOOD_COUNT, game_state
from snakevortex.web.routes import register_routes
from snakevortex.web.security import RateLimiter, is_same_origin


def initialize_game():
    init_arena()

    for _ in range(FOOD_COUNT):
        game_state["food"].append(generate_food())

    for _ in range(POWER_FOOD_COUNT):
        game_state["power_food"].append(generate_power_food())

    for _ in range(8):
        create_bot()


def create_app():
    base_dir = Path(__file__).resolve().parent.parent
    app = Quart(
        __name__,
        static_folder=str(base_dir / "static"),
        template_folder=str(base_dir / "templates"),
    )

    rate_limiter = RateLimiter(RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW)
    register_routes(app, rate_limiter, is_same_origin)

    @app.before_serving
    async def startup():
        initialize_game()
        asyncio.create_task(game_loop())

    return app
