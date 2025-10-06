from typing import Annotated, TypedDict

from fastapi import APIRouter, Depends, HTTPException, status, FastAPI

from database.user import create_user, get_user as get_db_user, UserNotExistError, user_exist
from helper.db_helper import DB, get_tx_conn
from helper.jwt_helper import get_user
from schema.db import User, Transaction
from database.coin import get_holder_balance
from database.transact import list_holder_transactions

user_app = FastAPI()

public_router = APIRouter()
protected_router = APIRouter(dependencies=[Depends(get_user)])

@public_router.get("/get/{user_id:int}", response_model=User)
async def handle_get_user(
    conn: Annotated[DB, Depends(get_tx_conn)], user_id: int
) -> User:
    try:
        user = await get_db_user(conn, user_id)
    except UserNotExistError:
        raise HTTPException(404, "User doesn't exist")
    return user



@protected_router.post("/create", response_model=User, status_code=status.HTTP_201_CREATED)
async def handle_create_user(
    conn: Annotated[DB, Depends(get_tx_conn)],
    user_id: Annotated[int, Depends(get_user)],
):
    if await user_exist(conn, user_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User with Discord ID {user_id} already have an account.",
        )
    
    new_user = await create_user(conn, user_id)
    return new_user

class ProfileData(TypedDict):
    balance: dict[str, int]
    transactions: list[Transaction]
    

@protected_router.get("/profile/@me", response_model=ProfileData)
async def get_user_profile(
    conn: Annotated[DB, Depends(get_tx_conn)],
    user_id: Annotated[int, Depends(get_user)],
) -> ProfileData:
    user = await get_db_user(conn, user_id)
    balance = {c.unique_name: b for c, b in (await get_holder_balance(conn, user.holder_id)).items()}
    transactions = await list_holder_transactions(conn, user.holder_id, limit=10)
    return {"balance": balance, "transactions": transactions}

user_app.include_router(protected_router)
user_app.include_router(public_router)
