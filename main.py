from fastapi import FastAPI, Request, Path
from fastapi.responses import JSONResponse
import httpx
import os
from dotenv import load_dotenv

# ======================================================
# LOAD ENV
# ======================================================
load_dotenv()

API_KEY = os.getenv("API_KEY", "henntaiiz_super").strip()
AUTHOR = "@henntaiiz"

app = FastAPI(
    title="Roblox User Info API",
    version="1.0",
    description="Secure Roblox User Information API"
)

# ======================================================
# HELPER: FETCH ROBLOX API
# ======================================================
async def fetch(client: httpx.AsyncClient, url: str, method="GET", payload=None):
    try:
        if method == "POST":
            r = await client.post(url, json=payload, timeout=15)
        else:
            r = await client.get(url, timeout=15)

        if r.status_code != 200:
            return None

        return r.json()
    except Exception:
        return None


# ======================================================
# GET USER ID BY USERNAME
# ======================================================
async def get_user_id(client, username: str):
    url = "https://users.roblox.com/v1/usernames/users"
    payload = {
        "usernames": [username],
        "excludeBannedUsers": True
    }
    data = await fetch(client, url, "POST", payload)
    return data["data"][0] if data and data.get("data") else None


# ======================================================
# GET USER DETAILS
# ======================================================
async def get_user_details(client, user_id: int):
    result = {}

    # Basic info
    basic = await fetch(client, f"https://users.roblox.com/v1/users/{user_id}")
    result["basicInfo"] = basic
    result["accountCreationDate"] = basic.get("created") if basic else None

    # Avatar
    avatar = await fetch(
        client,
        f"https://thumbnails.roblox.com/v1/users/avatar-headshot"
        f"?userIds={user_id}&size=150x150&format=Png&isCircular=false"
    )
    result["avatar"] = (
        avatar["data"][0]["imageUrl"]
        if avatar and avatar.get("data")
        else None
    )

    # Friends
    friends = await fetch(client, f"https://friends.roblox.com/v1/users/{user_id}/friends")
    result["friendCount"] = len(friends.get("data", [])) if friends else 0

    # Followers
    followers = await fetch(
        client,
        f"https://friends.roblox.com/v1/users/{user_id}/followers/count"
    )
    result["followersCount"] = followers.get("count", 0) if followers else 0

    # Premium
    premium = await fetch(
        client,
        f"https://premiumfeatures.roblox.com/v1/users/{user_id}/memberships"
    )
    result["isPremium"] = bool(premium and premium.get("premiumMembership"))

    # Presence
    presence = await fetch(
        client,
        "https://presence.roblox.com/v1/presence/users",
        "POST",
        {"userIds": [user_id]}
    )
    result["presence"] = (
        presence["userPresences"][0]
        if presence and presence.get("userPresences")
        else None
    )

    # Username history
    history = await fetch(
        client,
        f"https://users.roblox.com/v1/users/{user_id}/username-history"
    )
    result["usernameHistory"] = history.get("data", []) if history else []

    # Groups
    groups = await fetch(
        client,
        f"https://groups.roblox.com/v1/users/{user_id}/groups/roles"
    )
    result["groups"] = groups.get("data", []) if groups else []

    # Badges
    badges = await fetch(
        client,
        f"https://badges.roblox.com/v1/users/{user_id}/badges?limit=10&sortOrder=Desc"
    )
    result["badges"] = badges.get("data", []) if badges else []

    # Favorite games
    fav = await fetch(
        client,
        f"https://games.roblox.com/v1/users/{user_id}/favorite/games?limit=10"
    )
    result["favoriteGames"] = fav.get("data", []) if fav else []

    result["topGames"] = []

    return result


# ======================================================
# VERIFY API KEY (HEADER / QUERY / PATH)
# ======================================================
def verify_key(request: Request, path_key: str | None = None):
    key = (
        request.headers.get("x-api-key")
        or request.query_params.get("key")
        or path_key
    )

    if not key or key.strip() != API_KEY:
        return False

    return True


# ======================================================
# MAIN API ENDPOINT
# ======================================================
@app.get("/check/{api_key}/{username}")
async def check_roblox_user(
    request: Request,
    api_key: str = Path(..., description="API Key"),
    username: str = Path(..., description="Roblox Username")
):
    if not verify_key(request, api_key):
        return JSONResponse(
            status_code=401,
            content={
                "Trạng thái": "lỗi",
                "Tác giả": AUTHOR,
                "message": "API khóa không hợp lệ"
            }
        )

    async with httpx.AsyncClient() as client:
        user = await get_user_id(client, username)
        if not user:
            return JSONResponse(
                status_code=404,
                content={
                    "Trạng thái": "lỗi",
                    "Tác giả": AUTHOR,
                    "message": "Không tìm thấy người dùng Roblox này."
                }
            )

        data = await get_user_details(client, user["id"])

    return {
        "Trạng thái": "thành công",
        "Tác giả": AUTHOR,
        "data": data
    }


# ======================================================
# ROOT (HEALTH CHECK)
# ======================================================
@app.get("/")
async def root():
    return {
        "message": "Roblox Info API is running",
        "usage": "/check/{api_key}/{username} or ?key=API_KEY&username=name"
    }