from contextlib import asynccontextmanager

from fastapi import FastAPI
from api.auth import auth_app
from api.account import acc_app
from api.transaction import tr_app
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


@app.get("/health")
async def health():
    return {"status": "ok"}
