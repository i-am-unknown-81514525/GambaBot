from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, FastAPI

from database.user import create_user, get_user as get_db_user
from helper.db_helper import DB, get_tx_conn
from helper.jwt_helper import get_user
from schema.db import User

# This router will be protected; only authenticated internal services (like the bot) can access it.
user_app = FastAPI()

public_router = APIRouter()
protected_router = APIRouter(dependencies=[Depends(get_user)])

@public_router.get("/get/{user_id:int}", response_model=User)
async def handle_get_user(
    conn: Annotated[DB, Depends(get_tx_conn)], user_id: int
) -> User:
    user = await get_db_user(conn, user_id)
    if not user:
        raise HTTPException(404, "User doesn't exist")
    return user



@protected_router.post("/create", response_model=User, status_code=status.HTTP_201_CREATED)
async def handle_create_user(
    conn: Annotated[DB, Depends(get_tx_conn)],
    user_id: Annotated[int, Depends(get_user)],
):
    if await get_db_user(conn, user_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User with Discord ID {user_id} already have an account.",
        )
    
    new_user = await create_user(conn, user_id)
    return new_user
    
user_app.include_router(protected_router)
