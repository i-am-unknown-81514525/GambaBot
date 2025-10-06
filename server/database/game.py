from typing import Literal

from asqlite import ProxiedConnection
from schema.db import Account, Coin, GameInstance
from helper.db_helper import DB
from .transact import raw_force_transact, InsufficientBalanceError

from cryptography.hazmat.primitives.hashes import Hash, SHA3_512


def _acc_id(val: int | Account) -> int:
    return val if isinstance(val, int) else val.id


def _coin_id(val: int | Coin) -> int:
    return val if isinstance(val, int) else val.id


def _sha3_512_hex(data: str) -> str:
    h = Hash(SHA3_512())
    h.update(data.encode())
    return h.finalize().hex()


async def create_game_instance(conn: DB, game_id: str, secret: str) -> GameInstance:
    hash = _sha3_512_hex(f"{game_id}::{secret}")
    _ = await conn.execute(
        """
        INSERT INTO game_instance(game_id, game_secret, game_hash, is_used)
        VALUES (?,?,?,?)
        """,
        (game_id, secret, hash, False),
    )
    return GameInstance(game_id, secret, hash, False)


async def get_game_instance(conn: DB, game_id: str) -> GameInstance | None:
    row = await (
        await conn.execute(
            """
            SELECT game_id, game_secret, game_hash, is_used
            FROM game_instance
            WHERE game_id = ?
            """,
            (game_id,),
        )
    ).fetchone()
    if row is None:
        return None
    return GameInstance(
        game_id=str(row[0]),
        game_secret=str(row[1]),
        game_hash=str(row[2]),
        is_used=bool(row[3]),
    )


async def mark_game_instance_completed(
    conn: DB,
    game_id: str,
    *,
    fail_if_already_used: bool = True,
) -> GameInstance:
    row = await (
        await conn.execute(
            """
            SELECT game_id, game_secret, game_hash, is_used
            FROM game_instance
            WHERE game_id = ?
            """,
            (game_id,),
        )
    ).fetchone()

    if row is None:
        raise ValueError(f"Game instance '{game_id}' not found")

    gid, secret, ghash, is_used = str(row[0]), str(row[1]), str(row[2]), bool(row[3])

    if is_used:
        if fail_if_already_used:
            raise ValueError(f"Game instance '{game_id}' is already marked as used")
        return GameInstance(
            game_id=gid, game_secret=secret, game_hash=ghash, is_used=True
        )

    _ = await conn.execute(
        "UPDATE game_instance SET is_used = 1 WHERE game_id = ?",
        (game_id,),
    )

    return GameInstance(game_id=gid, game_secret=secret, game_hash=ghash, is_used=True)
