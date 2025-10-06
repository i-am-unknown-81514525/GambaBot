from typing import Annotated, TypedDict

from fastapi import FastAPI, APIRouter, Depends, HTTPException

from database.transact import get_transaction as db_get_transaction
from database.transact import transact, InsufficientBalanceError
from database.account import get_holder_account, get_account_by_id
from database.user import UserNotExistError, get_user as db_get_user
from helper.jwt_helper import get_user
from helper.db_helper import DB, get_tx_conn
from schema.db import Transaction

tr_app = FastAPI()

public_router = APIRouter()
protected_router = APIRouter(dependencies=[Depends(get_user)])


@public_router.get("/get/{transaction_id}")
async def get_transaction(
    conn: Annotated[DB, Depends(get_tx_conn)], transaction_id: str
) -> Transaction:
    try:
        uni_id = int(transaction_id)
        result = await db_get_transaction(conn, uni_id)
        if not result:
            raise HTTPException(404, "The requests transaction cannot be found")
    except (ValueError, HTTPException):
        result = await db_get_transaction(conn, transaction_id)
        if not result:
            raise HTTPException(404, "The requests transaction cannot be found")
    return result


class PaySchema(TypedDict):
    src: int
    dst: int
    coin_id: int
    amount: int


@protected_router.post("/pay")
async def pay_transaction(
    conn: Annotated[DB, Depends(get_tx_conn)],
    payment_config: PaySchema,
    user: Annotated[int, Depends(get_user)],
) -> Transaction:
    try:
        user_obj = await db_get_user(conn, user)
    except UserNotExistError:
        raise HTTPException(404, "User not found")

    # Correctly check if the authenticated user owns the source account
    # by comparing their holder_id with the account's holder_id.
    if payment_config["src"] not in map(lambda x: x.id, await get_holder_account(conn, user_obj.holder_id)):
        raise HTTPException(403, "You do not own the source account.")
    
    try:
        await get_account_by_id(conn, payment_config["dst"])
    except ValueError:
        raise HTTPException(404, "Destination account not found")

    try:
        tid, _ = await transact(
            conn,
            payment_config["src"],
            payment_config["dst"],
            payment_config["coin_id"],
            payment_config["amount"],
        )
        result = await db_get_transaction(conn, tid)
        if not result:
            raise HTTPException(500, "Unknown status: cannot get transaction just created")
        return result
    except InsufficientBalanceError:
        raise HTTPException(422, "Insufficient Balance")


tr_app.include_router(public_router)
tr_app.include_router(protected_router)
