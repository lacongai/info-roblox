from flask import Flask, request, jsonify
import requests

app = Flask(__name__)


def fetch_from_roblox_api(url, method="GET", payload=None):
    headers = {
        "Content-Type": "application/json"
    }

    try:
        if method == "POST":
            response = requests.post(url, json=payload, headers=headers, timeout=10)
        else:
            response = requests.get(url, headers=headers, timeout=10)

        if response.status_code != 200:
            print(f"[ERROR] Fetch failed {url} | Status {response.status_code}")
            return None

        return response.json()
    except Exception as e:
        print(f"[EXCEPTION] {url} -> {e}")
        return None


def get_user_id_by_username(username):
    url = "https://users.roblox.com/v1/usernames/users"
    payload = {
        "usernames": [username],
        "excludeBannedUsers": True
    }

    response = fetch_from_roblox_api(url, "POST", payload)
    if response and response.get("data"):
        return response["data"][0]
    return None


def get_user_details(user_id):
    details = {}

    # 1. Thông tin cơ bản
    basic_info = fetch_from_roblox_api(
        f"https://users.roblox.com/v1/users/{user_id}"
    )
    details["basicInfo"] = basic_info
    details["accountCreationDate"] = basic_info.get("created") if basic_info else None

    # 2. Avatar
    avatar = fetch_from_roblox_api(
        f"https://thumbnails.roblox.com/v1/users/avatar-headshot"
        f"?userIds={user_id}&size=150x150&format=Png&isCircular=false"
    )
    details["avatar"] = (
        avatar["data"][0]["imageUrl"]
        if avatar and avatar.get("data")
        else None
    )

    # 3. Bạn bè
    friends = fetch_from_roblox_api(
        f"https://friends.roblox.com/v1/users/{user_id}/friends"
    )
    details["friendCount"] = len(friends.get("data", [])) if friends else 0

    # 4. Followers
    followers = fetch_from_roblox_api(
        f"https://friends.roblox.com/v1/users/{user_id}/followers/count"
    )
    details["followersCount"] = followers.get("count", 0) if followers else 0

    # 5. Premium
    premium = fetch_from_roblox_api(
        f"https://premiumfeatures.roblox.com/v1/users/{user_id}/memberships"
    )
    details["isPremium"] = bool(
        premium and premium.get("premiumMembership") is True
    )

    # 6. Presence
    presence = fetch_from_roblox_api(
        "https://presence.roblox.com/v1/presence/users",
        "POST",
        {"userIds": [user_id]}
    )
    details["presence"] = (
        presence["userPresences"][0]
        if presence and presence.get("userPresences")
        else None
    )

    # 7. Username history
    username_history = fetch_from_roblox_api(
        f"https://users.roblox.com/v1/users/{user_id}/username-history"
    )
    details["usernameHistory"] = username_history.get("data", []) if username_history else []

    # 8. Groups
    groups = fetch_from_roblox_api(
        f"https://groups.roblox.com/v1/users/{user_id}/groups/roles"
    )
    details["groups"] = groups.get("data", []) if groups else []

    # 9. Badges
    badges = fetch_from_roblox_api(
        f"https://badges.roblox.com/v1/users/{user_id}/badges?sortOrder=Desc&limit=10"
    )
    details["badges"] = badges.get("data", []) if badges else []

    # 10. Favorite games
    favorites = fetch_from_roblox_api(
        f"https://games.roblox.com/v1/users/{user_id}/favorite/games?limit=10"
    )
    details["favoriteGames"] = favorites.get("data", []) if favorites else []

    # 11. Games đã tạo (top players)
    games = fetch_from_roblox_api(
        f"https://games.roblox.com/v2/users/{user_id}/games?sortOrder=Asc&limit=100"
    )

    game_details = []

    if games and games.get("data"):
        for game in games["data"]:
            universe_id = game.get("universeId")
            place_id = game.get("rootPlaceId")

            game_info = fetch_from_roblox_api(
                f"https://games.roblox.com/v1/games?universeIds={universe_id}"
            )

            if game_info and game_info.get("data"):
                info = game_info["data"][0]
                game_details.append({
                    "name": info.get("name", "Unknown"),
                    "placeId": place_id,
                    "currentPlayers": info.get("playing", 0),
                    "totalVisits": info.get("visits", 0),
                    "isPrivate": info.get("private", False)
                })

    game_details.sort(key=lambda x: x["currentPlayers"], reverse=True)
    details["topGames"] = game_details

    return details


@app.route("/", methods=["GET"])
def api():
    username = request.args.get("username")

    if not username:
        return jsonify({
            "status": "error",
            "message": "Vui lòng cung cấp username."
        }), 400

    user_info = get_user_id_by_username(username)

    if not user_info:
        return jsonify({
            "status": "error",
            "message": "Không tìm thấy người dùng Roblox này."
        }), 404

    user_id = user_info["id"]
    details = get_user_details(user_id)

    return jsonify({
        "status": "success",
        "data": details
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)