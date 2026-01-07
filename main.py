from fastapi import FastAPI, Query, Header
from fastapi.responses import JSONResponse
import httpx
import asyncio
import os
from dotenv import load_dotenv

# =========================
# LOAD ENV
# =========================
load_dotenv()
API_KEY = os.getenv("API_KEY")
AUTHOR = "@henntaiiz"

app = FastAPI(
    title="Roblox User Info API",
    version="1.0-secure"
)

# =========================
# API KEY CHECK
# =========================
def verify_api_key(x_api_key: str):
    return x_api_key == API_KEY


# =========================
# FETCH ROBLOX API
# =========================
async def fetch(client, url, method="GET", payload=None):
    try:
        if method == "POST":
            res = await client.post(url, json=payload, timeout=10)
        else:
            res = await client.get(url, timeout=10)

        if res.status_code != 200:
            return None

        return res.json()
    except:
        return None


# =========================
# GET USER ID
# =========================
async def get_user_id(client, username):
    url = "https://users.roblox.com/v1/usernames/users"
    payload = {"usernames": [username], "excludeBannedUsers": True}
    r = await fetch(client, url, "POST", payload)
    return r["data"][0] if r and r.get("data") else None


# =========================
# GET USER DETAILS
# =========================
async def get_user_details(client, user_id):
    details = {}

    # Basic Info
    basic = await fetch(client, f"https://users.roblox.com/v1/users/{user_id}")
    details["basicInfo"] = basic
    details["accountCreationDate"] = basic.get("created") if basic else None

    # Avatar
    avatar = await fetch(
        client,
        f"https://thumbnails.roblox.com/v1/users/avatar-headshot"
        f"?userIds={user_id}&size=150x150&format=Png&isCircular=false"
    )
    details["avatar"] = avatar["data"][0]["imageUrl"] if avatar and avatar.get("data") else None

    # Friends
    friends = await fetch(client, f"https://friends.roblox.com/v1/users/{user_id}/friends")
    details["friendCount"] = len(friends.get("data", [])) if friends else 0

    # Followers
    followers = await fetch(client, f"https://friends.roblox.com/v1/users/{user_id}/followers/count")
    details["followersCount"] = followers.get("count", 0) if followers else 0

    # Premium
    premium = await fetch(client, f"https://premiumfeatures.roblox.com/v1/users/{user_id}/memberships")
    details["isPremium"] = bool(premium and premium.get("premiumMembership"))

    # Presence
    presence = await fetch(
        client,
        "https://presence.roblox.com/v1/presence/users",
        "POST",
        {"userIds": [user_id]}
    )
    details["presence"] = presence["userPresences"][0] if presence and presence.get("userPresences") else None

    # Username history
    history = await fetch(client, f"https://users.roblox.com/v1/users/{user_id}/username-history")
    details["usernameHistory"] = history.get("data", []) if history else []

    # Groups
    groups = await fetch(client, f"https://groups.roblox.com/v1/users/{user_id}/groups/roles")
    details["groups"] = groups.get("data", []) if groups else []

    # Badges
    badges = await fetch(
        client,
        f"https://badges.roblox.com/v1/users/{user_id}/badges?sortOrder=Desc&limit=10"
    )
    details["badges"] = badges.get("data", []) if badges else []

    # Favorite games
    favorites = await fetch(
        client,
        f"https://games.roblox.com/v1/users/{user_id}/favorite/games?limit=10"
    )
    details["favoriteGames"] = favorites.get("data", []) if favorites else []

    # Created games (empty nếu không cần)
    details["topGames"] = []

    return details


# =========================
# API ENDPOINT (SECURED)
# =========================
@app.get("/")
async def roblox_lookup(
    username: str = Query(None),
    x_api_key: str = Header(None)
):
    if not verify_api_key(x_api_key):
        return JSONResponse(
            status_code=401,
            content={
                "status": "error",
                "author": AUTHOR,
                "message": "Invalid API Key"
            }
        )

    if not username:
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "author": AUTHOR,
                "message": "Vui lòng cung cấp username."
            }
        )

    async with httpx.AsyncClient() as client:
        user = await get_user_id(client, username)
        if not user:
            return JSONResponse(
                status_code=404,
                content={
                    "status": "error",
                    "author": AUTHOR,
                    "message": "Không tìm thấy người dùng Roblox này."
                }
            )

        data = await get_user_details(client, user["id"])

    return {
        "status": "success",
        "author": AUTHOR,
        "data": data
    }