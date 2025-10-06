from typing import Annotated

import asqlite
from fastapi import FastAPI, APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from schema.db import Account
from helper.jwt_helper import get_user
from helper.db_helper import get_tx_conn
from database.account import get_raw_user_account, get_account_by_id
from database.user import get_user as get_db_user

acc_app = FastAPI()

public_router = APIRouter()
protected_router = APIRouter(dependencies=[Depends(get_user)])


@protected_router.get("/list/@me")
async def list_auth_self_accounts(
    conn: Annotated[asqlite.ProxiedConnection, Depends(get_tx_conn)],
    user_id: Annotated[int, Depends(get_user)],
) -> list[Account]:
    user = await get_db_user(conn, user_id)
    if not user:
        raise HTTPException(404, "User doesn't exist")
    return await get_raw_user_account(conn, user_id)


@public_router.get("/list/{user_id:int}")
async def list_user_accounts(
    conn: Annotated[asqlite.ProxiedConnection, Depends(get_tx_conn)], user_id: int
) -> list[Account]:
    user = await get_db_user(conn, user_id)
    if not user:
        raise HTTPException(404, "User doesn't exist")
    return await get_raw_user_account(conn, user_id)

@public_router.get("/exist/{account_id:int}")
async def check_account_exist(
    conn: Annotated[asqlite.ProxiedConnection, Depends(get_tx_conn)],
    account_id: int,
) -> bool:
    try:
        await get_account_by_id(conn, account_id)
    except ValueError:
        return False
    return True

@public_router.get("/get/{account_id:int}")
async def get_account(
    conn: Annotated[asqlite.ProxiedConnection, Depends(get_tx_conn)],
    account_id: int,
) -> Account:
    try:
        return await get_account_by_id(conn, account_id)
    except ValueError:
        raise HTTPException(404, "Account doesn't exist")


acc_app.include_router(protected_router)
acc_app.include_router(public_router)
