from contextlib import asynccontextmanager
from collections.abc import Callable, Awaitable

from fastapi import FastAPI, Request, Response
from api.auth import auth_app
from api.account import acc_app
from api.transaction import tr_app
from api.game import game_app
from helper.db_helper import init_pool, close_pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_pool(app)
    yield
    await close_pool(app)


app = FastAPI(lifespan=lifespan)
app.mount("/auth", auth_app) 
app.mount("/account", acc_app)
app.mount("/transaction", tr_app)
app.mount("/game", game_app)

@app.middleware("http")
async def attach_parent(request: Request, call_next: Callable[[Request], Awaitable[Response]]):
    request.state.parent = app
    response = await call_next(request)
    return response


@app.get("/health")
async def health():
    return {"status": "ok"}
