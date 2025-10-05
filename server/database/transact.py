from typing import Literal, overload

from schema.db import Account, Coin, Transaction, Game, Reward
from cryptography.hazmat.primitives.hashes import Hash, SHA3_512

from asqlite import ProxiedConnection


class InsufficientBalanceError(ValueError): ...


def _acc_id(val: int | Account) -> int:
    return val if isinstance(val, int) else val.id


def _coin_id(val: int | Coin) -> int:
    return val if isinstance(val, int) else val.id


def _sha3_512_hex(data: str) -> str:
    h = Hash(SHA3_512())
    h.update(data.encode())
    return h.finalize().hex()


async def raw_force_transact(
    conn: ProxiedConnection,
    src: int,
    dst: int,
    coin: int,
    amount: int,
    reason: str = "No reason provided - Force transaction",
    kind: Literal["none", "reward", "game"] = "none",
    inner_hash: str = "",
) -> tuple[int, str]:
    # Update balances (dst gains, src loses)
    _ = await conn.execute(
        (
            "INSERT INTO user_coin(amount, account_id, coin_id) VALUES (?, ?, ?) "
            "ON CONFLICT (account_id, coin_id) DO UPDATE SET amount = amount + ? "
            "WHERE account_id = ? AND coin_id = ?"
        ),
        (amount, dst, coin, amount, dst, coin),
    )
    _ = await conn.execute(
        (
            "INSERT INTO user_coin(amount, account_id, coin_id) VALUES (?, ?, ?) "
            "ON CONFLICT (account_id, coin_id) DO UPDATE SET amount = amount + ? "
            "WHERE account_id = ? AND coin_id = ?"
        ),
        (-amount, src, coin, -amount, src, coin),
    )

    # Create universal transaction and fetch id + transact_data
    transact_row = await conn.execute(
        (
            "INSERT INTO uni_transact (src, dst, coin_id, amount, kind, reason, inner_hash) "
            "VALUES (?, ?, ?, ?, ?, ?, ?) RETURNING id, transact_data"
        ),
        (src, dst, coin, amount, kind, reason, inner_hash),
    )
    row = await transact_row.fetchone()
    transact_id: int = row[0]
    transact_data: str = row[1]

    # Compute self-hash of transact_data
    self_hash = _sha3_512_hex(transact_data)

    # Build chain hash by combining previous tx hash with this self-hash
    last_tx = await conn.execute(
        'SELECT tx FROM transact_chain ORDER BY "order" DESC LIMIT 1'
    )
    last_row = await last_tx.fetchone()
    last_tx_hash: str
    if last_row:
        last_tx_hash = last_row[0]
    else:
        last_tx_hash = "0" * 128

    new_tx = _sha3_512_hex(f"{last_tx_hash}::{self_hash}")

    _ = await conn.execute(
        "INSERT INTO transact_chain(tx, transact_id) VALUES (?, ?)",
        (new_tx, transact_id),
    )
    return transact_id, transact_data


async def force_transact(
    conn: ProxiedConnection,
    src: Account,
    dst: Account,
    coin: Coin,
    amount: int,
    reason: str = "No reason provided - Force transaction",
    kind: Literal["none", "reward", "game"] = "none",
    inner_hash: str = "",
) -> tuple[int, str]:
    return await raw_force_transact(
        conn, src.id, dst.id, coin.id, amount, reason, kind, inner_hash
    )


async def transact(
    conn: ProxiedConnection,
    src: Account | int,
    dst: Account | int,
    coin: Coin | int,
    amount: int,
    reason: str = "No reason provided - transaction",
    kind: Literal["none", "reward", "game"] = "none",
    inner_hash: str = "",
) -> tuple[int, str]:
    src = _acc_id(src)
    dst = _acc_id(dst)
    coin = _coin_id(coin)
    sufficient = await (
        await conn.execute(
            (
                "SELECT CASE WHEN COALESCE((SELECT amount FROM user_coin WHERE account_id = ? AND coin_id = ?), 0) >= ? "
                "THEN 1 ELSE 0 END AS sufficient;"
            ),
            (src, coin, amount),
        )
    ).fetchone()
    if sufficient[0] == 0:
        raise InsufficientBalanceError("Insufficient balance")

    return await raw_force_transact(
        conn, src, dst, coin, amount, reason, kind, inner_hash
    )


async def create_reward_transact(
    conn: ProxiedConnection,
    reason: str,
) -> tuple[int, str]:
    """
    Creates a reward_transact entry and returns (id, transact_data).
    """
    cur = await conn.execute(
        "INSERT INTO reward_transact(reason) VALUES (?) RETURNING id, transact_data",
        (reason,),
    )
    rid, rdata = await cur.fetchone()
    return int(rid), str(rdata)


async def create_game_transact(
    conn: ProxiedConnection,
    server_secret: str,
    client_secret: str,
    user_win: bool,
) -> tuple[int, str]:
    """
    Creates a game_transact entry and returns (id, transact_data).
    """
    cur = await conn.execute(
        (
            "INSERT INTO game_transact(server_secret, client_secret, user_win) "
            "VALUES (?, ?, ?) RETURNING id, transact_data"
        ),
        (server_secret, client_secret, int(user_win)),
    )
    gid, gdata = await cur.fetchone()
    return int(gid), str(gdata)


async def reward_force_transfer(
    conn: ProxiedConnection,
    src: int | Account,
    dst: int | Account,
    coin: int | Coin,
    amount: int,
    reward_reason: str,
    uni_reason: str = "Reward payout",
) -> tuple[int, int]:
    reward_id, reward_data = await create_reward_transact(conn, reward_reason)
    inner_hash = _sha3_512_hex(reward_data)

    uni_id, _ = await raw_force_transact(
        conn,
        _acc_id(src),
        _acc_id(dst),
        _coin_id(coin),
        amount,
        reason=uni_reason,
        kind="reward",
        inner_hash=inner_hash,
    )

    _ = await conn.execute(
        "UPDATE reward_transact SET ref_id = ? WHERE id = ?",
        (uni_id, reward_id),
    )
    return uni_id, reward_id


async def game_force_transfer(
    conn: ProxiedConnection,
    src: int | Account,
    dst: int | Account,
    coin: int | Coin,
    amount: int,
    server_secret: str,
    client_secret: str,
    user_win: bool,
    uni_reason: str = "Game settlement",
) -> tuple[int, int]:
    game_id, game_data = await create_game_transact(
        conn, server_secret, client_secret, user_win
    )
    inner_hash = _sha3_512_hex(game_data)

    uni_id, _ = await raw_force_transact(
        conn,
        _acc_id(src),
        _acc_id(dst),
        _coin_id(coin),
        amount,
        reason=uni_reason,
        kind="game",
        inner_hash=inner_hash,
    )

    _ = await conn.execute(
        "UPDATE game_transact SET ref_id = ? WHERE id = ?",
        (uni_id, game_id),
    )
    return uni_id, game_id


async def list_account_transactions(
    conn: ProxiedConnection,
    account: int | Account,
    limit: int = 100,
    offset: int = 0,
) -> list[Transaction]:
    acc_id = _acc_id(account)
    cur = await conn.execute(
        """
        SELECT
            u.id,
            u.src,
            u.dst,
            u.coin_id,
            c.unique_name,
            c.read_name,
            u.amount,
            u.kind,
            u.reason,
            u.inner_hash,
            u.create_dt,
            u.transact_data,
            rt.id AS reward_id,
            rt.reason AS reward_reason,
            gt.id AS game_id,
            gt.server_secret,
            gt.client_secret,
            gt.game_instance,
            gt.user_win
        FROM uni_transact u
        LEFT JOIN coin c ON c.id = u.coin_id
        LEFT JOIN reward_transact rt ON rt.ref_id = u.id
        LEFT JOIN game_transact gt ON gt.ref_id = u.id
        WHERE u.src = ? OR u.dst = ?
        ORDER BY u.id DESC
        LIMIT ? OFFSET ?
        """,
        (acc_id, acc_id, limit, offset),
    )
    rows = await cur.fetchall()
    results: list[Transaction] = []
    for (
        uid,
        src,
        dst,
        coin_id,
        coin_unique,
        coin_read,
        amount,
        kind,
        reason,
        inner_hash,
        create_dt,
        transact_data,
        reward_id,
        reward_reason,
        game_id,
        server_secret,
        client_secret,
        game_instance,
        user_win,
    ) in rows:
        reward_dc = (
            Reward(id=reward_id, reason=reward_reason)
            if reward_id is not None
            else None
        )
        game_dc = (
            Game(
                id=game_id,
                server_secret=server_secret,
                client_secret=client_secret,
                user_win=bool(user_win),
                game_instance=game_instance,
            )
            if game_id is not None
            else None
        )
        results.append(
            Transaction(
                id=uid,
                src=src,
                dst=dst,
                coin_id=coin_id,
                coin_unique_name=coin_unique,
                coin_read_name=coin_read,
                amount=amount,
                kind=kind,
                reason=reason,
                inner_hash=inner_hash,
                create_dt=create_dt,
                transact_data=transact_data,
                reward=reward_dc,
                game=game_dc,
            )
        )
    return results


async def get_transaction_by_uni_id(
    conn: ProxiedConnection, uni_id: int
) -> Transaction | None:
    cur = await conn.execute(
        """
        SELECT
            u.id,
            u.src,
            u.dst,
            u.coin_id,
            c.unique_name,
            c.read_name,
            u.amount,
            u.kind,
            u.reason,
            u.inner_hash,
            u.create_dt,
            u.transact_data,
            rt.id AS reward_id,
            rt.reason AS reward_reason,
            gt.id AS game_id,
            gt.server_secret,
            gt.client_secret,
            gt.game_instance,
            gt.user_win
        FROM uni_transact u
        LEFT JOIN coin c ON c.id = u.coin_id
        LEFT JOIN reward_transact rt ON rt.ref_id = u.id
        LEFT JOIN game_transact gt ON gt.ref_id = u.id
        WHERE u.id = ?
        """,
        (uni_id,),
    )
    row = await cur.fetchone()
    if not row:
        return None
    (
        uid,
        src,
        dst,
        coin_id,
        coin_unique,
        coin_read,
        amount,
        kind,
        reason,
        inner_hash,
        create_dt,
        transact_data,
        reward_id,
        reward_reason,
        game_id,
        server_secret,
        client_secret,
        game_instance,
        user_win,
    ) = row
    reward_dc = (
        Reward(id=reward_id, reason=reward_reason) if reward_id is not None else None
    )
    game_dc = (
        Game(
            id=game_id,
            server_secret=server_secret,
            client_secret=client_secret,
            game_instance=game_instance,
            user_win=bool(user_win),
        )
        if game_id is not None
        else None
    )
    return Transaction(
        id=uid,
        src=src,
        dst=dst,
        coin_id=coin_id,
        coin_unique_name=coin_unique,
        coin_read_name=coin_read,
        amount=amount,
        kind=kind,
        reason=reason,
        inner_hash=inner_hash,
        create_dt=create_dt,
        transact_data=transact_data,
        reward=reward_dc,
        game=game_dc,
    )


async def get_transaction_by_tx(conn: ProxiedConnection, tx: str) -> Transaction | None:
    cur = await conn.execute(
        """
        SELECT
            u.id,
            u.src,
            u.dst,
            u.coin_id,
            c.unique_name,
            c.read_name,
            u.amount,
            u.kind,
            u.reason,
            u.inner_hash,
            u.create_dt,
            u.transact_data,
            rt.id AS reward_id,
            rt.reason AS reward_reason,
            gt.id AS game_id,
            gt.server_secret,
            gt.client_secret,
            gt.game_instance,
            gt.user_win
        FROM transact_chain tc
        INNER JOIN uni_transact u ON u.id = tc.transact_id
        LEFT JOIN coin c ON c.id = u.coin_id
        LEFT JOIN reward_transact rt ON rt.ref_id = u.id
        LEFT JOIN game_transact gt ON gt.ref_id = u.id
        WHERE tc.tx = ?
        """,
        (tx,),
    )
    row = await cur.fetchone()
    if not row:
        return None
    (
        uid,
        src,
        dst,
        coin_id,
        coin_unique,
        coin_read,
        amount,
        kind,
        reason,
        inner_hash,
        create_dt,
        transact_data,
        reward_id,
        reward_reason,
        game_id,
        server_secret,
        client_secret,
        game_instance,
        user_win,
    ) = row
    reward_dc = (
        Reward(id=reward_id, reason=reward_reason) if reward_id is not None else None
    )
    game_dc = (
        Game(
            id=game_id,
            server_secret=server_secret,
            client_secret=client_secret,
            user_win=bool(user_win),
            game_instance=game_instance,
        )
        if game_id is not None
        else None
    )
    return Transaction(
        id=uid,
        src=src,
        dst=dst,
        coin_id=coin_id,
        coin_unique_name=coin_unique,
        coin_read_name=coin_read,
        amount=amount,
        kind=kind,
        reason=reason,
        inner_hash=inner_hash,
        create_dt=create_dt,
        transact_data=transact_data,
        reward=reward_dc,
        game=game_dc,
    )


async def get_transaction(conn: ProxiedConnection, id: str | int) -> Transaction | None:
    if isinstance(id, str):
        return await get_transaction_by_tx(conn, id)
    if isinstance(id, int):  # pyright: ignore[reportUnnecessaryIsInstance]
        return await get_transaction_by_uni_id(conn, id)
    raise TypeError("ID can only be string(str) or (int)")  # pyright: ignore[reportUnreachable]
