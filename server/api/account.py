from typing import Annotated

import asqlite
from fastapi import FastAPI, APIRouter, Depends
from fastapi.responses import JSONResponse

from schema.db import Account
from helper.jwt_helper import get_user
from helper.db_helper import get_tx_conn
from database.account import get_raw_user_account

acc_app = FastAPI()

public_router = APIRouter()
protected_router = APIRouter(dependencies=[Depends(get_user)])


@protected_router.get("/list/@me")
async def list_auth_self_accounts(
    conn: Annotated[asqlite.ProxiedConnection, Depends(get_tx_conn)],
    user_id: Annotated[int, Depends(get_user)],
) -> list[Account]:
    return await get_raw_user_account(conn, user_id)


@public_router.get("/list/{user_id:int}")
async def list_user_accounts(
    conn: Annotated[asqlite.ProxiedConnection, Depends(get_tx_conn)], user_id: int
) -> list[Account]:
    return await get_raw_user_account(conn, user_id)


acc_app.include_router(protected_router)
acc_app.include_router(public_router)
