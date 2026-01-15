from __future__ import annotations

import os
from pathlib import Path

import aiosqlite
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


load_dotenv()

PANEL_API_KEY = os.getenv("PANEL_API_KEY", "").strip()
if not PANEL_API_KEY:
    raise RuntimeError("PANEL_API_KEY is required")

DB_PATH = Path(os.getenv("DATABASE_PATH", "./data/bot.sqlite")).resolve()

# In most PaaS/containers the platform provides PORT.
PORT = int(os.getenv("PORT", os.getenv("PANEL_PORT", "8000")))

# For cloud/container use 0.0.0.0 so it's reachable from outside.
HOST = os.getenv("PANEL_HOST", "0.0.0.0")

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="Bot Admin Panel")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def require_key(x_api_key: str | None) -> None:
    if x_api_key != PANEL_API_KEY:
        raise HTTPException(status_code=401, detail="invalid api key")


@app.get("/")
async def index():
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/api/health")
async def health():
    return {"ok": True, "db": str(DB_PATH)}


@app.get("/api/users")
async def list_users(x_api_key: str | None = Header(default=None), limit: int = 50):
    require_key(x_api_key)
    if limit < 1 or limit > 200:
        raise HTTPException(status_code=400, detail="limit out of range")

    async with aiosqlite.connect(str(DB_PATH)) as conn:
        cur = await conn.execute(
            "SELECT u.discord_user_id, u.remanga_profile_url, b.balance FROM users u "
            "LEFT JOIN balances b ON b.discord_user_id=u.discord_user_id "
            "ORDER BY u.created_at DESC LIMIT ?",
            (limit,),
        )
        rows = await cur.fetchall()

    return {
        "items": [
            {"discord_user_id": int(r[0]), "remanga_profile_url": r[1], "balance": int(r[2] or 0)}
            for r in rows
        ]
    }


@app.post("/api/user/{user_id}/ban")
async def ban_user(user_id: int, body: dict, x_api_key: str | None = Header(default=None)):
    require_key(x_api_key)
    days = int(body.get("days", 7))
    reason = body.get("reason")

    if days < 0 or days > 3650:
        raise HTTPException(status_code=400, detail="days out of range")

    banned_until = None
    if days > 0:
        async with aiosqlite.connect(":memory:") as tmp:
            cur = await tmp.execute("SELECT datetime('now', ?)", (f"+{days} days",))
            row = await cur.fetchone()
            banned_until = row[0]

    async with aiosqlite.connect(str(DB_PATH)) as conn:
        await conn.execute(
            "INSERT INTO game_bans(discord_user_id, banned_until, reason) VALUES (?, ?, ?) "
            "ON CONFLICT(discord_user_id) DO UPDATE SET banned_until=excluded.banned_until, reason=excluded.reason, updated_at=datetime('now')",
            (user_id, banned_until, reason),
        )
        await conn.commit()

    return {"ok": True, "discord_user_id": user_id, "banned_until": banned_until, "reason": reason}


@app.post("/api/user/{user_id}/unban")
async def unban_user(user_id: int, x_api_key: str | None = Header(default=None)):
    require_key(x_api_key)
    async with aiosqlite.connect(str(DB_PATH)) as conn:
        await conn.execute(
            "INSERT INTO game_bans(discord_user_id, banned_until, reason) VALUES (?, NULL, NULL) "
            "ON CONFLICT(discord_user_id) DO UPDATE SET banned_until=NULL, reason=NULL, updated_at=datetime('now')",
            (user_id,),
        )
        await conn.commit()
    return {"ok": True}


def main() -> None:
    import uvicorn

    uvicorn.run(app, host=HOST, port=PORT, reload=False)


if __name__ == "__main__":
    main()
