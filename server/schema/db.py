from dataclasses import dataclass
from typing import Literal, Optional


@dataclass(frozen=True, eq=True)
class Coin:
    id: int
    unique_name: str
    name: str


@dataclass(frozen=True)
class Account:
    id: int
    holder_id: int
    balance: dict[Coin, int]


@dataclass(frozen=True)
class User:
    id: int
    holder_id: int
    accounts: list[Account]


@dataclass(frozen=True)
class Reward:
    id: int
    reason: str


@dataclass(frozen=True)
class Game:
    id: int
    server_secret: str
    client_secret: str
    user_win: bool


@dataclass(frozen=True)
class Transaction:
    id: int
    src: int
    dst: int
    coin_id: int
    coin_unique_name: str
    coin_read_name: str
    amount: int
    kind: Literal["none", "reward", "game"]
    reason: str
    inner_hash: str
    create_dt: str
    transact_data: str
    reward: Optional[Reward]
    game: Optional[Game]


@dataclass(frozen=True)
class GameInstance:
    game_id: str
    game_secret: str
    game_hash: str
    is_used: bool
