from typing import Annotated, TypedDict

from fastapi import APIRouter, Depends, HTTPException, status, FastAPI

from database.user import create_user, get_user as get_db_user, UserNotExistError, user_exist
from database.coin import get_holder_balance
from database.transact import list_holder_transactions
from helper.db_helper import DB, get_tx_conn
from helper.jwt_helper import get_user
from schema.db import User, Transaction

profile_app = FastAPI()

public_router = APIRouter()
protected_router = APIRouter(dependencies=[Depends(get_user)])





    
profile_app.include_router(protected_router)
profile_app.include_router(public_router)
