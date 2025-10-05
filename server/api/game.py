from dataclasses import dataclass
from random import Random
import secrets
from typing import Annotated
import uuid

from fastapi import FastAPI, APIRouter, Depends, HTTPException
from database.account import get_raw_user_account
from helper.jwt_helper import get_user
from helper.db_helper import DB, get_tx_conn

from database.game import (
    create_game_instance,
    get_game_instance,
    mark_game_instance_completed,
)
from database.holder import (
    game_force_transfer_holder_to_system,
    get_holder_coin_balance,
)
from database.transact import game_force_transfer, get_transaction_by_uni_id
from database.user import get_user as get_db_user

from cryptography.hazmat.primitives.hashes import Hash, SHA3_512

from schema.db import GameInstance, Transaction

game_app = FastAPI()

protected_router = APIRouter(dependencies=[Depends(get_user)])


def _sha3_512_hex(data: str) -> str:
    h = Hash(SHA3_512())
    h.update(data.encode())
    return h.finalize().hex()


def generate_run_secret(server_secret: str, client_secret: str) -> str:
    return _sha3_512_hex(f"{server_secret}::{client_secret}")


@dataclass
class InitResp:
    game_id: str
    hame_hash: str


@dataclass
class PlayReq:
    client_secret: str
    amount: int
    coin_id: int


@dataclass
class CoinFlipReq(PlayReq):
    side: bool


@dataclass
class PlayResp:
    win: bool
    user_net_delta: int
    transaction: Transaction


@protected_router.post("/init")
async def init_game(
    conn: Annotated[DB, Depends(get_tx_conn)],
) -> InitResp:
    game_id = secrets.token_hex(512)
    game_secret = secrets.token_hex(512)
    dt = await create_game_instance(conn, game_id, game_secret)
    return InitResp(dt.game_id, dt.game_hash)


async def _handle_game(conn: DB, game_id: str) -> GameInstance:
    instance = await get_game_instance(conn, game_id)
    if not instance:
        raise HTTPException(404, "The referenced game cannot be found")
    if instance.is_used:
        raise HTTPException(400, "The game have already been played")
    return instance


async def gamble_handler(
    conn: DB,
    user_win: bool,
    user_id: int,
    req: PlayReq,
    server_secret: str,
    client_secret: str,
) -> Transaction:
    if user_win:
        tid = (
            await game_force_transfer(
                conn,
                (await get_raw_user_account(conn, user_id))[0],
                0,
                coin=req.coin_id,
                amount=req.amount,
                server_secret=server_secret,
                client_secret=client_secret,
                user_win=user_win,
            )
        )[0]
    else:
        tid = (
            await game_force_transfer_holder_to_system(
                conn,
                (await get_db_user(conn, user_id)).holder_id,
                coin=req.coin_id,
                amount=req.amount,
                server_secret=server_secret,
                client_secret=client_secret,
                user_win=user_win,
            )
        )[0]
    transaction = await get_transaction_by_uni_id(conn, tid)
    if not transaction:
        raise ValueError("Transaction doesn't exist (wtf)")
    return transaction


@protected_router.post("/play_coinflip/{game_id}")
async def conflip_game(
    conn: Annotated[DB, Depends(get_tx_conn)],
    user_id: Annotated[int, Depends(get_user)],
    game_id: str,
    play_req: CoinFlipReq,
) -> PlayResp:
    instance = await _handle_game(conn, game_id)
    _ = await mark_game_instance_completed(conn, game_id)
    if (
        not await get_holder_coin_balance(conn, user_id, play_req.coin_id)
        >= play_req.amount
    ):
        raise HTTPException(403, "Attempt to gamble more than what you have")
    secret = generate_run_secret(instance.game_secret, play_req.client_secret)
    rnd = Random(secret)
    win = rnd.randint(0, 1) == 0
    transaction = await gamble_handler(
        conn, win, user_id, play_req, instance.game_secret, play_req.client_secret
    )
    return PlayResp(win, play_req.amount * (1 if win else -1), transaction)


game_app.include_router(protected_router)
