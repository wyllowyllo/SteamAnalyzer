"""GPT-4o 기반 게이머 성향 분석 모듈"""

import json
from pydantic import BaseModel
from openai import OpenAI


class GamerPersonality(BaseModel):
    gamer_type: str  # 게이머 칭호 ("전략의 대가", "인디 탐험가" 등)
    gamer_type_english: str  # 영문 칭호 (DALL-E 프롬프트용)
    gamer_type_emoji: str  # 대표 이모지
    tier: str  # S/A/B/C/D
    genre_analysis: str  # 장르 선호도 분석 (3-5문장)
    play_pattern: str  # 플레이 패턴 분석 (3-5문장)
    hidden_preference: str  # 숨겨진 취향 (2-3문장)
    one_line_summary: str  # 한줄 요약 (20자 이내)
    top_genres: list[str]  # Top 3 장르
    portrait_prompt: str  # DALL-E용 영문 초상화 프롬프트


def calculate_tier(total_hours: float, total_games: int) -> str:
    """결정론적 티어 계산 (검증용 폴백)."""
    if total_hours >= 5000 and total_games >= 100:
        return "S"
    elif total_hours >= 2000 and total_games >= 50:
        return "A"
    elif total_hours >= 500 and total_games >= 20:
        return "B"
    elif total_hours >= 100 and total_games >= 10:
        return "C"
    else:
        return "D"


def analyze_gamer_profile(data: dict, api_key: str) -> GamerPersonality:
    """GPT-4o로 게이머 프로필 분석.

    Args:
        data: prepare_analysis_data()의 반환값
        api_key: OpenAI API 키
    """
    deterministic_tier = calculate_tier(
        data["total_playtime_hours"], data["total_games"]
    )

    top_games_text = "\n".join(
        f"- {g['name']}: {g['playtime_hours']}시간 (장르: {', '.join(g['genres']) if g['genres'] else '정보없음'})"
        for g in data["top_games"]
    )

    genre_text = "\n".join(
        f"- {genre}: {hours:.1f}시간" for genre, hours in data["genre_distribution"]
    )

    recent_text = "\n".join(
        f"- {g['name']}: 최근 2주 {g['playtime_2weeks']}시간"
        for g in data["recent_games"]
    ) or "최근 2주 플레이 기록 없음"

    system_prompt = """당신은 Steam 게임 데이터를 분석하는 게이머 프로파일링 전문가입니다.
주어진 게임 라이브러리 데이터를 분석하여 게이머의 성향, 취향, 플레이 패턴을 깊이있게 파악해주세요.

분석 시 주의사항:
- 한국어로 분석하되, gamer_type_english와 portrait_prompt는 영문으로 작성
- 게이머 칭호(gamer_type)는 창의적이고 재미있게 (예: "밤을 지새우는 전략가", "인디의 숨은 보석 사냥꾼")
- 숨겨진 취향은 장르 분포에서 의외의 패턴을 찾아 분석
- portrait_prompt는 게이머 성향을 상징하는 판타지 캐릭터 초상화를 묘사
- portrait_prompt 형식: "Fantasy character portrait of a [gamer type], [personality visual traits], wearing a stylish casual outfit with subtle fantasy armor accents and glowing enchanted accessories, holding [game-related items], semi-realistic digital painting, warm cinematic lighting, dreamy bokeh background with floating magical particles, RPG character select screen aesthetic, shoulder-up composition"
- one_line_summary는 반드시 20자 이내"""

    user_prompt = f"""다음 Steam 게이머 데이터를 분석해주세요.

## 기본 통계
- 총 플레이시간: {data['total_playtime_hours']:,.1f}시간
- 보유 게임: {data['total_games']}개
- 플레이한 게임: {data['played_games']}개
- 미플레이 게임: {data['unplayed_games']}개
- 산정 티어: {deterministic_tier} (S: 5000h+/100게임+, A: 2000h+/50게임+, B: 500h+/20게임+, C: 100h+/10게임+, D: 그 외)

## 가장 많이 플레이한 게임 (상위 20개)
{top_games_text}

## 장르별 플레이시간 분포
{genre_text}

## 최근 활동
{recent_text}

tier 값은 반드시 "{deterministic_tier}"로 설정해주세요."""

    client = OpenAI(api_key=api_key)
    response = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format=GamerPersonality,
        temperature=0.8,
    )

    result = response.choices[0].message.parsed

    # 티어 강제 보정
    if result.tier != deterministic_tier:
        result.tier = deterministic_tier

    return result
