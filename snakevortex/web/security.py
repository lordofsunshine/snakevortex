import json
import math
import re
import time
from collections import defaultdict

from snakevortex.config import DEFAULT_PLAYER_COLOR

HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


class RateLimiter:
    def __init__(self, requests_limit, window_seconds):
        self.requests_limit = requests_limit
        self.window_seconds = window_seconds
        self.storage = defaultdict(list)

    def is_allowed(self, client_ip):
        if not client_ip:
            return True

        current_time = time.time()
        requests = self.storage[client_ip]
        requests[:] = [value for value in requests if current_time - value < self.window_seconds]

        if len(requests) >= self.requests_limit:
            return False

        requests.append(current_time)

        if len(self.storage) > 1000:
            stale_ips = [
                ip
                for ip, values in self.storage.items()
                if not values or current_time - max(values) > self.window_seconds * 2
            ]
            for ip in stale_ips[:500]:
                del self.storage[ip]

        return True


def is_same_origin(headers):
    origin = headers.get("Origin")
    if not origin:
        return True

    host = headers.get("Host")
    if not host:
        return False

    return origin.startswith(f"http://{host}") or origin.startswith(f"https://{host}")


def sanitize_name(name):
    if not isinstance(name, str):
        return ""

    cleaned = []
    for char in name.strip():
        if char.isalnum() or char in " _-":
            cleaned.append(char)
    return "".join(cleaned)[:15].strip()


def sanitize_color(color):
    if isinstance(color, str) and HEX_COLOR_RE.match(color):
        return color
    return DEFAULT_PLAYER_COLOR


def parse_direction(value):
    try:
        direction = float(value)
    except Exception:
        return None

    if not math.isfinite(direction):
        return None

    return direction % (2 * math.pi)


def parse_ping(value):
    try:
        ping = int(value)
    except Exception:
        return 0

    return max(0, min(5000, ping))


def parse_client_message(message, max_size):
    if not isinstance(message, str) or len(message) > max_size:
        return None

    try:
        payload = json.loads(message)
    except Exception:
        return None

    if not isinstance(payload, dict):
        return None

    message_type = payload.get("type")
    if not isinstance(message_type, str):
        return None

    return payload
