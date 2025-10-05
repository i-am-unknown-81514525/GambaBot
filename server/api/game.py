from dataclasses import dataclass
import secrets
from typing import Annotated
import uuid

from fastapi import FastAPI, APIRouter, Depends
from helper.jwt_helper import get_user
from helper.db_helper import DB, get_tx_conn

from database.game import create_game_instance

game_app = FastAPI()

protected_router = APIRouter(dependencies=[Depends(get_user)])


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


@protected_router.post("/init")
async def init_game(
    conn: Annotated[DB, Depends(get_tx_conn)],
) -> InitResp:
    game_id = secrets.token_hex(512)
    game_secret = secrets.token_hex(512)
    dt = await create_game_instance(conn, game_id, game_secret)
    return InitResp(dt.game_id, dt.game_hash)


@protected_router.post("/play_coinflip/{game_id}")
async def conflip_game(
    conn: Annotated[DB, Depends(get_tx_conn)],
    user_id: Annotated[int, Depends(get_user)],
    game_id: str,
    play_req: CoinFlipReq,
): ...
