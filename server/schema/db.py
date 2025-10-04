from dataclasses import dataclass
from typing import Literal, Optional


@dataclass(frozen=True, eq=True)
class Coin:
    id: int
    unique_name: str
    name: str


@dataclass
class Account:
    id: int
    holder_id: int
    balance: dict[Coin, int]


@dataclass
class User:
    id: int
    holder_id: int
    accounts: list[Account]


@dataclass
class Reward:
    id: int
    reason: str


@dataclass
class Game:
    id: int
    server_secret: str
    client_secret: str
    user_win: bool


@dataclass
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
