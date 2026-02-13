"""Steam 게이머 성향 카드 & 취향 분석기 - Streamlit 메인 앱"""

import re

import requests
import streamlit as st
import pandas as pd
import altair as alt
from streamlit_option_menu import option_menu

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

# ─── 페이지 설정 ──────────────────────────────────────────
st.set_page_config(
    page_title="Steam 게이머 성향 분석기",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CSS 스타일 (다크 게이밍 테마) ─────────────────────────
CSS_STYLES = """
<style>
/* ── Google Fonts ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap');

/* ── 전역 ── */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    color: #e6e6e6;
}
.stApp {
    background-color: #0e1117;
}

/* Streamlit 기본 헤더/푸터 숨김 */
header[data-testid="stHeader"] { display: none !important; }
footer { display: none !important; }
#MainMenu { display: none !important; }

/* ── 사이드바 ── */
section[data-testid="stSidebar"] {
    background-color: #0d1117;
    border-right: 1px solid #2d3548;
    min-width: 280px;
    max-width: 280px;
}
section[data-testid="stSidebar"] .block-container {
    padding-top: 1rem;
}

/* ── 사이드바 브랜드 ── */
.sidebar-brand {
    text-align: center;
    padding: 0.5rem 0 1rem 0;
    border-bottom: 1px solid #2d3548;
    margin-bottom: 1rem;
}
.sidebar-brand h2 {
    background: linear-gradient(135deg, #6c5ce7, #00cec9);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-size: 1.3rem;
    font-weight: 800;
    margin: 0;
    letter-spacing: -0.5px;
}
.sidebar-brand p {
    color: #8b95a5;
    font-size: 0.75rem;
    margin: 0.2rem 0 0 0;
}

/* ── 사이드바 분석 상태 ── */
.sidebar-status {
    background: #21273a;
    border: 1px solid #2d3548;
    border-radius: 12px;
    padding: 1rem;
    margin-top: 1.5rem;
    text-align: center;
}
.sidebar-status .status-emoji {
    font-size: 2rem;
}
.sidebar-status .status-type {
    color: #e6e6e6;
    font-weight: 700;
    font-size: 0.95rem;
    margin-top: 0.3rem;
}
.sidebar-status .status-tier {
    display: inline-block;
    padding: 2px 12px;
    border-radius: 20px;
    font-weight: 700;
    font-size: 0.8rem;
    margin-top: 0.4rem;
}

/* ── 히어로 섹션 ── */
.hero-section {
    text-align: center;
    padding: 3rem 0 2rem 0;
}
.hero-title {
    font-size: 2.8rem;
    font-weight: 800;
    background: linear-gradient(135deg, #6c5ce7, #00cec9);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0.5rem;
    line-height: 1.2;
}
.hero-subtitle {
    color: #8b95a5;
    font-size: 1.1rem;
    max-width: 600px;
    margin: 0 auto;
    line-height: 1.6;
}

/* ── 카드 컴포넌트 ── */
.g-card {
    background: #21273a;
    border: 1px solid #2d3548;
    border-radius: 16px;
    padding: 1.5rem;
    transition: all 0.3s ease;
    animation: fadeInUp 0.5s ease-out;
}
.g-card:hover {
    border-color: #6c5ce7;
    box-shadow: 0 0 20px rgba(108, 92, 231, 0.15);
    transform: translateY(-2px);
}

/* ── 미리보기 카드 (홈) ── */
.preview-cards {
    display: flex;
    gap: 1.5rem;
    justify-content: center;
    margin-top: 2rem;
    flex-wrap: wrap;
}
.preview-card {
    background: #21273a;
    border: 1px solid #2d3548;
    border-radius: 16px;
    padding: 2rem 1.5rem;
    text-align: center;
    flex: 1;
    min-width: 200px;
    max-width: 280px;
    transition: all 0.3s ease;
}
.preview-card:hover {
    border-color: #6c5ce7;
    box-shadow: 0 0 20px rgba(108, 92, 231, 0.15);
    transform: translateY(-2px);
}
.preview-card .card-icon {
    font-size: 2.5rem;
    margin-bottom: 0.8rem;
}
.preview-card .card-title {
    color: #e6e6e6;
    font-weight: 700;
    font-size: 1.1rem;
    margin-bottom: 0.4rem;
}
.preview-card .card-desc {
    color: #8b95a5;
    font-size: 0.85rem;
    line-height: 1.5;
}

/* ── 스탯 박스 ── */
.stat-box {
    background: #21273a;
    border: 1px solid #2d3548;
    border-left: 4px solid #6c5ce7;
    border-radius: 12px;
    padding: 1.2rem 1rem;
    text-align: center;
    animation: fadeInUp 0.5s ease-out;
}
.stat-box .stat-value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.6rem;
    font-weight: 700;
    color: #e6e6e6;
}
.stat-box .stat-label {
    color: #8b95a5;
    font-size: 0.8rem;
    margin-top: 0.2rem;
}

/* ── 티어 배지 ── */
.tier-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 56px;
    height: 56px;
    border-radius: 50%;
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.5rem;
    font-weight: 800;
    color: #fff;
    animation: glowPulse 2s ease-in-out infinite;
}

/* ── 장르 필 ── */
.genre-pill {
    display: inline-block;
    background: rgba(108, 92, 231, 0.2);
    border: 1px solid rgba(108, 92, 231, 0.4);
    color: #a29bfe;
    padding: 0.3rem 0.9rem;
    border-radius: 20px;
    font-size: 0.85rem;
    font-weight: 500;
    margin: 0.2rem;
}

/* ── 게임 추천 카드 ── */
.game-card {
    background: #21273a;
    border: 1px solid #2d3548;
    border-radius: 16px;
    overflow: hidden;
    transition: all 0.3s ease;
    animation: fadeInUp 0.5s ease-out;
    height: 100%;
}
.game-card:hover {
    border-color: #6c5ce7;
    box-shadow: 0 0 20px rgba(108, 92, 231, 0.15);
    transform: translateY(-2px);
}
.game-card-body {
    padding: 1rem 1.2rem 1.2rem 1.2rem;
}
.game-card-body .game-name {
    color: #e6e6e6;
    font-weight: 700;
    font-size: 1.05rem;
    margin-bottom: 0.3rem;
}
.game-card-body .game-genre {
    color: #8b95a5;
    font-size: 0.8rem;
    margin-bottom: 0.5rem;
}
.game-card-body .game-reason {
    color: #b0b8c8;
    font-size: 0.88rem;
    line-height: 1.5;
}

/* ── 분석 텍스트 카드 ── */
.analysis-card {
    background: #21273a;
    border: 1px solid #2d3548;
    border-radius: 16px;
    padding: 1.5rem;
    animation: fadeInUp 0.5s ease-out;
    height: 100%;
}
.analysis-card h4 {
    color: #e6e6e6;
    font-weight: 700;
    margin-bottom: 0.8rem;
}
.analysis-card p {
    color: #b0b8c8;
    line-height: 1.7;
    font-size: 0.95rem;
}

/* ── 정보 페이지 스텝 ── */
.info-step {
    background: #21273a;
    border: 1px solid #2d3548;
    border-radius: 16px;
    padding: 1.5rem;
    text-align: center;
    animation: fadeInUp 0.5s ease-out;
}
.info-step .step-number {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background: linear-gradient(135deg, #6c5ce7, #00cec9);
    color: #fff;
    font-weight: 800;
    font-size: 1.1rem;
    margin-bottom: 0.7rem;
}
.info-step .step-title {
    color: #e6e6e6;
    font-weight: 700;
    font-size: 1rem;
    margin-bottom: 0.3rem;
}
.info-step .step-desc {
    color: #8b95a5;
    font-size: 0.85rem;
    line-height: 1.5;
}

/* ── 인용 박스 ── */
.quote-box {
    background: rgba(108, 92, 231, 0.08);
    border-left: 4px solid #6c5ce7;
    border-radius: 0 12px 12px 0;
    padding: 1rem 1.2rem;
    color: #a29bfe;
    font-size: 1.05rem;
    font-weight: 600;
    font-style: italic;
    margin: 1rem 0;
}

/* ── 페이지 타이틀 ── */
.page-title {
    font-size: 1.8rem;
    font-weight: 800;
    background: linear-gradient(135deg, #6c5ce7, #00cec9);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0.3rem;
}
.page-subtitle {
    color: #8b95a5;
    font-size: 0.95rem;
    margin-bottom: 1.5rem;
}

/* ── 버튼 커스텀 ── */
div.stButton > button[kind="primary"],
div.stDownloadButton > button {
    background: linear-gradient(135deg, #6c5ce7, #00cec9) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 12px !important;
    font-weight: 700 !important;
    padding: 0.6rem 1.5rem !important;
    transition: all 0.3s ease !important;
}
div.stButton > button[kind="primary"]:hover,
div.stDownloadButton > button:hover {
    filter: brightness(1.15) !important;
    box-shadow: 0 0 20px rgba(108, 92, 231, 0.3) !important;
}

/* ── Altair 차트 투명 배경 ── */
.vega-embed {
    background: transparent !important;
}
.vega-embed .vega-bind-name {
    color: #8b95a5 !important;
}

/* ── 애니메이션 ── */
@keyframes fadeInUp {
    from {
        opacity: 0;
        transform: translateY(16px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}
@keyframes glowPulse {
    0%, 100% { box-shadow: 0 0 8px rgba(108, 92, 231, 0.4); }
    50% { box-shadow: 0 0 20px rgba(108, 92, 231, 0.7); }
}

/* ── option-menu 오버라이드 ── */
div[data-testid="stSidebar"] .nav-link {
    color: #8b95a5 !important;
    border-radius: 10px !important;
    margin: 2px 0 !important;
}
div[data-testid="stSidebar"] .nav-link:hover {
    color: #e6e6e6 !important;
    background-color: rgba(108, 92, 231, 0.1) !important;
}
div[data-testid="stSidebar"] .nav-link-selected {
    background: linear-gradient(135deg, #6c5ce7, #00cec9) !important;
    color: #ffffff !important;
    font-weight: 700 !important;
}

/* ── 메인 영역 패딩 ── */
.block-container {
    padding-top: 1.5rem;
    padding-bottom: 2rem;
}

/* ── link_button 스타일 ── */
div.stLinkButton > a {
    background: linear-gradient(135deg, #6c5ce7, #00cec9) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
}
div.stLinkButton > a:hover {
    filter: brightness(1.15) !important;
}

/* ── text_input 다크 테마 ── */
div[data-testid="stTextInput"] input {
    background-color: #21273a !important;
    color: #e6e6e6 !important;
    border: 1px solid #2d3548 !important;
    border-radius: 10px !important;
}
div[data-testid="stTextInput"] input:focus {
    border-color: #6c5ce7 !important;
    box-shadow: 0 0 0 1px #6c5ce7 !important;
}

/* ── 크레딧 ── */
.credits {
    text-align: center;
    color: #8b95a5;
    font-size: 0.8rem;
    margin-top: 2rem;
    padding-top: 1rem;
    border-top: 1px solid #2d3548;
}
</style>
"""

st.markdown(CSS_STYLES, unsafe_allow_html=True)


# ─── 기존 함수 (변경 없음) ─────────────────────────────────

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


# ─── 페이지 렌더 함수들 ───────────────────────────────────

def render_home_page():
    """홈 페이지: 히어로 + 입력 + 분석 트리거."""
    # 히어로 섹션
    st.markdown(
        """
        <div class="hero-section">
            <div class="hero-title">Steam 게이머 성향 분석기</div>
            <div class="hero-subtitle">
                Steam 프로필 URL을 입력하면 게임 라이브러리를 분석하여<br>
                <b>게이머 성향 카드</b>, <b>취향 분석 리포트</b>, <b>맞춤 게임 추천</b>을 제공합니다.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 입력 영역 (가운데 정렬)
    col_pad_l, col_input, col_pad_r = st.columns([1, 2, 1])
    with col_input:
        steam_url = st.text_input(
            "Steam 프로필 URL",
            placeholder="https://steamcommunity.com/id/유저이름 또는 Steam ID",
            label_visibility="collapsed",
        )
        if st.button("🔍 분석하기", type="primary", use_container_width=True):
            if not steam_url.strip():
                st.warning("Steam 프로필 URL을 입력해주세요.")
            else:
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

    # 미리보기 카드
    st.markdown(
        """
        <div class="preview-cards">
            <div class="preview-card">
                <div class="card-icon">🎴</div>
                <div class="card-title">성향 카드</div>
                <div class="card-desc">AI가 그린 초상화와 함께<br>나만의 게이머 성향 카드를 받아보세요</div>
            </div>
            <div class="preview-card">
                <div class="card-icon">📊</div>
                <div class="card-title">취향 분석</div>
                <div class="card-desc">장르 선호도, 플레이 패턴,<br>숨겨진 취향까지 깊이 있는 분석</div>
            </div>
            <div class="preview-card">
                <div class="card-icon">🎮</div>
                <div class="card-title">추천 게임</div>
                <div class="card-desc">분석된 취향을 바탕으로<br>딱 맞는 게임을 추천해드립니다</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _get_tier_color(tier: str) -> str:
    """티어에 해당하는 accent 색상 반환."""
    colors = TIER_COLORS.get(tier, TIER_COLORS["B"])
    return colors["accent"]


def render_card_page():
    """성향 카드 페이지: 초상화 + 정보 2컬럼."""
    if not st.session_state.get("analysis_complete"):
        st.info("먼저 홈 페이지에서 Steam 프로필을 분석해주세요.")
        return

    personality = st.session_state.personality
    portrait_image = st.session_state.portrait_image
    data = st.session_state.analysis_data
    tier_color = _get_tier_color(personality.tier)

    st.markdown('<div class="page-title">🎴 성향 카드</div>', unsafe_allow_html=True)

    col_img, col_info = st.columns([1, 1], gap="large")

    with col_img:
        st.image(portrait_image, use_container_width=True)

    with col_info:
        # 이모지 + 게이머 타입
        st.markdown(
            f"<h2 style='margin-top:0'>{personality.gamer_type_emoji} {personality.gamer_type}</h2>",
            unsafe_allow_html=True,
        )

        # 티어 배지
        st.markdown(
            f'<div class="tier-badge" style="background:{tier_color};">'
            f'{personality.tier}</div>',
            unsafe_allow_html=True,
        )

        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

        # 스탯 3종
        s1, s2, s3 = st.columns(3)
        with s1:
            st.markdown(
                f'<div class="stat-box">'
                f'<div class="stat-value">{personality.tier}</div>'
                f'<div class="stat-label">티어</div></div>',
                unsafe_allow_html=True,
            )
        with s2:
            st.markdown(
                f'<div class="stat-box">'
                f'<div class="stat-value">{data["total_playtime_hours"]:,.0f}h</div>'
                f'<div class="stat-label">플레이시간</div></div>',
                unsafe_allow_html=True,
            )
        with s3:
            st.markdown(
                f'<div class="stat-box">'
                f'<div class="stat-value">{data["total_games"]}</div>'
                f'<div class="stat-label">보유 게임</div></div>',
                unsafe_allow_html=True,
            )

        st.markdown("<div style='height:0.8rem'></div>", unsafe_allow_html=True)

        # 장르 필
        pills_html = "".join(
            f'<span class="genre-pill">{g}</span>' for g in personality.top_genres[:5]
        )
        st.markdown(pills_html, unsafe_allow_html=True)

        # 한줄 요약
        st.markdown(
            f'<div class="quote-box">"{personality.one_line_summary}"</div>',
            unsafe_allow_html=True,
        )

        # 다운로드 버튼
        portrait_bytes = card_to_bytes(portrait_image)
        st.download_button(
            label="📥 카드 이미지 다운로드 (PNG)",
            data=portrait_bytes,
            file_name="steam_gamer_card.png",
            mime="image/png",
            use_container_width=True,
        )


def render_analysis_page():
    """취향 분석 페이지: 메트릭 + 차트 + 분석 텍스트."""
    if not st.session_state.get("analysis_complete"):
        st.info("먼저 홈 페이지에서 Steam 프로필을 분석해주세요.")
        return

    personality = st.session_state.personality
    data = st.session_state.analysis_data
    tier_color = _get_tier_color(personality.tier)

    # 페이지 헤더
    st.markdown(
        f'<div class="page-title">{personality.gamer_type_emoji} {personality.gamer_type}</div>'
        f'<div class="page-subtitle">"{personality.one_line_summary}"</div>',
        unsafe_allow_html=True,
    )

    # 4개 메트릭
    play_rate = (
        round(data["played_games"] / data["total_games"] * 100)
        if data["total_games"] > 0
        else 0
    )

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(
            f'<div class="stat-box" style="border-left-color:{tier_color}">'
            f'<div class="stat-value">{personality.tier}</div>'
            f'<div class="stat-label">티어</div></div>',
            unsafe_allow_html=True,
        )
    with m2:
        st.markdown(
            f'<div class="stat-box" style="border-left-color:{tier_color}">'
            f'<div class="stat-value">{data["total_playtime_hours"]:,.0f}h</div>'
            f'<div class="stat-label">총 플레이시간</div></div>',
            unsafe_allow_html=True,
        )
    with m3:
        st.markdown(
            f'<div class="stat-box" style="border-left-color:{tier_color}">'
            f'<div class="stat-value">{data["total_games"]}</div>'
            f'<div class="stat-label">보유 게임</div></div>',
            unsafe_allow_html=True,
        )
    with m4:
        st.markdown(
            f'<div class="stat-box" style="border-left-color:{tier_color}">'
            f'<div class="stat-value">{play_rate}%</div>'
            f'<div class="stat-label">플레이율</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)

    # 장르 선호도 분석
    st.markdown(
        '<div class="analysis-card"><h4>🎯 장르 선호도 분석</h4>'
        f'<p>{personality.genre_analysis}</p></div>',
        unsafe_allow_html=True,
    )

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    # 장르 분포 차트
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
            .configure_view(strokeWidth=0)
            .configure_axis(
                labelColor="#8b95a5",
                titleColor="#8b95a5",
                gridColor="#2d3548",
            )
        )
        st.altair_chart(chart, use_container_width=True)

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    # 플레이 패턴 + 숨겨진 취향 (2컬럼)
    col_pattern, col_hidden = st.columns(2, gap="large")
    with col_pattern:
        st.markdown(
            '<div class="analysis-card"><h4>🕹️ 플레이 패턴</h4>'
            f'<p>{personality.play_pattern}</p></div>',
            unsafe_allow_html=True,
        )
    with col_hidden:
        st.markdown(
            '<div class="analysis-card"><h4>🔮 숨겨진 취향</h4>'
            f'<p>{personality.hidden_preference}</p></div>',
            unsafe_allow_html=True,
        )


def render_recommendations_page():
    """추천 게임 페이지: 2컬럼 카드 그리드."""
    if not st.session_state.get("analysis_complete"):
        st.info("먼저 홈 페이지에서 Steam 프로필을 분석해주세요.")
        return

    recommendations = st.session_state.recommendations

    st.markdown(
        '<div class="page-title">🎮 맞춤 게임 추천</div>'
        '<div class="page-subtitle">당신의 취향을 기반으로 AI가 추천하는 게임입니다.</div>',
        unsafe_allow_html=True,
    )

    recs = recommendations.recommendations
    for i in range(0, len(recs), 2):
        cols = st.columns(2, gap="large")
        for j, col in enumerate(cols):
            idx = i + j
            if idx >= len(recs):
                break
            rec = recs[idx]

            # appid 결정
            appid = rec.appid
            if not appid:
                m = re.search(r"/app/(\d+)", rec.steam_url)
                if m:
                    appid = int(m.group(1))

            with col:
                # 게임 이미지
                _show_game_image(appid)
                # 카드 내용
                st.markdown(
                    f'<div class="game-card-body">'
                    f'<div class="game-name">{rec.name}</div>'
                    f'<div class="game-genre">장르: {rec.match_genre}</div>'
                    f'<div class="game-reason">{rec.reason}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                st.link_button("Steam 스토어", rec.steam_url, use_container_width=True)
                st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)


def render_info_page():
    """정보 페이지: 이용 안내 + 크레딧."""
    st.markdown(
        '<div class="page-title">ℹ️ 이용 안내</div>'
        '<div class="page-subtitle">Steam 게이머 성향 분석기 사용 방법</div>',
        unsafe_allow_html=True,
    )

    # 4단계 안내
    steps = [
        ("1", "🔗 URL 입력", "Steam 프로필 URL을 홈 페이지에 입력합니다."),
        ("2", "🤖 AI 분석", "GPT-4o가 게임 라이브러리를 분석하고 성향을 파악합니다."),
        ("3", "📊 결과 확인", "성향 카드, 취향 분석, 추천 게임을 확인합니다."),
        ("4", "📥 카드 다운로드", "DALL-E 3가 그린 나만의 성향 카드를 다운로드합니다."),
    ]

    cols = st.columns(4, gap="medium")
    for col, (num, title, desc) in zip(cols, steps):
        with col:
            st.markdown(
                f'<div class="info-step">'
                f'<div class="step-number">{num}</div>'
                f'<div class="step-title">{title}</div>'
                f'<div class="step-desc">{desc}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.markdown("<div style='height:2rem'></div>", unsafe_allow_html=True)

    # 크레딧
    st.markdown(
        """
        <div class="credits">
            <b>Powered by</b><br>
            Steam Web API &nbsp;·&nbsp; OpenAI GPT-4o-mini &nbsp;·&nbsp; DALL-E 3 &nbsp;·&nbsp; Streamlit<br><br>
            게임 데이터는 Steam Web API에서 실시간으로 가져오며,<br>
            AI 분석에는 OpenAI의 GPT-4o-mini와 DALL-E 3 모델이 사용됩니다.
        </div>
        """,
        unsafe_allow_html=True,
    )


# ─── 사이드바 + 페이지 디스패치 ────────────────────────────

steam_key, openai_key = get_api_keys()

with st.sidebar:
    # 브랜드
    st.markdown(
        """
        <div class="sidebar-brand">
            <h2>🎮 STEAM ANALYZER</h2>
            <p>게이머 성향 분석기</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    selected = option_menu(
        menu_title=None,
        options=["홈", "성향 카드", "취향 분석", "추천 게임", "정보"],
        icons=[
            "house-fill",
            "person-badge-fill",
            "bar-chart-fill",
            "controller",
            "info-circle-fill",
        ],
        default_index=0,
        styles={
            "container": {
                "padding": "0 !important",
                "background-color": "transparent",
            },
            "icon": {"font-size": "1rem"},
            "nav-link": {
                "font-size": "0.95rem",
                "text-align": "left",
                "margin": "2px 0",
                "padding": "0.6rem 1rem",
                "border-radius": "10px",
                "color": "#8b95a5",
                "--hover-color": "rgba(108, 92, 231, 0.1)",
            },
            "nav-link-selected": {
                "background": "linear-gradient(135deg, #6c5ce7, #00cec9)",
                "color": "#ffffff",
                "font-weight": "700",
            },
            "separator": {"margin": "0.5rem 0"},
        },
    )

    # 분석 완료 시 사이드바 하단 상태
    if st.session_state.get("analysis_complete"):
        p = st.session_state.personality
        tier_color = _get_tier_color(p.tier)
        st.markdown(
            f'<div class="sidebar-status">'
            f'<div class="status-emoji">{p.gamer_type_emoji}</div>'
            f'<div class="status-type">{p.gamer_type}</div>'
            f'<div class="status-tier" style="background:{tier_color};color:#fff;">'
            f'Tier {p.tier}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

# 페이지 디스패치
if selected == "홈":
    render_home_page()
elif selected == "성향 카드":
    render_card_page()
elif selected == "취향 분석":
    render_analysis_page()
elif selected == "추천 게임":
    render_recommendations_page()
elif selected == "정보":
    render_info_page()
