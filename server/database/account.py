from asqlite import ProxiedConnection

from schema.db import Account, Coin


async def get_raw_user_account(conn: ProxiedConnection, user_id: int) -> list[Account]:
    holder_id: int = (
        await (
            await conn.execute("SELECT holder_id FROM account WHERE id = ?", (user_id,))
        ).fetchone()
    )[0]
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
        for acc_id, balances in balance_record.items()
    ]
