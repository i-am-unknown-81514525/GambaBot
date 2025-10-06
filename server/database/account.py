from asqlite import ProxiedConnection

from schema.db import Account, Coin
from .holder import holder_transact


async def get_raw_user_account(conn: ProxiedConnection, user_id: int) -> list[Account]:
    row = await (
            await conn.execute("SELECT holder_id FROM user_acc WHERE user_id = ?", (user_id,))
        ).fetchone()
    if not row:
        raise ValueError(f"User {user_id} not found")
    holder_id: int =row[0]
    return await get_holder_account(conn, holder_id)


async def get_holder_account(conn: ProxiedConnection, holder_id: int) -> list[Account]:
    accounts = await conn.execute(
        """
SELECT
    account.id AS account_id,
    coin.id AS coin_id,
    coin.unique_name AS unique_name,
    coin.read_name AS read_name,
    user_coin.amount AS amount
FROM account
RIGHT JOIN user_coin ON user_coin.account_id = account.id
LEFT JOIN coin ON coin.id = user_coin.coin_id
WHERE holder_id = ?""",
        (holder_id,),
    )
    balance_record: dict[int, dict[Coin, int]] = {}
    datas = await accounts.fetchall()
    for data in datas:
        balance_record[data[0]] = balance_record.get(data[0], {})
        coin = Coin(data[1], data[2], data[3])
        balance_record[data[0]][coin] = data[4]
    return [
        Account(acc_id, holder_id, balances)
        for acc_id, balances in sorted(balance_record.items(), key=lambda x: x[0])
    ]


async def get_account_by_id(conn: ProxiedConnection, account_id: int) -> Account:
    """
    Fetch a single account by its account id, with holder_id and balances.
    Raises ValueError if the account does not exist.
    """
    row = await (
        await conn.execute("SELECT holder_id FROM account WHERE id = ?", (account_id,))
    ).fetchone()
    if row is None:
        raise ValueError(f"Account {account_id} not found")
    holder_id: int = row[0]

    cur = await conn.execute(
        """
        SELECT c.id, c.unique_name, c.read_name, uc.amount
        FROM user_coin uc
        JOIN coin c ON c.id = uc.coin_id
        WHERE uc.account_id = ?
        """,
        (account_id,),
    )
    balances: dict[Coin, int] = {}
    for cid, unique_name, read_name, amount in await cur.fetchall():
        balances[Coin(cid, unique_name, read_name)] = amount

    return Account(id=account_id, holder_id=holder_id, balance=balances)


async def force_create_holder_account(
    conn: ProxiedConnection, holder_id: int
) -> Account:
    account = await (
        await conn.execute(
            """INSERT INTO account(holder_id) VALUES (?) RETURNING id AS account_id""",
            (holder_id,),
        )
    ).fetchone()

    account_id: int = account[0]
    return await get_account_by_id(conn, account_id)


async def create_account(conn: ProxiedConnection, holder_id: int) -> Account:
    _ = await holder_transact(
        conn, holder_id, 0, 0, 10, reason_payment="Create new account", kind="none"
    )
    return await force_create_holder_account(conn, holder_id)


async def get_account_coin_balance(
    conn: ProxiedConnection, account_id: int, coin_id: int
) -> int:
    # Scalar subquery returns a row even if no user_coin entry exists
    row = await (
        await conn.execute(
            "SELECT COALESCE((SELECT amount FROM user_coin WHERE account_id = ? AND coin_id = ?), 0)",
            (account_id, coin_id),
        )
    ).fetchone()
    return int(row[0]) if row else 0
