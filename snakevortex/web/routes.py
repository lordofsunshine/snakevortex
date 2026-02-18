import asyncio
import json

from quart import abort, render_template, request, websocket

from snakevortex.config import MAX_WS_MESSAGE_SIZE, MIN_MOVE_INTERVAL_MS, PING_INTERVAL_MS
from snakevortex.game.game_state import connected_clients
from snakevortex.web.player_service import PlayerService
from snakevortex.web.security import parse_client_message, parse_direction, parse_ping, sanitize_color, sanitize_name


def register_routes(app, rate_limiter, security_checker):
    player_service = PlayerService()

    async def send_error(message):
        await websocket.send(json.dumps({"type": "error", "message": message}))

    @app.route("/")
    async def index():
        client_ip = request.remote_addr
        if not rate_limiter.is_allowed(client_ip):
            abort(429)

        return await render_template("index.html")

    @app.after_request
    async def add_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com data:; "
            "img-src 'self' data: https:; "
            "connect-src 'self' ws: wss:; "
            "frame-ancestors 'none'"
        )
        return response

    @app.errorhandler(404)
    async def not_found(_error):
        return "Page not found", 404

    @app.errorhandler(429)
    async def rate_limit_exceeded(_error):
        return "Too many requests", 429

    @app.websocket("/ws")
    async def websocket_endpoint():
        if not security_checker(websocket.headers):
            return

        ws_client = websocket._get_current_object()
        connected_clients.add(ws_client)

        current_player_id = None
        last_move_ms = 0
        last_ping_ms = 0

        try:
            while True:
                raw_message = await websocket.receive()
                data = parse_client_message(raw_message, MAX_WS_MESSAGE_SIZE)
                if not data:
                    continue

                message_type = data.get("type")

                if message_type == "join":
                    if current_player_id:
                        player_service.remove_player(current_player_id, drop_food=False)

                    if not player_service.can_join():
                        await send_error("Server is full")
                        continue

                    name = sanitize_name(data.get("name", ""))
                    if not name:
                        await send_error("Invalid nickname")
                        continue

                    color = sanitize_color(data.get("color"))
                    current_player_id, unique_name = player_service.register_player(name, color)

                    await websocket.send(
                        json.dumps(
                            {
                                "type": "player_id",
                                "player_id": current_player_id,
                                "assigned_name": unique_name,
                            }
                        )
                    )
                    continue

                if message_type == "move":
                    direction = parse_direction(data.get("direction"))
                    if direction is None:
                        continue

                    accelerating = bool(data.get("accelerating", False))
                    last_move_ms = player_service.handle_move(
                        current_player_id,
                        direction,
                        accelerating,
                        last_move_ms,
                        MIN_MOVE_INTERVAL_MS,
                    )
                    continue

                if message_type == "ping":
                    ping_value = parse_ping(data.get("ping"))
                    last_ping_ms = player_service.handle_ping(
                        current_player_id,
                        ping_value,
                        last_ping_ms,
                        PING_INTERVAL_MS,
                    )
                    continue

        except asyncio.CancelledError:
            raise
        except Exception as exc:
            print(f"WebSocket error: {exc}")
        finally:
            connected_clients.discard(ws_client)
            player_service.remove_player(current_player_id, drop_food=True)
