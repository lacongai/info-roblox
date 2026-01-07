from fastapi import FastAPI, Request, Path
from fastapi.responses import JSONResponse
import httpx
import os
import asyncio
from dotenv import load_dotenv
from typing import Optional, List, Dict, Any

# ======================================================
# LOAD ENVIRONMENT VARIABLES
# ======================================================
load_dotenv()

# API key mặc định lấy từ Environment của Render hoặc file .env
API_KEY = os.getenv("API_KEY", "henntaiiz_super").strip()
AUTHOR = "@henntaiiz"

app = FastAPI(
    title="Roblox User Info API",
    version="1.1.0",
    description="Optimized Roblox API with Parallel Data Fetching"
)

# ======================================================
# HELPER: FETCH DATA FROM ROBLOX API
# ======================================================
async def fetch_from_roblox(
    client: httpx.AsyncClient,
    url: str,
    method: str = "GET",
    payload: Optional[dict] = None
) -> Optional[dict]:
    try:
        if method.upper() == "POST":
            response = await client.post(url, json=payload, timeout=10)
        else:
            response = await client.get(url, timeout=10)
        
        if response.status_code == 200:
            return response.json()
        return None
    except Exception:
        return None

# ======================================================
# OPTIMIZED STEP 2: GET ALL DETAILS IN PARALLEL
# ======================================================
async def get_user_details(client: httpx.AsyncClient, user_id: int) -> Dict[str, Any]:
    """
    Sử dụng asyncio.gather để gọi tất cả API Roblox cùng một lúc, 
    giúp giảm đáng kể thời gian chờ (Latency).
    """
    # Định nghĩa danh sách các task cần lấy
    tasks = [
        fetch_from_roblox(client, f"https://users.roblox.com/v1/users/{user_id}"), # 0: Basic
        fetch_from_roblox(client, f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=150x150&format=Png&isCircular=false"), # 1: Avatar
        fetch_from_roblox(client, f"https://friends.roblox.com/v1/users/{user_id}/friends"), # 2: Friends
        fetch_from_roblox(client, f"https://friends.roblox.com/v1/users/{user_id}/followers/count"), # 3: Followers
        fetch_from_roblox(client, f"https://premiumfeatures.roblox.com/v1/users/{user_id}/memberships"), # 4: Premium
        fetch_from_roblox(client, f"https://presence.roblox.com/v1/presence/users", "POST", {"userIds": [user_id]}), # 5: Presence
        fetch_from_roblox(client, f"https://users.roblox.com/v1/users/{user_id}/username-history"), # 6: History
        fetch_from_roblox(client, f"https://groups.roblox.com/v1/users/{user_id}/groups/roles"), # 7: Groups
        fetch_from_roblox(client, f"https://badges.roblox.com/v1/users/{user_id}/badges?limit=10&sortOrder=Desc"), # 8: Badges
        fetch_from_roblox(client, f"https://games.roblox.com/v1/users/{user_id}/favorite/games?limit=10"), # 9: Favs
    ]

    # Chạy đồng thời
    results = await asyncio.gather(*tasks)

    # Giải nén kết quả
    basic = results[0] or {}
    avatar = results[1]
    friends = results[2]
    followers = results[3]
    premium = results[4]
    presence = results[5]
    history = results[6]
    groups = results[7]
    badges = results[8]
    fav = results[9]

    return {
        "basicInfo": basic,
        "accountCreationDate": basic.get("created"),
        "avatar": avatar["data"][0]["imageUrl"] if avatar and avatar.get("data") else None,
        "friendCount": len(friends.get("data", [])) if friends else 0,
        "followersCount": followers.get("count", 0) if followers else 0,
        "isPremium": bool(premium and premium.get("premiumMembership")),
        "presence": presence["userPresences"][0] if presence and presence.get("userPresences") else None,
        "usernameHistory": history.get("data", []) if history else [],
        "groups": groups.get("data", []) if groups else [],
        "badges": badges.get("data", []) if badges else [],
        "favoriteGames": fav.get("data", []) if fav else [],
        "topGames": []
    }

# ======================================================
# MAIN ENDPOINT
# ======================================================
@app.get("/check/{param1}/{param2}")
async def check_roblox_user(param1: str = Path(...), param2: str = Path(...)):
    # Logic nhận diện thông minh API Key và Username
    if param1 == API_KEY:
        username = param2
    elif param2 == API_KEY:
        username = param1
    else:
        return JSONResponse(status_code=401, content={
            "status": "error", "author": AUTHOR, "message": "Invalid API key"
        })

    async with httpx.AsyncClient() as client:
        # Bước 1: Tìm ID người dùng
        user_id_url = "https://users.roblox.com/v1/usernames/users"
        user_res = await fetch_from_roblox(client, user_id_url, "POST", {"usernames": [username], "excludeBannedUsers": True})
        
        if not user_res or not user_res.get("data"):
            return JSONResponse(status_code=404, content={
                "status": "error", "author": AUTHOR, "message": "Roblox user not found"
            })

        # Bước 2: Lấy thông tin chi tiết (Đã tối ưu chạy song song)
        data = await get_user_details(client, user_res["data"][0]["id"])

    return {
        "status": "success",
        "author": AUTHOR,
        "data": data
    }

@app.get("/")
async def root():
    return {"message": "Roblox API is Online", "author": AUTHOR}
