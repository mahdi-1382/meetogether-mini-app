import hashlib
import hmac
import json
from urllib.parse import parse_qsl

from config import BOT_TOKEN

def validate_init_data(init_data: str):
    if not init_data or not BOT_TOKEN:
        return None
    try:
        pairs = dict(parse_qsl(init_data, keep_blank_values=True))
        received_hash = pairs.pop("hash", None)
        if not received_hash:
            return None
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
        secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
        calculated = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(calculated, received_hash):
            return None
        user_raw = pairs.get("user")
        return json.loads(user_raw) if user_raw else None
    except (ValueError, TypeError, json.JSONDecodeError):
        return None
