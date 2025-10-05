import os
import logging

from typing import Final
from collections.abc import Mapping, Sequence
import jwt
import time

type JSON = Mapping[str, JSON] | Sequence[JSON] | str | None | bool | float | int


class JWTHandler:
    def __init__(self, secret_key: str):
        self._key: Final[str] = secret_key
        self._algo: Final[str] = "HS256"

    def encode(self, payload: Mapping[str, JSON]) -> str:
        return jwt.encode(dict(payload), self._key, algorithm=self._algo)

    def decode(self, token: str) -> Mapping[str, JSON]:
        return jwt.decode(token, self._key, algorithms=[self._algo])  # pyright: ignore[reportAny]

    def verify(self, token: str) -> bool:
        try:
            jwt.decode(token, self._key, algorithms=[self._algo])
            return True
        except jwt.InvalidTokenError:
            return False

    def create_user(self, user_id: int, ttl: float = 86400) -> str:
        payload = {
            "nbt": time.time(),
            "iat": time.time(),
            "exp": time.time() + ttl,
            "issuer": "gamba_bot",
            "aud": [f"user:{user_id}"],
            "user_id": user_id,
        }
        return self.encode(payload)


jwt_handler = JWTHandler(os.environ["JWT_SECRET"])

def impersonate_user(user_id: int) -> str:
    return jwt_handler.create_user(user_id)

