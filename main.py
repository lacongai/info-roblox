from fastapi import FastAPI, Request, Path
from fastapi.responses import JSONResponse
import httpx
import os
from dotenv import load_dotenv
from typing import Optional

# ======================================================
# LOAD ENVIRONMENT VARIABLES
# ======================================================
load_dotenv()

API_KEY = os.getenv("API_KEY", "henntaiiz_super").strip()
AUTHOR = "@henntaiiz"

# ======================================================
# FASTAPI APP INIT
# ======================================================
app = FastAPI(
    title="Roblox User Info API",
    version="1.1",
    description="Roblox User Information API (Readable Version)"
)

# ======================================================
# HELPER FUNCTION: FETCH DATA FROM ROBLOX API
# ======================================================
async def fetch_from_roblox(
    client: httpx.AsyncClient,
    url: str,
    method: str = "GET",
    payload: Optional[dict] = None
):
    """
    Send request to Roblox API safely.
    Returns JSON or None if failed.
    """
    try:
        if method == "POST":
            response = await client.post(
                url,
                json=payload,
                timeout=10
            )
        else:
            response = await client.get(
                url,
                timeout=10
            )

        if response.status_code != 200:
            return None

        return response.json()

    except Exception:
        return None


# ======================================================
# STEP 1: GET USER ID FROM USERNAME
# ======================================================
async def get_user_id_by_username(
    client: httpx.AsyncClient,
    username: str
):
    """
    Convert Roblox username -> userId
    """
    url = "https://users.roblox.com/v1/usernames/users"

    payload = {
        "usernames": [username],
        "excludeBannedUsers": True
    }

    data = await fetch_from_roblox(
        client=client,
        url=url,
        method="POST",
        payload=payload
    )

    if not data:
        return None

    if not data.get("data"):
        return None

    return data["data"][0]


# ======================================================
# STEP 2: GET FULL USER DETAILS
# ======================================================
async def get_user_details(
    client: httpx.AsyncClient,
    user_id: int
):
    """
    Collect all Roblox user information
    """
    result = {}

    # ---------------- BASIC INFO ----------------
    basic_info = await fetch_from_roblox(
        client,
        f"https://users.roblox.com/v1/users/{user_id}"
    )

    result["basicInfo"] = basic_info
    result["accountCreationDate"] = (
        basic_info.get("created")
        if basic_info else None
    )

    # ---------------- AVATAR ----------------
    avatar_data = await fetch_from_roblox(
        client,
        f"https://thumbnails.roblox.com/v1/users/avatar-headshot"
        f"?userIds={user_id}&size=150x150&format=Png&isCircular=false"
    )

    if avatar_data and avatar_data.get("data"):
        result["avatar"] = avatar_data["data"][0]["imageUrl"]
    else:
        result["avatar"] = None

    # ---------------- FRIEND COUNT ----------------
    friends_data = await fetch_from_roblox(
        client,
        f"https://friends.roblox.com/v1/users/{user_id}/friends"
    )

    if friends_data:
        result["friendCount"] = len(friends_data.get("data", []))
    else:
        result["friendCount"] = 0

    # ---------------- FOLLOWERS COUNT ----------------
    followers_data = await fetch_from_roblox(
        client,
        f"https://friends.roblox.com/v1/users/{user_id}/followers/count"
    )

    result["followersCount"] = (
        followers_data.get("count", 0)
        if followers_data else 0
    )

    # ---------------- PREMIUM STATUS ----------------
    premium_data = await fetch_from_roblox(
        client,
        f"https://premiumfeatures.roblox.com/v1/users/{user_id}/memberships"
    )

    result["isPremium"] = bool(
        premium_data and premium_data.get("premiumMembership")
    )

    # ---------------- PRESENCE ----------------
    presence_data = await fetch_from_roblox(
        client,
        "https://presence.roblox.com/v1/presence/users",
        method="POST",
        payload={"userIds": [user_id]}
    )

    if presence_data and presence_data.get("userPresences"):
        result["presence"] = presence_data["userPresences"][0]
    else:
        result["presence"] = None

    # ---------------- USERNAME HISTORY ----------------
    history_data = await fetch_from_roblox(
        client,
        f"https://users.roblox.com/v1/users/{user_id}/username-history"
    )

    result["usernameHistory"] = (
        history_data.get("data", [])
        if history_data else []
    )

    # ---------------- GROUPS ----------------
    groups_data = await fetch_from_roblox(
        client,
        f"https://groups.roblox.com/v1/users/{user_id}/groups/roles"
    )

    result["groups"] = (
        groups_data.get("data", [])
        if groups_data else []
    )

    # ---------------- BADGES ----------------
    badges_data = await fetch_from_roblox(
        client,
        f"https://badges.roblox.com/v1/users/{user_id}/badges?limit=10&sortOrder=Desc"
    )

    result["badges"] = (
        badges_data.get("data", [])
        if badges_data else []
    )

    # ---------------- FAVORITE GAMES ----------------
    fav_games = await fetch_from_roblox(
        client,
        f"https://games.roblox.com/v1/users/{user_id}/favorite/games?limit=10"
    )

    result["favoriteGames"] = (
        fav_games.get("data", [])
        if fav_games else []
    )

    # ---------------- TOP GAMES (PLACEHOLDER) ----------------
    result["topGames"] = []

    return result


# ======================================================
# VERIFY API KEY
# ======================================================
def is_valid_api_key(key: Optional[str]) -> bool:
    """
    Check API key correctness
    """
    if not key:
        return False

    if key.strip() != API_KEY:
        return False

    return True


# ======================================================
# MAIN ENDPOINT (SUPPORT 2 URL FORMATS)
# ======================================================
@app.get("/check/{param1}/{param2}")
async def check_roblox_user(
    request: Request,
    param1: str = Path(..., description="API Key or Username"),
    param2: str = Path(..., description="Username or API Key")
):
    # ---------------- DETECT API KEY ----------------
    if is_valid_api_key(param1):
        api_key = param1
        username = param2
    elif is_valid_api_key(param2):
        api_key = param2
        username = param1
    else:
        return JSONResponse(
            status_code=401,
            content={
                "status": "error",
                "author": AUTHOR,
                "message": "Invalid API key"
            }
        )

    # ---------------- FETCH USER DATA ----------------
    async with httpx.AsyncClient() as client:
        user = await get_user_id_by_username(client, username)

        if not user:
            return JSONResponse(
                status_code=404,
                content={
                    "status": "error",
                    "author": AUTHOR,
                    "message": "Roblox user not found"
                }
            )

        data = await get_user_details(client, user["id"])

    # ---------------- SUCCESS RESPONSE ----------------
    return {
        "status": "success",
        "author": AUTHOR,
        "data": data
    }


# ======================================================
# ROOT ENDPOINT (HEALTH CHECK)
# ======================================================
@app.get("/")
async def root():
    return {
        "message": "Roblox Info API is running",
        "usage": [
            "status": "success",
            "author": AUTHOR,
            "/check/API_KEY/USERNAME",
            "/check/USERNAME/API_KEY"
        ]
    }