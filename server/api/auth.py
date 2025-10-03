import os
import time
import secrets
from urllib.parse import urlencode

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv
from aiohttp import ClientSession

from schema.discord import TokenResp, User
from crypto.jwt_handler import JWTHandler

load_dotenv()  # pyright: ignore[reportUnusedCallResult]

auth_app = FastAPI()
DISCORD_CLIENT_ID = os.environ["DISCORD_CLIENT_ID"]
DISCORD_CLIENT_SECRET = os.environ["DISCORD_CLIENT_SECRET"]
DISCORD_REDIRECT_URI = os.environ["DISCORD_REDIRECT_URI"]
JWT_SECRET = os.environ["JWT_SECRET"]
jwt_handler = JWTHandler(JWT_SECRET)

STATE_TTL_SECONDS = 300

type JSON = dict[str, JSON] | list[JSON] | str | None | bool | float | int
type StateValue = str
type RedirectURL = str
type TTL = float
type DiscordToken = str

# In-memory state store (sufficient for single-process dev)
# For production / multi-instance: move to Redis or signed stateless token
_pending_states: dict[StateValue, tuple[TTL, RedirectURL]] = {}


def create_state(redirect: RedirectURL) -> StateValue:
    state = secrets.token_urlsafe(24)
    _pending_states[state] = time.time(), redirect
    return state


def validate_and_consume_state(state: StateValue) -> RedirectURL:
    created = _pending_states.get(state)
    if not created:
        raise HTTPException(400, "Invalid or already used state")
    if time.time() - created[0] > STATE_TTL_SECONDS:
        _ = _pending_states.pop(state, None)
        raise HTTPException(400, "State expired")
    _ = _pending_states.pop(state, None)
    return created[1]


async def discord_token_exchange(code: DiscordToken) -> TokenResp:
    form = {
        "client_id": DISCORD_CLIENT_ID,
        "client_secret": DISCORD_CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": DISCORD_REDIRECT_URI,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    async with ClientSession(timeout=15) as client:
        resp = await client.post(
            "https://discord.com/api/oauth2/token", data=form, headers=headers
        )
        if not resp.ok:
            raise HTTPException(400, f"Code exchange failed: {resp.text}")
        return await resp.json()  # pyright: ignore[reportAny]


async def fetch_discord_user(access_token: str) -> User:
    headers = {"Authorization": f"Bearer {access_token}"}
    async with ClientSession(timeout=15) as client:
        resp = await client.get("https://discord.com/api//users/@me", headers=headers)
        if not resp.ok:
            raise HTTPException(400, "Failed to fetch Discord user")
        return await resp.json()  # pyright: ignore[reportAny]


def build_avatar_url(user: User) -> str:
    avatar_hash = user.get("avatar")
    if avatar_hash:
        ext = "gif" if avatar_hash.startswith("a_") else "png"
        return f"https://cdn.discordapp.com/avatars/{user['id']}/{avatar_hash}.{ext}"
    disc = int(user.get("discriminator", "0")) if user.get("discriminator") else 0
    return f"https://cdn.discordapp.com/embed/avatars/{disc % 5}.png"


@auth_app.get("/discord/login")
async def discord_login(redirect: str = "/"):
    """
    Step 1: Redirect user to Discord authorization screen.
    Pass ?redirect=/some/path if you want to track post-login navigation client-side.
    """
    state = create_state(redirect)
    params = {
        "client_id": DISCORD_CLIENT_ID,
        "redirect_uri": DISCORD_REDIRECT_URI,
        "response_type": "code",
        "scope": "identify",
        "state": state,
        "prompt": "consent",
    }
    url = f"https://discord.com/oauth2/authorize?{urlencode(params)}"
    return RedirectResponse(url, status_code=302)


@auth_app.get("/discord/callback")
async def discord_callback(code: str, state: str) -> RedirectResponse:
    url = validate_and_consume_state(state)
    token_data = await discord_token_exchange(code)
    access_token = token_data["access_token"]
    user = await fetch_discord_user(access_token)
    resp = RedirectResponse(url, status_code=302)
    resp.set_cookie(
        "login",
        jwt_handler.create_user(int(user["id"])),
        max_age=86400,
        httponly=True,
        path="/",
    )
    return resp


@auth_app.get("/logout")
async def discord_logout():
    resp = RedirectResponse("/", status_code=302)
    resp.delete_cookie("login")
    return resp


@auth_app.get("/status")
async def discord_status(request: Request):
    if not request.cookies.get("login"):
        return {"status": "error", "reason": "Not logged in"}
    data: str = request.cookies["login"]
    if data and jwt_handler.verify(data):
        return {"status": "ok"}
    return {"status": "error", "reason": "Invalid token"}
