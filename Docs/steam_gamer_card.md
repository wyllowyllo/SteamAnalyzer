# 프로젝트: Steam 게이머 성향 카드 & 취향 분석기

## 개요
Steam 프로필 URL만 입력하면 게임 라이브러리를 분석하여 게이머 성향 카드, 취향 분석 리포트, 맞춤 게임 추천을 제공하는 Streamlit 웹앱

## 기술 스택
- Python 3.11+
- Streamlit (단일 페이지 웹)
- Steam Web API (게임 목록, 플레이 시간)
- OpenAI API (GPT-4 + DALL-E 3) 또는 Gemini API
- Pillow (카드 이미지 합성)

## 핵심 기능

### 1. 입력
- Steam 프로필 URL 입력 (예: https://steamcommunity.com/id/username)
- 프로필 공개 여부 자동 체크 → 비공개 시 설정 가이드 안내

### 2. 데이터 수집
- Steam Web API로 소유 게임 목록 조회
- 게임별 플레이 시간 수집
- 플레이 시간 기준 상위 50개 필터링
- Steam Store API로 각 게임의 장르/태그 정보 수집

### 3. 출력물 (3종 세트)

#### ① 게이머 성향 카드 (이미지)
- 포토카드 스타일 세로형 이미지
- 포함 요소:
  - AI 생성 대표 이미지 (유저 취향 반영)
  - 게이머 타입 칭호 (예: "전략의 대가", "인디 탐험가", "좀비 헌터")
  - 주요 스탯 (총 플레이 시간, 게임 수, 선호 장르 Top 3)
  - 레벨/티어 뱃지

#### ② 취향 분석 리포트 (텍스트)
- 장르 선호도 분석 (차트 또는 텍스트)
- 플레이 패턴 분석 (장시간 몰입형 vs 다양하게 찍먹형)
- 숨겨진 취향 발견 (의외의 공통점)
- 게이머 성향 한줄 요약

#### ③ 추천 게임 리스트
- 라이브러리에 없는 게임 중 취향에 맞는 5~10개 추천
- 각 추천 게임 포함 정보:
  - 썸네일 이미지
  - 게임명 + Steam 링크
  - 추천 이유 (1-2문장)
  - 가격 정보 (가능하면)

### 4. 내보내기
- 성향 카드 PNG 다운로드
- 전체 리포트 이미지 다운로드
- (선택) 공유용 이미지 (SNS 최적화 사이즈)

## Steam API 사용법

### API Key 발급
- https://steamcommunity.com/dev/apikey 에서 발급 (무료)
- 개발자가 1개만 발급받아 서버에서 사용

### 주요 엔드포인트
```
# 프로필 URL에서 Steam ID 추출
GET api.steampowered.com/ISteamUser/ResolveVanityURL/v1/
    ?key={API_KEY}&vanityurl={username}

# 소유 게임 목록 + 플레이 시간
GET api.steampowered.com/IPlayerService/GetOwnedGames/v1/
    ?key={API_KEY}&steamid={STEAM_ID}&include_appinfo=1

# 게임 상세 정보 (장르, 태그)
GET store.steampowered.com/api/appdetails
    ?appids={APP_ID}
```

### 프로필 URL 파싱
```python
# 지원 형식
# https://steamcommunity.com/id/username
# https://steamcommunity.com/profiles/76561198xxxxxxxxx
```

## 파일 구조
```
project/
├── app.py                # Streamlit 메인
├── steam_api.py          # Steam API 연동 (게임 목록, 상세 정보)
├── analyzer.py           # LLM 분석 (성향 분류, 리포트 생성)
├── recommender.py        # 게임 추천 로직
├── card_generator.py     # 성향 카드 이미지 생성 (Pillow + DALL-E)
├── requirements.txt
└── .streamlit/
    └── secrets.toml      # API 키 관리
```

## API 키 관리
secrets.toml 사용:
- STEAM_API_KEY (필수)
- OPENAI_API_KEY 또는 GEMINI_API_KEY (필수)

## UI 플로우

### 메인 화면
1. 타이틀 + 간단한 설명
2. Steam 프로필 URL 입력창
3. "분석하기" 버튼

### 로딩 중
1. 프로그레스 바
2. 단계별 상태 표시:
   - "게임 라이브러리 불러오는 중..."
   - "장르 정보 수집 중..."
   - "취향 분석 중..."
   - "성향 카드 생성 중..."
   - "추천 게임 찾는 중..."

### 결과 화면 (탭 또는 섹션)
1. **성향 카드**: 이미지 + 다운로드 버튼
2. **취향 분석**: 텍스트 리포트 + 차트
3. **추천 게임**: 카드 그리드 (썸네일 + 링크)

## 제약사항
- Steam 프로필 "공개" 설정 필수
- 게임 수 많을 경우 플레이 시간 상위 50개만 분석
- Steam Store API rate limit 고려 (요청 간 딜레이)
- 일부 게임은 장르/태그 정보 없을 수 있음

## 에러 처리
- 프로필 비공개: 설정 변경 가이드 링크 제공
- 게임 0개: 안내 메시지
- API 실패: 재시도 버튼

## 평가
| 항목 | 평가 |
|------|------|
| 실현 가능성 | 🟢 90% |
| 시간 내 완성 | 🟢 가능 |
| 사용자 경험 | 🟢 최고 (URL만 입력) |
| 임팩트 | 🟢 높음 (3종 세트) |
| 바이럴 가능성 | 🟢 높음 (공유 욕구) |

## 참고
- 마감: 2025.02.13(금) 16:30
- 바이브코딩 해커톤 출품작
- 한글 UI 사용

## 개발 우선순위 (MVP)
1. Steam API 연동 + 게임 목록 조회
2. LLM 취향 분석 + 텍스트 리포트
3. 추천 게임 리스트
4. 성향 카드 이미지 생성
5. (시간 남으면) UI 다듬기, 공유 기능
