from typing import TypedDict


class User(TypedDict):
    id: str
    username: str
    discriminator: str
    global_name: str | None
    avatar: str | None
    bot: bool
    system: bool
    accent_color: int | None
    locale: str | None
    verified: bool
    email: str | None
    flags: int
    premium_type: int
    public_flags: int


class TokenResp(TypedDict):
    access_token: str
    token_type: str
    expires_in: int
    refresh_token: str
    scope: str
