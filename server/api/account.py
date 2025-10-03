from typing import Annotated

from fastapi import FastAPI, APIRouter, Depends
from helper.jwt_helper import get_user

acc_app = FastAPI()

public_router = APIRouter()
protected_router = APIRouter(dependencies=[Depends(get_user)])


@public_router.get("/list/@me")
async def list_auth_self_accounts(user_id: Annotated[int, Depends(get_user)]): ...


@protected_router.get("/list/{user_id:int}")
async def list_user_accounts(user_id: int): ...
