import os
from typing import Dict

DEFAULT: Dict[str, str | None] = {}

if "emsi_client_id" in os.environ and "emsi_client_secret" in os.environ:
    DEFAULT = {
        "username": os.environ.get("emsi_client_id"),
        "password": os.environ.get("emsi_client_secret")
}

def credentials(username: str, password: str) -> None:
    global DEFAULT
    DEFAULT = {
        "username": username,
        "password": password
    }

    return None
