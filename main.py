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
    version="1.1",
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

    basic = await fetch(client, f"https://users.roblox.com/v1/users/{user_id}")
    result["basicInfo"] = basic
    result["accountCreationDate"] = basic.get("created") if basic else None

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

    friends = await fetch(client, f"https://friends.roblox.com/v1/users/{user_id}/friends")
    result["friendCount"] = len(friends.get("data", [])) if friends else 0

    followers = await fetch(
        client,
        f"https://friends.roblox.com/v1/users/{user_id}/followers/count"
    )
    result["followersCount"] = followers.get("count", 0) if followers else 0

    premium = await fetch(
        client,
        f"https://premiumfeatures.roblox.com/v1/users/{user_id}/memberships"
    )
    result["isPremium"] = bool(premium and premium.get("premiumMembership"))

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

    history = await fetch(
        client,
        f"https://users.roblox.com/v1/users/{user_id}/username-history"
    )
    result["usernameHistory"] = history.get("data", []) if history else []

    groups = await fetch(
        client,
        f"https://groups.roblox.com/v1/users/{user_id}/groups/roles"
    )
    result["groups"] = groups.get("data", []) if groups else []

    badges = await fetch(
        client,
        f"https://badges.roblox.com/v1/users/{user_id}/badges?limit=10&sortOrder=Desc"
    )
    result["badges"] = badges.get("data", []) if badges else []

    fav = await fetch(
        client,
        f"https://games.roblox.com/v1/users/{user_id}/favorite/games?limit=10"
    )
    result["favoriteGames"] = fav.get("data", []) if fav else []

    result["topGames"] = []

    return result


# ======================================================
# VERIFY API KEY (AUTO DETECT)
# ======================================================
def verify_key(key: str) -> bool:
    return key.strip() == API_KEY


# ======================================================
# MAIN API ENDPOINT (SUPPORT 2 URL TYPES)
# ======================================================
@app.get("/check/{param1}/{param2}")
async def check_roblox_user(
    request: Request,
    param1: str = Path(...),
    param2: str = Path(...)
):
    # Auto detect which is API key
    if verify_key(param1):
        api_key = param1
        username = param2
    elif verify_key(param2):
        api_key = param2
        username = param1
    else:
        return JSONResponse(
            status_code=401,
            content={
                "status": "error",
                "author": AUTHOR,
                "message": "Invalid API key"
            },
            indent=2
        )

    async with httpx.AsyncClient() as client:
        user = await get_user_id(client, username)
        if not user:
            return JSONResponse(
                status_code=404,
                content={
                    "status": "error",
                    "author": AUTHOR,
                    "message": "Roblox user not found"
                },
                indent=2
            )

        data = await get_user_details(client, user["id"])

    return JSONResponse(
        content={
            "status": "success",
            "author": AUTHOR,
            "data": data
        },
        indent=2
    )


# ======================================================
# ROOT (HEALTH CHECK)
# ======================================================
@app.get("/")
async def root():
    return JSONResponse(
        content={
            "message": "Roblox Info API is running",
            "usage": [
                "/check/API_KEY/USERNAME",
                "/check/USERNAME/API_KEY"
            ]
        },
        indent=2
    )