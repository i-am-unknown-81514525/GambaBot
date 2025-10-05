from pathlib import Path

import asqlite
from fastapi import Request
from fastapi.applications import FastAPI

DB_PATH = Path() / "data" / "gamba.db"
SCHEMA_PATH = Path() / "sql" / "schema.sql"

PRAGMAS = [
    "PRAGMA journal_mode=WAL;",
    "PRAGMA synchronous=NORMAL;",
    "PRAGMA foreign_keys=ON;",
    "PRAGMA temp_store=MEMORY;",
    "PRAGMA cache_size=-2000;",  # ~2MB
]

type DB = asqlite.ProxiedConnection


async def init_pool(app: FastAPI, size: int = 8):
    if not DB_PATH.exists():
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        DB_PATH.touch()
        async with asqlite.connect(DB_PATH.absolute().as_posix()) as conn:
            _ = await conn.executescript(SCHEMA_PATH.read_text())
            await conn.commit()
    app.state.db_pool = await asqlite.create_pool(
        DB_PATH.absolute().as_posix(), size=size
    )
    # Initialize all currently created connections with PRAGMAs.
    # Pool lazily creates up to max_size; only those pre-created get PRAGMAs now.
    for _ in range(size):
        async with app.state.db_pool.acquire() as conn:
            for pragma in PRAGMAS:
                _ = await conn.execute(pragma)
            await conn.commit()


async def close_pool(app: FastAPI):
    pool: asqlite.Pool | None = getattr(app.state, "db_pool", None)
    if pool:
        await pool.close()


async def get_conn(request: Request):
    pool: asqlite.Pool = request.state.parent.state.db_pool  # pyright: ignore[reportAny]
    async with pool.acquire() as conn:
        yield conn


async def get_tx_conn(request: Request, immediate: bool = True):
    pool: asqlite.Pool = request.state.parent.state.db_pool  # pyright: ignore[reportAny]
    async with pool.acquire() as conn:
        if immediate:
            _ = await conn.execute("BEGIN IMMEDIATE;")
        else:
            _ = await conn.execute("BEGIN;")
        try:
            yield conn
        except Exception:
            _ = await conn.execute("ROLLBACK;")
            raise
        else:
            _ = await conn.execute("COMMIT;")
