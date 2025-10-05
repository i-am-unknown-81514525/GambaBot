from typing import Literal

from asqlite import ProxiedConnection
from schema.db import Account, Coin
from .transact import raw_force_transact, InsufficientBalanceError, create_game_transact

from cryptography.hazmat.primitives.hashes import Hash, SHA3_512


def _sha3_512_hex(data: str) -> str:
    h = Hash(SHA3_512())
    h.update(data.encode())
    return h.finalize().hex()


def _acc_id(val: int | Account) -> int:
    return val if isinstance(val, int) else val.id


def _coin_id(val: int | Coin) -> int:
    return val if isinstance(val, int) else val.id


async def holder_transact(
    conn: ProxiedConnection,
    holder_id: int,
    dst: int | Account,
    coin: int | Coin,
    amount: int,
    *,
    reason_internal: str = "Holder consolidation",
    reason_payment: str = "Holder payment",
    kind: Literal["none", "reward", "game"] = "none",
    payment_inner_hash: str = "",
) -> list[tuple[int, str]]:
    if amount <= 0:
        raise ValueError("amount must be > 0")

    dst_id = _acc_id(dst)
    coin_id = _coin_id(coin)

    # Fetch accounts for holder with balances (ordered by account_id asc: "first" is rows[0])
    cur = await conn.execute(
        """
        SELECT a.id AS account_id, COALESCE(uc.amount, 0) AS balance
        FROM account a
        LEFT JOIN user_coin uc
          ON uc.account_id = a.id AND uc.coin_id = ?
        WHERE a.holder_id = ?
        ORDER BY a.id ASC
        """,
        (coin_id, holder_id),
    )
    rows = await cur.fetchall()

    if not rows:
        raise InsufficientBalanceError(f"No accounts found for holder {holder_id}")

    combined = sum(bal for _, bal in rows)
    if combined < amount:
        raise InsufficientBalanceError(
            f"Insufficient combined balance for holder {holder_id}: have {combined}, need {amount}"
        )

    # 1) If any single account has sufficient balance, pay from that account directly.
    for src_account_id, bal in rows:
        if bal >= amount:
            tx_id, tx_data = await raw_force_transact(
                conn,
                src=src_account_id,
                dst=dst_id,
                coin=coin_id,
                amount=amount,
                reason=reason_payment,
                kind=kind,
                inner_hash="",
            )
            return [(tx_id, tx_data)]

    # 2) Otherwise, consolidate just enough into the first account, then pay from it.
    first_account_id, first_balance = rows[0]
    needed = amount - first_balance if first_balance < amount else 0

    results: list[tuple[int, str]] = []

    if needed > 0:
        for src_account_id, bal in rows[1:]:
            if needed <= 0:
                break
            if bal <= 0:
                continue
            take = bal if bal <= needed else needed
            tx_id, tx_data = await raw_force_transact(
                conn,
                src=src_account_id,
                dst=first_account_id,
                coin=coin_id,
                amount=take,
                reason=reason_internal,
                kind=kind,
                inner_hash="",
            )
            results.append((tx_id, tx_data))
            needed -= take

    # Final payment from the first account
    tx_id, tx_data = await raw_force_transact(
        conn,
        src=first_account_id,
        dst=dst_id,
        coin=coin_id,
        amount=amount,
        reason=reason_payment,
        kind=kind,
        inner_hash=payment_inner_hash,
    )
    results.append((tx_id, tx_data))
    return results


async def get_holder_coin_balance(
    conn: ProxiedConnection, holder_id: int, coin_id: int
) -> int:
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


async def game_force_transfer_holder_to_system(
    conn: ProxiedConnection,
    holder_id: int,
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

    _, uni_id = await holder_transact(
        conn,
        holder_id,
        0,
        _coin_id(coin),
        amount,
        reason_payment=uni_reason,
        kind="game",
        payment_inner_hash=inner_hash,
    )

    _ = await conn.execute(
        "UPDATE game_transact SET ref_id = ? WHERE id = ?",
        (uni_id[0], game_id),
    )
    return uni_id[0], game_id
