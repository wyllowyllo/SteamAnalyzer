"""Steam API 연동 모듈 - 프로필 파싱, 게임 목록 조회, 장르 정보 수집"""

import re
import time
import requests
import streamlit as st


def parse_steam_url(url: str) -> tuple[str, str]:
    """Steam 프로필 URL 파싱.

    지원 형식:
    - https://steamcommunity.com/id/vanityname
    - https://steamcommunity.com/profiles/76561198012345678
    - 76561198012345678 (raw Steam ID)
    - vanityname (raw vanity name)

    Returns:
        (type, id) where type is "id64" or "vanity"
    """
    url = url.strip().rstrip("/")

    # /profiles/숫자 패턴
    m = re.search(r"steamcommunity\.com/profiles/(\d+)", url)
    if m:
        return ("id64", m.group(1))

    # /id/바니티 패턴
    m = re.search(r"steamcommunity\.com/id/([^/?#]+)", url)
    if m:
        return ("vanity", m.group(1))

    # 순수 숫자 (64bit Steam ID)
    if re.fullmatch(r"\d{17}", url):
        return ("id64", url)

    # 그 외 → vanity name으로 시도
    if url and not url.startswith("http"):
        return ("vanity", url)

    raise ValueError(
        "올바른 Steam 프로필 URL을 입력해주세요.\n\n"
        "지원 형식:\n"
        "- https://steamcommunity.com/id/유저이름\n"
        "- https://steamcommunity.com/profiles/76561198012345678\n"
        "- Steam ID (17자리 숫자)"
    )


def resolve_vanity_url(vanity: str, api_key: str) -> str:
    """바니티 URL을 64bit Steam ID로 변환."""
    resp = requests.get(
        "https://api.steampowered.com/ISteamUser/ResolveVanityURL/v1/",
        params={"key": api_key, "vanityurl": vanity},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json().get("response", {})
    if data.get("success") != 1:
        raise ValueError(
            f"'{vanity}' 유저를 찾을 수 없습니다.\n"
            "Steam 프로필 URL을 다시 확인해주세요."
        )
    return data["steamid"]


def get_steam_id(url: str, api_key: str) -> str:
    """URL에서 Steam 64bit ID를 추출/변환."""
    url_type, value = parse_steam_url(url)
    if url_type == "id64":
        return value
    return resolve_vanity_url(value, api_key)


def get_owned_games(steam_id: str, api_key: str) -> list[dict]:
    """소유 게임 목록 조회 (플레이시간 내림차순 정렬)."""
    resp = requests.get(
        "https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/",
        params={
            "key": api_key,
            "steamid": steam_id,
            "include_appinfo": True,
            "include_played_free_games": True,
            "format": "json",
        },
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json().get("response", {})

    if "games" not in data or len(data.get("games", [])) == 0:
        raise ValueError(
            "게임 라이브러리를 불러올 수 없습니다.\n\n"
            "**가능한 원인:**\n"
            "1. 프로필이 **비공개** 상태입니다\n"
            "2. 게임 세부 정보가 **비공개**로 설정되어 있습니다\n\n"
            "**해결 방법:**\n"
            "1. Steam → 프로필 → 프로필 편집 → 개인정보 설정\n"
            "2. **내 프로필** → `공개`\n"
            "3. **게임 세부 정보** → `공개`\n"
            "4. 변경 후 1-2분 대기 후 다시 시도해주세요"
        )

    games = data["games"]
    games.sort(key=lambda g: g.get("playtime_forever", 0), reverse=True)
    return games


@st.cache_data(ttl=3600, show_spinner=False)
def get_app_details(appid: int) -> dict | None:
    """Store API로 게임 상세 정보(장르, 태그) 조회."""
    try:
        resp = requests.get(
            "https://store.steampowered.com/api/appdetails",
            params={"appids": appid, "l": "korean"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        app_data = data.get(str(appid), {})
        if app_data.get("success"):
            detail = app_data.get("data", {})
            return {
                "genres": [g["description"] for g in detail.get("genres", [])],
                "categories": [c["description"] for c in detail.get("categories", [])],
                "short_description": detail.get("short_description", ""),
            }
    except Exception:
        pass
    return None


def enrich_games_with_details(
    games: list[dict], callback=None, max_games: int = 20
) -> list[dict]:
    """상위 게임들에 장르 정보를 추가.

    Args:
        games: 플레이시간 내림차순 정렬된 게임 목록
        callback: 진행률 콜백 함수 (current, total)
        max_games: 상세 조회할 최대 게임 수
    """
    top_games = games[:max_games]
    enriched = []

    for i, game in enumerate(top_games):
        appid = game.get("appid")
        details = get_app_details(appid)

        enriched_game = {
            "name": game.get("name", f"Unknown ({appid})"),
            "appid": appid,
            "playtime_hours": round(game.get("playtime_forever", 0) / 60, 1),
            "playtime_2weeks": round(game.get("playtime_2weeks", 0) / 60, 1),
        }

        if details:
            enriched_game["genres"] = details["genres"]
            enriched_game["categories"] = details["categories"]
            enriched_game["short_description"] = details["short_description"]
        else:
            enriched_game["genres"] = []
            enriched_game["categories"] = []
            enriched_game["short_description"] = ""

        enriched.append(enriched_game)

        if callback:
            callback(i + 1, len(top_games))

        # Store API rate limit 방지
        if i < len(top_games) - 1:
            time.sleep(0.3)

    return enriched


@st.cache_data(ttl=3600, show_spinner=False)
def search_steam_store(game_name: str) -> dict | None:
    """Steam Store 검색 API로 게임명을 검색하여 정확한 appid와 URL을 반환.

    Returns:
        {"appid": int, "name": str, "steam_url": str} 또는 None
    """
    try:
        resp = requests.get(
            "https://store.steampowered.com/api/storesearch/",
            params={"term": game_name, "l": "korean", "cc": "KR"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items", [])
        if items:
            top = items[0]
            appid = top["id"]
            return {
                "appid": appid,
                "name": top.get("name", game_name),
                "steam_url": f"https://store.steampowered.com/app/{appid}/",
            }
    except Exception:
        pass
    return None


def prepare_analysis_data(enriched_games: list[dict], all_games: list[dict]) -> dict:
    """LLM 입력용 데이터 가공."""
    total_playtime_hours = round(
        sum(g.get("playtime_forever", 0) for g in all_games) / 60, 1
    )
    total_games = len(all_games)
    played_games = sum(1 for g in all_games if g.get("playtime_forever", 0) > 0)

    # 장르 분포 계산
    genre_hours: dict[str, float] = {}
    for game in enriched_games:
        hours = game.get("playtime_hours", 0)
        for genre in game.get("genres", []):
            genre_hours[genre] = genre_hours.get(genre, 0) + hours

    genre_distribution = sorted(genre_hours.items(), key=lambda x: x[1], reverse=True)

    # 최근 2주 활동
    recent_games = [g for g in enriched_games if g.get("playtime_2weeks", 0) > 0]

    return {
        "total_playtime_hours": total_playtime_hours,
        "total_games": total_games,
        "played_games": played_games,
        "unplayed_games": total_games - played_games,
        "top_games": [
            {
                "name": g["name"],
                "playtime_hours": g["playtime_hours"],
                "genres": g.get("genres", []),
            }
            for g in enriched_games
        ],
        "genre_distribution": genre_distribution,
        "recent_games": [
            {"name": g["name"], "playtime_2weeks": g["playtime_2weeks"]}
            for g in recent_games
        ],
        "all_game_names": [g.get("name", "") for g in all_games[:100]],
    }
