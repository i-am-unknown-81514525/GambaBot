from schema.db import User
from .transact import raw_force_transact
from .account import get_raw_user_account

from asqlite import ProxiedConnection


class UserNotExistError(ValueError): ...

async def user_exist(conn: ProxiedConnection, user_id: int) -> bool:
    if (
        await (
            await conn.execute(
                "SELECT COUNT(*) FROM user_acc WHERE user_id = ?", (user_id,)
            )
        ).fetchone()
    )[0] == 0:
        return False
    return True

async def get_user(conn: ProxiedConnection, user_id: int) -> User:
    if (
        await (
            await conn.execute(
                "SELECT COUNT(*) FROM user_acc WHERE user_id = ?", (user_id,)
            )
        ).fetchone()
    )[0] == 0:
        raise UserNotExistError(f"The user {user_id} does not exist")
    row = await (
        await conn.execute(
            "SELECT user_id, holder_id, create_dt FROM user_acc WHERE user_id = ?",
            (user_id,),
        )
    ).fetchone()
    await conn.commit()
    return User(
        id=row[0], holder_id=row[1], accounts=await get_raw_user_account(conn, row[0])
    )


async def create_user(conn: ProxiedConnection, user_id: int) -> User:
    cursor = await conn.execute(
        "SELECT COUNT(*) FROM user_acc WHERE user_id = ?", (user_id,)
    )
    count = await cursor.fetchone()
    if count[0] != 0:
        raise ValueError("User already exists")
    holder_record = await conn.execute(
        "INSERT INTO holder_entity DEFAULT VALUES RETURNING holder_id;"
    )
    holder_id: int = (await holder_record.fetchone())[0]
    _ = await conn.execute(
        "INSERT INTO user_acc(user_id, holder_id) VALUES (?, ?);", (user_id, holder_id)
    )
    account_record = await conn.execute(
        "INSERT INTO account(holder_id) VALUES (?) RETURNING id AS account_id;",
        (holder_id,),
    )
    account_id: int = (await account_record.fetchone())[0]
    await raw_force_transact(
        conn, 0, account_id, 0, 1000, f"Account creation user:{user_id}"
    )
    await conn.commit()
    return await get_user(conn, user_id)
