---
name: caracal-instagram-cardnews
description: 카라칼 서플라이(@caracal_supply) 공식 인스타그램용 정보성 카드뉴스를 자동으로 만드는 카라칼 전용 스킬. 주제 선정 → 운동정보 리서치 → 브랜드 톤 카피 → PNG 카드뉴스(1080×1350) 7장 생성 → 검수 → 캡션·해시태그 → (선택) Buffer 예약 큐까지 처리한다. "카드뉴스 만들어줘", "인스타 콘텐츠 제작", 주 2회 자동 발행 작업에 사용.
---

# 카라칼 인스타그램 카드뉴스 스킬

카라칼 서플라이 공식 인스타그램(@caracal_supply)에 올릴 **정보성 카드뉴스**를 end-to-end로 생성한다.
핵심 원칙: **"운동 정보를 먼저 주고, 카라칼 테이핑 양말은 보조로 자연스럽게 연결"** + **의학적 단정 금지**.

## 언제 쓰나
- "카라칼 카드뉴스 만들어줘 / 인스타 콘텐츠 제작해줘"
- 주 2회 자동 발행 스케줄(월·목 19:07)이 트리거할 때
- 특정 주제로 카드뉴스 1세트가 필요할 때

## 반드시 먼저 읽을 컨텍스트 (프로젝트 루트 기준)
- `marketing-agent/context/brand-guidelines.md` — 톤, 금지 표현, 해시태그(5~8개), 핸들
- `marketing-agent/context/design-style-guide.md` — 컬러/레이아웃/슬라이드 구성
- `marketing-agent/context/business-context.md` — 타깃, 페인포인트, 검증 수치
- `marketing-agent/output/topic-bank.md` — 주제 순환 큐 (여기서 주제를 꺼냄)
- (배경 지식) `/Users/zsho/카라칼 정보/카라칼_정보정리.md` — 제품·성과·기술 팩트 원본

## 산출물 위치
- PNG 7장: `marketing-agent/output/cardnews-<주제번호>/slide_01..07.png`
- 카피/캡션: `marketing-agent/output/card-news-copy.md` (또는 `-<번호>.md`)
- 슬라이드 스펙: `marketing-agent/output/cardnews-spec-<번호>.json`
- 검수 메모: `marketing-agent/output/review-<번호>.md`

---

## 실행 절차 (자동 발행 시 그대로 따른다)

### 1) 주제 선정
- `marketing-agent/output/topic-bank.md` 의 `대기` 상태 맨 위 주제 1개를 꺼낸다.
- 대기 주제가 3개 미만이면, WebSearch로 "인스타 저장·공유 잘 되는 운동 정보(러닝/등산/축구/발목·무릎·종아리 케어)" 최신 트렌드를 조사해 새 주제 5개를 큐 하단에 보충한다.

### 2) 리서치 (필요 시)
- 주제에 대한 근거가 부족하면 WebSearch로 2~3개 신뢰 출처 확보 (의학·스포츠의학·공신력 매체).
- 카라칼 제품과 연결 가능한 근거(예: 테이핑이 균형/고유수용감각 개선, 압박 15~25mmHg)를 찾는다.
- 핵심 팩트·출처를 `research-report.md`에 누적 기록.

### 3) 카피 작성 (브랜드 톤)
- 7슬라이드 구성: ①커버 ②문제공감 ③④⑤ 정보 STEP(또는 포인트) ⑥수치+자연연결 ⑦CTA
- 헤드라인 15~20자, 슬라이드당 메시지 1개, 본문 2~3문장.
- 금지: "치료/완치/통증이 사라진다" 등 의학적 단정, 경쟁사 비방, 근거 없는 최상급.
- 캡션 끝에 안전 문구 1줄 + 해시태그 5~8개(#카라칼 #CARACAL #테이핑양말 고정 + 종목/주제 태그).
- 결과를 `card-news-copy.md`에 저장.

### 4) 슬라이드 스펙 JSON 생성
`cardnews-spec-<번호>.json` 작성. 스키마(v2 — 사진·로고 마무리 지원):
```json
{
  "topic_id": "02",
  "title": "주제 짧은 제목",
  "accent": "#E5402F",
  "slides": [
    {"layout":"cover","photo":"<사진경로>","kicker":"...","headline":"두 줄\n가능","subtitle":"..."},
    {"layout":"photo","photo":"<사진경로>","kicker":"...","headline":"...","body":"..."},
    {"layout":"step","bg":"light","step":"STEP 1","headline":"...","body":"...","highlight":"강조 한 줄(선택)"},
    {"layout":"stat","bg":"dark","kicker":"...","big":"92%","biglabel":"...","body":"..."},
    {"layout":"summary","bg":"dark","headline":"...","items":["...","...","..."]},
    {"layout":"closing","bg":"dark","subtitle":"저장 유도 문구","cta":"프로필 링크 → 네이버 스마트스토어","handle":"@caracal_supply"}
  ]
}
```
- 레이아웃(v9 — **사진/글씨 완전 분리 + 균일 발란스**): `cover`/`photo` = **사진은 상단 약 59%(고정)에 cover로 깔끔히, 글씨는 하단 솔리드 다크 패널에 가운데정렬**(겹침 0, 사진 잘 보임). 텍스트가 많으면(정보박스) 그만큼만 사진을 줄여 자동 발란스. 경계 주황 라인. 사진별 `"focus"`(0~1)로 인물이 밴드에 잘 들어오게(잘림 방지). `closing`(공식 워드마크+아이콘 로고 페이지 — 마지막 장 필수).
  > 교훈: 풀블리드 텍스트오버레이는 "사진 위 글씨 겹침/사진 안 보임" 불만 → **사진 상단 고정밴드 + 텍스트 하단 패널 분리**가 정답(발란스 균일이 핵심).
- **사진 잘림 금지(v10, 매우 중요):** 사진은 `cover`(꽉채우기, 잘림)가 아니라 **`photo_band`=전체를 잘림없이(contain) 보여주고 빈 곳은 같은 사진의 흐릿한 배경(blurred-fill)으로 채움**. 인물이 머리~발끝 항상 온전히 노출. "사람은 사진에 먼저 반응→글씨→캡션" 순서라 사진을 절대 안 자른다.
- **★ 최종 채택(v11 — 사용자가 고른 @runninglife_korea/@cltoo.run 스타일):** **풀블리드 사진이 카드를 꽉 채우고**(blurred wings·상단밴드 분리 아님), **하단만 그라데이션으로 어둡게**(상단 사진 밝게), **하단 왼쪽정렬**로 라벨 pill → 제목(*별표* 키워드 주황) → 설명. infobox는 반투명 박스. **사진 프레이밍은 `focus`(0~1)로 슬라이드마다 조정**해 인물 머리~발끝 잘 들어오게(세로 전신컷 사용). 사진이 시각적으로 먼저 시선을 끌고 → 제목 → 캡션 순.
- **★ 사진/글씨 분리 발란스(핵심 노하우):** 인물이 하단까지 내려와 글씨와 바짝 붙으면 답답함. **focus를 높여 인물을 상단~중앙에 두고, 사진 하단(길·바닥 등)을 비워 그 위에 글씨**가 오게 한다(인물 위→여백→글씨 아래 흐름). 인물이 화면을 꽉 채운 컷(예: 정면 근접)은 focus를 낮춰 얼굴·상체 위주로 보이게. 생성 후 Read로 보고 슬라이드마다 focus 재조정 필수. (그래디언트 곡선 t^1.5: 상단 밝게→하단만 진하게)
- **★ 좌우(대각선) 발란스 + 반복감 줄이기:** 인물이 한쪽에 몰리면 글씨를 **반대쪽으로 정렬**해 대각선 균형(인물 왼쪽→글씨 오른쪽 등). 스펙 `"align"`: `left`/`center`/`right`(기본 left), `"focus_x"`(0~1, 단 세로로 긴 사진은 가로 크롭 여백이 없어 zoom>1과 함께 써야 효과). 슬라이드마다 정렬을 달리해 반복감도 줄인다(예: 커버 center, 인물 좌측 슬라이드 right, 나머지 left). 세로 사진은 focus_x 효과가 없으니 align으로 균형을 맞춘다.
- **요소(스펙 키):**
  - `kicker` → **주황 라벨 태그(pill)**, 헤드라인 위.
  - `headline` → 흰색 굵게 가운데정렬. **키워드만 `*별표*`로 감싸면 브랜드 주황 강조** (예: `"빠를수록\n*천천히* 달려라"`). 줄바꿈은 `\n`.
  - `subtitle`(cover) / `body`(photo) → 흰색, 어절 단위 `\n` 줄바꿈, 가운데정렬.
  - `infobox` → **반투명 라운드 정보박스**. `[{"label","value"}, ...]` 각 행 라벨=주황·값=흰색. 핵심 수치/공식/비교에 사용(예: 80/20, 심박공식, 92%).
  - `source` → 좌하단 작은 출처표기(예: "사진 Pexels").
  - `focus`(0~1)·`zoom`으로 인물 프레이밍.
- 워터마크 = 고양이 아이콘 **좌상단**(자동). accent 기본 `#EC561A`(어두운 배경용으로 공식 주황 살짝 밝게).
- 사진: **세로 풀바디/무드 컷**. 스크림이 강해 밝은 사진도 통일됨. 본문에 이모지·−·× 금지(□).
- 참고 계정 cltoo.run(8.9만 No.1 러닝미디어): 풀블리드 무드 + 키워드 강조 + 정보박스 + 섹션형 상세 캡션. 이 문법을 따른다.
- **분량: 8~12장(교육형 최적, 2026 알고리즘).** 너무 간결하면 저장·공유 안 됨. 각 장 = 헤드라인 + 본문 2~4줄(실질 정보 1덩이: 수치·체크리스트·근거).
- 콘텐츠 슬라이드는 전부 사진 배경(`photo`). 패널에 정보를 담되, 더 긴 디테일은 캡션으로.
- **마지막 직전 또는 마무리에 '저장+공유' 유도**(예: "저장하고 러닝메이트에게 공유해요"). 솔직한 단서(과장 X)로 신뢰·공유↑.
- **포인트 컬러 = 공식 브랜드 주황 `#E44E12`** (첨부 공식 워드마크에서 추출). 과거 #C8962A·#E5402F는 폐기.
- **브랜드 폰트**: 공식 워드마크 PDF(`Downloads/카라칼_주황_흰배경_테두리없음.pdf`)는 글자가 외곽선이라 폰트 파일 추출 불가 → **워드마크 이미지 자체를 인용**해서 사용(아래 에셋). 한글 헤드라인은 AppleSDGothicNeo Bold.
- **워터마크 = 카라칼 고양이 아이콘만**(글자 없음). 좌상단 작게 자동(`icon_white.png`/라이트bg는 `icon_orange.png`).
- 브랜드 에셋(`assets/brand/`): `icon_white.png`·`icon_orange.png`(고양이 아이콘=워터마크) / `wordmark_official_white.png`·`wordmark_official_orange.png`(공식 주황 워드마크=closing) / (구) logo_white·wordmark_white·logo_red 등.
- 사진: 프로젝트 루트 기준 상대경로로 `photo` 지정. Zone2 사진 6장: `assets/photos/zone2/{cover_sunset,silhouette,treelined,warmfield,roadrun,crew}.jpg`(Pexels, 무료 상업적 이용, SOURCES.txt 기록). 위에 가독성 그라데이션 자동.
- 새 주제용 사진은 Pexels(images.pexels.com) 무료 라이선스에서 WebFetch로 URL 추출→curl 저장. **세로형(>1200h) 우선.** 8~12장이면 사진도 그만큼 필요.
- **폰트 미지원 문자 금지(□ 깨짐): 이모지·−(U+2212 빼기)·×(곱하기). ASCII `-`,`x` 사용. 캡션엔 이모지 OK.**
- **브랜드 빌딩 미션**: 카드뉴스는 카라칼 브랜드를 키워가는 장기 자산. 매 발행 전문성·일관성·저장공유 설계를 지킨다.
- 어투: 친근하게(~해요/~죠/~예요). 딱딱한 설명체 지양.
- 줄바꿈은 헤드라인에 `\n`으로 명시.

### 5) PNG 생성
```bash
python3 ".claude/skills/caracal-instagram-cardnews/assets/cardnews_gen.py" \
  --spec "marketing-agent/output/cardnews-spec-<번호>.json" \
  --out  "marketing-agent/output/cardnews-<번호>"
```
- 의존성: Pillow(설치됨), 폰트 AppleSDGothicNeo(시스템 기본). 1080×1350 PNG 7장 출력.

### 6) 자가 검수 (review-agent 기준 축약)
생성된 PNG 1·3·6·7번을 Read로 시각 확인하고 체크:
- [ ] 텍스트 잘림/넘침 없음, 슬라이드당 메시지 1개
- [ ] 금지 표현 없음, 브랜드 핸들/슬로건 정확(@caracal_supply, WE SUPPORT ALL THE PLAYERS)
- [ ] 수치·출처 정확, 해시태그 5~8개
- 결과를 `review-<번호>.md`에 1줄 요약(✅/⚠️). ⚠️면 스펙 수정 후 5)부터 재실행.

### 7) topic-bank 갱신 & 발행
- 해당 주제 상태를 `발행대기(검수)`로 바꾸고 날짜·파일경로·캡션 위치 기록, 발행 로그에 추가.
- **발행 방식(현재 설정 = 2단계 승인):**
  - **1차 승인(예약 전 · Claude 세션):** 카드뉴스 PNG(가능하면 이미지 첨부) + 캡션 + 예약 시각을 사용자에게 보여주고 **반드시 `AskUserQuestion`으로 승인을 받는다.** 승인 전에는 절대 Buffer로 보내지 않는다.
    - 도구 차원 안전장치: `publish_cardnews.sh`는 `--approved` 없이 실행하면 **미리보기만 출력하고 외부 동작(이미지 push·Buffer 전송) 없이 exit 10**으로 멈춘다. 사용자가 승인하면 같은 명령에 `--approved`를 붙여 다시 실행한다.
  - **2차 승인(게시 시각 · 휴대폰):** Buffer가 `notification` 모드로 예약 → 예약 시각에 **휴대폰 Buffer 앱 푸시**가 오고, 앱에서 **'게시'를 눌러야** 인스타에 올라간다.
  - 1차 미리보기 단계를 건너뛰지 않는다. 게시 시각 자동 게시(2차 생략)는 사용자가 명시적으로 요청할 때만 `--auto`.

---

## Buffer 게시 (✅ 연동 검증 완료 — 2026-06-04 실제 예약 게시 성공 / 기본 = 2단계 승인)
> **2단계 승인 흐름:**
> 1. **1차(예약 전·세션):** `--approved` 없이 `publish_cardnews.sh` 실행 → 미리보기(슬라이드 수·예약시각·채널·캡션 전문)만 출력하고 외부 동작 없이 멈춤(exit 10). 사용자 승인 후 `--approved`로 재실행해야 실제 예약이 진행된다.
> 2. **2차(게시 시각·휴대폰):** `notification` 모드라 예약 시각에 휴대폰 **Buffer 앱**으로 푸시가 오고, 앱에서 '게시'를 눌러야 인스타에 업로드된다. (Buffer 모바일 앱 설치 + 알림 허용 + 인스타 채널 연결 필요.)
> 게시 시각 자동 게시(2차 생략)는 `--auto`.
Buffer(2026)는 GraphQL API + 개인 API 키 + **이미지 URL만** 허용. 그래서 PNG를 GitHub(=Vercel 사이트)로
push해 공개 URL을 만든 뒤 Buffer로 캐러셀을 예약한다. 전 과정을 오케스트레이터 한 줄로 실행:
- 연결 상태: 인스타 채널 `caracal_supply`가 `.env`의 BUFFER_CHANNEL_ID에 저장됨.
- 확정 스키마(`buffer_post.py`에 반영 완료): `channels(input:{organizationId})`, `createPost`는 union 반환(`PostActionSuccess`/에러), assets는 `{image:{url}}`, **인스타는 `metadata.instagram.type="post"` + `shouldShareToFeed=true` 필수**, schedulingType `notification`(**기본** — 휴대폰 앱 승인 알림 후 수동 게시)/`automatic`(`--auto`일 때만 자동게시), mode `customScheduled`(--due)/`addToQueue`(기본)/`shareNow`(--now).
```bash
# 1차: 미리보기(승인용) — 외부 동작 없음, 내용 확인만
bash ".claude/skills/caracal-instagram-cardnews/assets/publish_cardnews.sh" \
  --dir "marketing-agent/output/cardnews-<번호>" \
  --caption "marketing-agent/output/caption-<번호>.txt" --due "2026-06-04T19:30:00+09:00"
# 사용자 승인 후: 동일 명령 + --approved (실제 예약 진행)
bash ".claude/skills/caracal-instagram-cardnews/assets/publish_cardnews.sh" \
  --dir "marketing-agent/output/cardnews-<번호>" \
  --caption "marketing-agent/output/caption-<번호>.txt" --due "2026-06-04T19:30:00+09:00" --approved
#   자동 게시(2차 생략)는 끝에 --auto 추가
```
동작: (1차 승인) 미리보기 → 멈춤 → 사용자 승인 → **--approved 재실행** → ①PNG를 main에 commit/push → ②Vercel 배포 200 확인까지 폴링 → ③`buffer_post.py publish`로 인스타 **승인 알림 예약** → (2차 승인) 예약 시각에 휴대폰 Buffer 앱 알림에서 '게시'.

- `.env`에 `BUFFER_API_KEY`가 비어 있으면 스크립트가 **exit 3**으로 멈춤 → 자동 게시 대신 **검수 후 수동 승인**으로 폴백(경로+캡션 보고).
- 키 최초 입력 후 1회 검증·채널 ID 확인:
  ```bash
  python3 ".claude/skills/caracal-instagram-cardnews/assets/buffer_post.py" verify       # 조직·채널·인스타 채널ID
  python3 ".claude/skills/caracal-instagram-cardnews/assets/buffer_post.py" introspect   # createPost 입력 스키마(필요시 enum 조정)
  ```
- 스키마는 이미 확정·반영됨(위 참조). 향후 Buffer가 베타 스키마를 또 바꾸면 `introspect`로 재확인 후 `inp`/mutation 조정.
- 예약 게시물 삭제(재예약 시): `buffer_post.py delete --id <postId>`. 이미지 교체 후 재예약할 땐 Buffer가 생성 시점 이미지를 가져가므로 **기존 예약 삭제 → 새로 publish**(이미지 캐시 우회 위해 `publish_cardnews.sh --bust <토큰>`으로 URL에 `?v=` 부여).
> 공식 계정 게시는 브랜드 리스크가 있으니 **기본 승인 알림 모드를 유지**하는 것을 권장(휴대폰에서 최종 확인 후 게시). `--auto`(자동 게시)는 운영이 안정된 뒤에만 사용.

## 포인트 컬러 (확정)
`#E44E12`(주황) — **공식 CARACAL 워드마크 파일에서 추출한 브랜드 색**. (과거 #C8962A·#E5402F는 폐기)
스펙 JSON의 `accent` 값으로 전체 카드뉴스에 일괄 반영된다.

## 업로드 하루 전 알람
스케줄 작업 `caracal-cardnews-preupload-alarm`(cron `0 17 * * 0,3` = 일·수 17시)이 다음 날 업로드 예정 카드뉴스를
PushNotification으로 알려준다. 검토 후 Buffer 대시보드에서 최종 확인.
