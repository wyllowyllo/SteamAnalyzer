"""GPT-4o 기반 맞춤 게임 추천 모듈"""

from pydantic import BaseModel
from openai import OpenAI


class GameRecommendation(BaseModel):
    name: str  # 게임명
    steam_url: str  # Steam 스토어 URL
    reason: str  # 추천 이유 (1-2문장, 한글)
    match_genre: str  # 매칭 장르


class RecommendationList(BaseModel):
    recommendations: list[GameRecommendation]  # 5-10개


def get_recommendations(
    data: dict, personality, api_key: str
) -> RecommendationList:
    """GPT-4o로 보유 게임 제외한 맞춤 추천 생성.

    Args:
        data: prepare_analysis_data()의 반환값
        personality: GamerPersonality 인스턴스
        api_key: OpenAI API 키
    """
    owned_names = ", ".join(data["all_game_names"][:80])

    top_games_text = "\n".join(
        f"- {g['name']} ({g['playtime_hours']}시간, 장르: {', '.join(g['genres']) if g['genres'] else '?'})"
        for g in data["top_games"][:10]
    )

    genre_text = "\n".join(
        f"- {genre}: {hours:.1f}시간"
        for genre, hours in data["genre_distribution"][:8]
    )

    system_prompt = """당신은 Steam 게임 추천 전문가입니다.
게이머의 플레이 데이터와 성향 분석을 기반으로 맞춤형 게임을 추천해주세요.

규칙:
- 반드시 Steam에서 구매 가능한 실제 게임만 추천
- steam_url은 "https://store.steampowered.com/app/앱ID/게임명/" 형식 (정확한 URL을 모르면 게임명 기반으로 구성)
- 이미 보유한 게임은 절대 추천하지 않기
- 추천 이유는 한국어로, 해당 게이머의 취향과 연결지어 설명
- 다양한 장르에서 추천하되 선호 장르 비중을 높게
- 5~8개의 게임을 추천"""

    user_prompt = f"""다음 게이머에게 맞춤 게임을 추천해주세요.

## 게이머 성향
- 유형: {personality.gamer_type}
- 분석: {personality.genre_analysis}
- 숨겨진 취향: {personality.hidden_preference}
- Top 장르: {', '.join(personality.top_genres)}

## 가장 많이 플레이한 게임
{top_games_text}

## 장르 분포
{genre_text}

## 이미 보유한 게임 (추천 제외 대상)
{owned_names}"""

    client = OpenAI(api_key=api_key)
    response = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format=RecommendationList,
        temperature=0.9,
    )

    return response.choices[0].message.parsed
