from crypto.jwt_handler import JWTHandler
import os
import logging

from fastapi import Request, HTTPException

jwt_handler = JWTHandler(os.environ["JWT_SECRET"])

logger = logging.getLogger(__name__)


class AuthError(HTTPException):
    def __init__(self, detail: str = "Unauthorized", status_code: int = 401):
        super().__init__(status_code=status_code, detail=detail)


async def get_user(
    request: Request,
) -> int:
    if not request.cookies.get("login"):
        if request.headers.get("X-API-KEY"):
            jwt_value = request.headers["X-API-KEY"]
        else:
            raise AuthError("Not logged in")
    else:
        jwt_value = request.cookies["login"]
    try:
        jwt_inner = jwt_handler.decode(jwt_value)
    except Exception:
        logger.error("Failed to decode JWT", exc_info=True)
        raise AuthError("Invalid token")
    if jwt_inner.get("user_id") is None or not isinstance(jwt_inner["user_id"], int):
        print(jwt_inner)
        raise AuthError("Invalid token")
    print(jwt_inner)
    return jwt_inner["user_id"]
