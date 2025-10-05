from helper.db_helper import DB
from schema.db import Coin


async def get_holder_id_by_account(conn: DB, account_id: int) -> int:
    row = await (
        await conn.execute("SELECT holder_id FROM account WHERE id = ?", (account_id,))
    ).fetchone()
    if row is None:
        raise ValueError(f"Account {account_id} not found")
    return int(row[0])


async def get_account_coin_balance(conn: DB, account_id: int, coin_id: int) -> int:
    row = await (
        await conn.execute(
            "SELECT COALESCE((SELECT amount FROM user_coin WHERE account_id = ? AND coin_id = ?), 0)",
            (account_id, coin_id),
        )
    ).fetchone()
    return int(row[0]) if row else 0


async def get_holder_coin_balance(conn: DB, holder_id: int, coin_id: int) -> int:
    row = await (
        await conn.execute(
            """
            SELECT COALESCE(SUM(uc.amount), 0)
            FROM account a
            LEFT JOIN user_coin uc
              ON uc.account_id = a.id AND uc.coin_id = ?
            WHERE a.holder_id = ?
            """,
            (coin_id, holder_id),
        )
    ).fetchone()
    return int(row[0]) if row else 0


async def get_account_balance(conn: DB, account_id: int) -> dict[Coin, int]:
    cur = await conn.execute(
        """
        SELECT c.id, c.unique_name, c.read_name, uc.amount
        FROM user_coin uc
        JOIN coin c ON c.id = uc.coin_id
        WHERE uc.account_id = ?
        ORDER BY c.id
        """,
        (account_id,),
    )
    balances: dict[Coin, int] = {}
    for cid, unique_name, read_name, amount in await cur.fetchall():
        balances[Coin(cid, unique_name, read_name)] = int(amount)
    return balances


async def get_holder_balance(conn: DB, holder_id: int) -> dict[Coin, int]:
    cur = await conn.execute(
        """
        SELECT c.id, c.unique_name, c.read_name, COALESCE(SUM(uc.amount), 0) AS total
        FROM account a
        LEFT JOIN user_coin uc ON uc.account_id = a.id
        LEFT JOIN coin c ON c.id = uc.coin_id
        WHERE a.holder_id = ?
        GROUP BY c.id, c.unique_name, c.read_name
        HAVING c.id IS NOT NULL
        ORDER BY c.id
        """,
        (holder_id,),
    )
    balances: dict[Coin, int] = {}
    for cid, unique_name, read_name, total in await cur.fetchall():
        balances[Coin(cid, unique_name, read_name)] = int(total)
    return balances
