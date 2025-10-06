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
            jwt.decode(token, self._key, algorithms=[self._algo], audience="use", issuer="gamba_bot")
            return True
        except jwt.InvalidTokenError:
            return False

    def create_user(self, user_id: int, ttl: float = 86400) -> str:
        payload = {
            "nbt": time.time(),
            "iat": time.time(),
            "exp": time.time() + ttl,
            "iss": "gamba_bot",
            "aud": [f"use"],
            "user_id": user_id,
        }
        return self.encode(payload)


jwt_handler = JWTHandler("fc49037adb858619b770dfcb89758a464027c7a0379dd0bc72d24f9c0bfe7fc622dc0fa4b7f52d0426688575d6b008aeea432d5487a0c90c9c8f32fb8625a3a3c9b7e755c4f671c2262ca2dfa86378f50a82ce50a5d8f23cd70ed0606d4f010f6e64887f70bb144df32987fd01c32a494e6f58958bf059a7c3e8dfe669bf0f58")

def impersonate_user(user_id: int) -> str:
    return jwt_handler.create_user(user_id)

print(impersonate_user(0))