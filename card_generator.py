"""성향 카드 이미지 생성 모듈 - DALL-E 3 + Pillow 합성"""

import io
import requests
from PIL import Image, ImageDraw, ImageFont
from openai import OpenAI

# 티어별 색상 테마
TIER_COLORS = {
    "S": {"bg": "#1a0a2e", "accent": "#ff6b35", "text": "#ffffff"},
    "A": {"bg": "#0d1b2a", "accent": "#48bfe3", "text": "#ffffff"},
    "B": {"bg": "#1b2838", "accent": "#66bb6a", "text": "#ffffff"},
    "C": {"bg": "#2c2c2c", "accent": "#90a4ae", "text": "#e0e0e0"},
    "D": {"bg": "#3c3c3c", "accent": "#78909c", "text": "#e0e0e0"},
}

CARD_WIDTH = 600
CARD_HEIGHT = 900
PORTRAIT_HEIGHT = 400


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """한글 폰트 로드 (Windows 맑은 고딕)."""
    font_paths = []
    if bold:
        font_paths = [
            "C:/Windows/Fonts/malgunbd.ttf",
            "C:/Windows/Fonts/malgun.ttf",
        ]
    else:
        font_paths = [
            "C:/Windows/Fonts/malgun.ttf",
            "C:/Windows/Fonts/malgunbd.ttf",
        ]

    for path in font_paths:
        try:
            return ImageFont.truetype(path, size)
        except (OSError, IOError):
            continue

    # 폴백: 기본 폰트
    return ImageFont.load_default()


def generate_portrait(prompt: str, api_key: str) -> Image.Image | None:
    """DALL-E 3로 초상화 이미지 생성."""
    try:
        client = OpenAI(api_key=api_key)
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )
        image_url = response.data[0].url
        img_resp = requests.get(image_url, timeout=30)
        img_resp.raise_for_status()
        img = Image.open(io.BytesIO(img_resp.content))
        # 1024x1024 → 600x400 중앙 크롭
        img = img.resize((600, 600), Image.LANCZOS)
        top = (600 - PORTRAIT_HEIGHT) // 2
        img = img.crop((0, top, 600, top + PORTRAIT_HEIGHT))
        return img.convert("RGB")
    except Exception:
        return None


def generate_fallback_portrait(emoji: str, tier: str) -> Image.Image:
    """DALL-E 실패 시 그라데이션 + 이모지 폴백 이미지."""
    colors = TIER_COLORS.get(tier, TIER_COLORS["B"])
    bg_rgb = _hex_to_rgb(colors["bg"])
    accent_rgb = _hex_to_rgb(colors["accent"])

    img = Image.new("RGB", (CARD_WIDTH, PORTRAIT_HEIGHT))
    draw = ImageDraw.Draw(img)

    # 그라데이션 배경
    for y in range(PORTRAIT_HEIGHT):
        ratio = y / PORTRAIT_HEIGHT
        r = int(bg_rgb[0] * (1 - ratio) + accent_rgb[0] * ratio * 0.3)
        g = int(bg_rgb[1] * (1 - ratio) + accent_rgb[1] * ratio * 0.3)
        b = int(bg_rgb[2] * (1 - ratio) + accent_rgb[2] * ratio * 0.3)
        draw.line([(0, y), (CARD_WIDTH, y)], fill=(r, g, b))

    # 중앙에 이모지 텍스트
    try:
        emoji_font = ImageFont.truetype("C:/Windows/Fonts/seguiemj.ttf", 120)
    except (OSError, IOError):
        emoji_font = _load_font(120, bold=True)

    bbox = draw.textbbox((0, 0), emoji, font=emoji_font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x = (CARD_WIDTH - tw) // 2
    y = (PORTRAIT_HEIGHT - th) // 2
    draw.text((x, y), emoji, font=emoji_font, fill="white")

    return img


def _draw_tier_badge(draw: ImageDraw.Draw, tier: str, x: int, y: int, colors: dict):
    """티어 뱃지 그리기."""
    accent_rgb = _hex_to_rgb(colors["accent"])
    badge_size = 48
    # 원형 뱃지 배경
    draw.ellipse(
        [x, y, x + badge_size, y + badge_size],
        fill=accent_rgb,
    )
    # 티어 텍스트
    font = _load_font(28, bold=True)
    bbox = draw.textbbox((0, 0), tier, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    draw.text(
        (x + (badge_size - tw) // 2, y + (badge_size - th) // 2),
        tier,
        font=font,
        fill="white",
    )


def create_gamer_card(
    personality, data: dict, portrait: Image.Image | None, tier: str
) -> Image.Image:
    """최종 성향 카드 이미지 합성.

    Args:
        personality: GamerPersonality 인스턴스
        data: prepare_analysis_data() 반환값
        portrait: 초상화 이미지 (None이면 폴백 사용)
        tier: S/A/B/C/D
    """
    colors = TIER_COLORS.get(tier, TIER_COLORS["B"])
    bg_rgb = _hex_to_rgb(colors["bg"])
    accent_rgb = _hex_to_rgb(colors["accent"])
    text_rgb = _hex_to_rgb(colors["text"])

    # 카드 배경
    card = Image.new("RGB", (CARD_WIDTH, CARD_HEIGHT), bg_rgb)
    draw = ImageDraw.Draw(card)

    # 초상화 영역
    if portrait is None:
        portrait = generate_fallback_portrait(
            personality.gamer_type_emoji, tier
        )
    card.paste(portrait, (0, 0))

    # 초상화 하단 그라데이션 오버레이 (부드러운 전환)
    for y in range(60):
        alpha = int(255 * (y / 60))
        overlay_y = PORTRAIT_HEIGHT - 60 + y
        for x in range(CARD_WIDTH):
            orig = card.getpixel((x, overlay_y))
            r = int(orig[0] * (1 - alpha / 255) + bg_rgb[0] * (alpha / 255))
            g = int(orig[1] * (1 - alpha / 255) + bg_rgb[1] * (alpha / 255))
            b = int(orig[2] * (1 - alpha / 255) + bg_rgb[2] * (alpha / 255))
            card.putpixel((x, overlay_y), (r, g, b))

    # 정보 영역 시작
    info_y = PORTRAIT_HEIGHT + 15

    # 티어 뱃지 + 게이머 칭호
    _draw_tier_badge(draw, tier, 24, info_y, colors)

    title_font = _load_font(26, bold=True)
    title_text = f"{personality.gamer_type} {personality.gamer_type_emoji}"
    draw.text((84, info_y + 8), title_text, font=title_font, fill=text_rgb)

    # 구분선
    line_y = info_y + 62
    draw.line(
        [(24, line_y), (CARD_WIDTH - 24, line_y)],
        fill=accent_rgb,
        width=2,
    )

    # 통계 정보
    stat_font = _load_font(18, bold=False)
    stat_label_font = _load_font(18, bold=True)
    stat_y = line_y + 16

    stats = [
        ("총 플레이", f"{data['total_playtime_hours']:,.0f}시간"),
        ("보유 게임", f"{data['total_games']}개"),
        ("Top 장르", " / ".join(personality.top_genres[:3])),
    ]

    for label, value in stats:
        draw.text((36, stat_y), label, font=stat_label_font, fill=accent_rgb)
        draw.text((150, stat_y), value, font=stat_font, fill=text_rgb)
        stat_y += 34

    # 구분선 2
    line_y2 = stat_y + 8
    draw.line(
        [(24, line_y2), (CARD_WIDTH - 24, line_y2)],
        fill=accent_rgb,
        width=2,
    )

    # 한줄 요약
    summary_y = line_y2 + 20
    summary_font = _load_font(20, bold=True)
    summary_text = f'"{personality.one_line_summary}"'
    bbox = draw.textbbox((0, 0), summary_text, font=summary_font)
    tw = bbox[2] - bbox[0]
    draw.text(
        ((CARD_WIDTH - tw) // 2, summary_y),
        summary_text,
        font=summary_font,
        fill=accent_rgb,
    )

    # 하단 워터마크
    watermark_font = _load_font(12, bold=False)
    watermark = "Steam Gamer Card Generator"
    bbox = draw.textbbox((0, 0), watermark, font=watermark_font)
    tw = bbox[2] - bbox[0]
    draw.text(
        ((CARD_WIDTH - tw) // 2, CARD_HEIGHT - 30),
        watermark,
        font=watermark_font,
        fill=(*accent_rgb, 128) if len(accent_rgb) == 3 else accent_rgb,
    )

    return card


def card_to_bytes(card: Image.Image) -> bytes:
    """카드 이미지를 PNG 바이트로 변환."""
    buffer = io.BytesIO()
    card.save(buffer, format="PNG", quality=95)
    buffer.seek(0)
    return buffer.getvalue()
