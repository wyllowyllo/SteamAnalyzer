"""Steam 게이머 성향 카드 & 취향 분석기 - Streamlit 메인 앱"""

import re

import requests
import streamlit as st
import pandas as pd
import altair as alt

from steam_api import (
    get_steam_id,
    get_owned_games,
    enrich_games_with_details,
    prepare_analysis_data,
)
from analyzer import analyze_gamer_profile
from recommender import get_recommendations
from card_generator import (
    TIER_COLORS,
    generate_portrait,
    create_gamer_card,
    create_portrait_image,
    card_to_bytes,
)

# 페이지 설정
st.set_page_config(
    page_title="Steam 게이머 성향 카드",
    page_icon="🎮",
    layout="centered",
)


def get_api_keys() -> tuple[str, str]:
    """API 키 로드."""
    steam_key = st.secrets.get("STEAM_API_KEY", "")
    openai_key = st.secrets.get("OPENAI_API_KEY", "")
    if not steam_key or not openai_key:
        st.error(
            "API 키가 설정되지 않았습니다.\n\n"
            "`.streamlit/secrets.toml` 파일에 다음을 입력해주세요:\n\n"
            "```toml\n"
            'STEAM_API_KEY = "your-steam-api-key"\n'
            'OPENAI_API_KEY = "your-openai-api-key"\n'
            "```"
        )
        st.stop()
    return steam_key, openai_key


def run_analysis(steam_url: str, steam_key: str, openai_key: str):
    """전체 분석 파이프라인 실행."""
    with st.status("분석을 시작합니다...", expanded=True) as status:
        # 1. Steam ID 확인
        status.update(label="🔗 Steam 프로필 연결 중...")
        st.write("Steam 프로필을 확인하고 있습니다...")
        steam_id = get_steam_id(steam_url, steam_key)
        st.write(f"Steam ID: `{steam_id}` 확인 완료")

        # 2. 게임 라이브러리 로드
        status.update(label="📚 게임 라이브러리 불러오는 중...")
        st.write("게임 목록을 가져오고 있습니다...")
        all_games = get_owned_games(steam_id, steam_key)
        st.write(f"총 **{len(all_games)}**개 게임 발견")

        # 3. 장르 정보 수집 (상위 20개)
        status.update(label="🏷️ 장르 정보 수집 중...")
        progress_bar = st.progress(0, text="게임 상세 정보를 수집하고 있습니다...")

        def on_progress(current, total):
            progress_bar.progress(
                current / total,
                text=f"게임 상세 정보 수집 중... ({current}/{total})",
            )

        enriched = enrich_games_with_details(all_games, callback=on_progress)
        progress_bar.progress(1.0, text="장르 정보 수집 완료!")

        # 4. 분석 데이터 준비
        analysis_data = prepare_analysis_data(enriched, all_games)

        # 5. AI 취향 분석
        status.update(label="🤖 AI 취향 분석 중...")
        st.write("GPT-4o가 게이머 성향을 분석하고 있습니다...")
        personality = analyze_gamer_profile(analysis_data, openai_key)
        st.write(f"분석 완료: **{personality.gamer_type}** {personality.gamer_type_emoji}")

        # 6. 추천 게임 생성
        status.update(label="🎯 추천 게임 생성 중...")
        st.write("맞춤 게임 추천을 준비하고 있습니다...")
        recommendations = get_recommendations(analysis_data, personality, openai_key)
        st.write(f"**{len(recommendations.recommendations)}**개 게임 추천 완료")

        # 7. 성향 카드 이미지 생성
        status.update(label="🎨 성향 카드 이미지 생성 중...")
        st.write("DALL-E 3가 초상화를 그리고 있습니다...")
        portrait = generate_portrait(personality.portrait_prompt, openai_key)
        if portrait:
            st.write("초상화 생성 완료!")
        else:
            st.write("초상화 생성 실패, 기본 이미지를 사용합니다.")

        portrait_image = create_portrait_image(
            personality, portrait, personality.tier
        )
        card_image = create_gamer_card(
            personality, analysis_data, portrait, personality.tier
        )

        status.update(label="✅ 분석 완료!", state="complete")

    # 세션에 결과 저장
    st.session_state.analysis_complete = True
    st.session_state.personality = personality
    st.session_state.recommendations = recommendations
    st.session_state.portrait_image = portrait_image
    st.session_state.card_image = card_image
    st.session_state.analysis_data = analysis_data


@st.cache_data(show_spinner=False)
def _fetch_header_image(appid: int) -> bytes | None:
    """Steam CDN에서 게임 헤더 이미지를 가져온다. 실패 시 None."""
    try:
        resp = requests.get(
            f"https://cdn.akamai.steamstatic.com/steam/apps/{appid}/header.jpg",
            timeout=5,
        )
        resp.raise_for_status()
        return resp.content
    except Exception:
        return None


def _show_game_image(appid: int | None):
    """게임 헤더 이미지를 표시하고, 실패 시 Steam 로고 폴백."""
    if appid:
        img_bytes = _fetch_header_image(appid)
        if img_bytes:
            st.image(img_bytes, use_container_width=True)
            return
    st.image(
        "https://store.steampowered.com/public/shared/images/header/logo_steam.svg",
        use_container_width=True,
    )


def display_results():
    """분석 결과를 3개 탭으로 표시."""
    personality = st.session_state.personality
    recommendations = st.session_state.recommendations
    portrait_image = st.session_state.portrait_image
    card_image = st.session_state.card_image
    data = st.session_state.analysis_data

    tab1, tab2, tab3 = st.tabs(["🎴 성향 카드", "📊 취향 분석", "🎮 추천 게임"])

    # 탭 1: 성향 카드
    with tab1:
        st.image(portrait_image, use_container_width=True)

        # 게이머 칭호
        st.markdown(
            f"### {personality.gamer_type_emoji} {personality.gamer_type}"
        )

        # 통계 메트릭
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("티어", personality.tier)
        with col2:
            st.metric("총 플레이시간", f"{data['total_playtime_hours']:,.0f}h")
        with col3:
            st.metric("보유 게임", f"{data['total_games']}개")

        # Top 장르
        st.markdown(
            f"**Top 장르:** {' / '.join(personality.top_genres[:3])}"
        )

        # 한줄 요약
        st.info(f'"{personality.one_line_summary}"')

        # 다운로드 버튼 (초상화 이미지)
        portrait_bytes = card_to_bytes(portrait_image)
        st.download_button(
            label="📥 카드 이미지 다운로드 (PNG)",
            data=portrait_bytes,
            file_name="steam_gamer_card.png",
            mime="image/png",
            use_container_width=True,
        )

    # 탭 2: 취향 분석
    with tab2:
        st.subheader(f"{personality.gamer_type_emoji} {personality.gamer_type}")
        st.caption(f'"{personality.one_line_summary}"')

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("티어", personality.tier)
        with col2:
            st.metric("총 플레이시간", f"{data['total_playtime_hours']:,.0f}h")
        with col3:
            st.metric("보유 게임", f"{data['total_games']}개")

        st.divider()

        st.markdown("#### 🎯 장르 선호도 분석")
        st.markdown(personality.genre_analysis)

        # 장르 분포 차트 (가로 막대)
        if data["genre_distribution"]:
            colors = TIER_COLORS.get(personality.tier, TIER_COLORS["B"])
            accent_color = colors["accent"]
            genre_df = pd.DataFrame(
                data["genre_distribution"][:10],
                columns=["장르", "플레이시간(h)"],
            )
            chart = (
                alt.Chart(genre_df)
                .mark_bar(cornerRadiusEnd=4)
                .encode(
                    x=alt.X("플레이시간(h):Q", title="플레이시간(h)"),
                    y=alt.Y("장르:N", sort="-x", title=None),
                    color=alt.value(accent_color),
                )
                .properties(height=max(len(genre_df) * 32, 200))
            )
            st.altair_chart(chart, use_container_width=True)

        st.markdown("#### 🕹️ 플레이 패턴")
        st.markdown(personality.play_pattern)

        st.markdown("#### 🔮 숨겨진 취향")
        st.markdown(personality.hidden_preference)

    # 탭 3: 추천 게임
    with tab3:
        st.subheader("🎯 맞춤 게임 추천")
        st.caption("당신의 취향을 기반으로 AI가 추천하는 게임입니다.")
        st.divider()

        for rec in recommendations.recommendations:
            with st.container():
                # appid 결정: 필드 우선, 없으면 steam_url에서 파싱
                appid = rec.appid
                if not appid:
                    m = re.search(r"/app/(\d+)", rec.steam_url)
                    if m:
                        appid = int(m.group(1))

                col_img, col_text, col_btn = st.columns([2, 3, 1])
                with col_img:
                    _show_game_image(appid)
                with col_text:
                    st.markdown(f"**{rec.name}**")
                    st.caption(f"장르: {rec.match_genre}")
                    st.markdown(rec.reason)
                with col_btn:
                    st.link_button("Steam 스토어", rec.steam_url, use_container_width=True)
                st.divider()


# ─── 메인 UI ────────────────────────────────────────────

st.title("🎮 Steam 게이머 성향 카드")
st.markdown(
    "Steam 프로필 URL을 입력하면 게임 라이브러리를 분석하여\n"
    "**게이머 성향 카드**, **취향 분석 리포트**, **맞춤 게임 추천**을 제공합니다."
)

steam_key, openai_key = get_api_keys()

steam_url = st.text_input(
    "Steam 프로필 URL",
    placeholder="https://steamcommunity.com/id/유저이름 또는 Steam ID",
)

if st.button("🔍 분석하기", type="primary", use_container_width=True):
    if not steam_url.strip():
        st.warning("Steam 프로필 URL을 입력해주세요.")
    else:
        # 이전 결과 초기화
        st.session_state.analysis_complete = False
        try:
            run_analysis(steam_url.strip(), steam_key, openai_key)
        except ValueError as e:
            st.error(str(e))
        except Exception as e:
            st.error(
                f"분석 중 오류가 발생했습니다.\n\n"
                f"**오류 내용:** {str(e)}\n\n"
                f"잠시 후 다시 시도해주세요."
            )

# 분석 결과 표시 (세션에 결과가 있을 때)
if st.session_state.get("analysis_complete"):
    st.divider()
    display_results()
