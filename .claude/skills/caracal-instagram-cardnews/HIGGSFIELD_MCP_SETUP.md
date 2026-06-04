# Higgsfield MCP 연동 + 트렌드 릴스 워크플로

카라칼 카드뉴스 스킬에 **AI 영상(Higgsfield)** 을 붙여 요즘(2026) 인스타 트렌드형 릴스를 만든다.
Higgsfield는 이미지→영상(시네마틱 카메라 모션)과 Kling 3 / Veo 3 / Sora 2 등 다중 모델을 제공한다.

---

## 1. Higgsfield MCP 서버 등록

루트의 `.mcp.json.example` 을 `.mcp.json` 으로 복사하고 아래 둘 중 하나를 선택해 채운다.

### 방식 A — 호스티드 MCP (권장 · 폰/웹 세션에 적합)
키 관리 없이 브라우저 OAuth로 Higgsfield 계정을 인증한다.
1. `higgsfield.ai` 로그인 → 대시보드의 **MCP** 항목에서 MCP 서버 URL을 확인.
2. `.mcp.json`:
   ```json
   { "mcpServers": { "higgsfield": { "type": "http", "url": "<대시보드 MCP URL>" } } }
   ```
3. 세션을 다시 시작하면 브라우저 인증 후 `mcp__higgsfield__*` 도구가 활성화된다.

### 방식 B — 자체 호스팅 커뮤니티 MCP
`HIGGSFIELD_API_KEY` / `HIGGSFIELD_SECRET`(.env)이 필요하다.
1. 커뮤니티 서버 클론·설치 (예: `jfikrat/higgsfield-mcp`).
2. `.mcp.json`:
   ```json
   { "mcpServers": { "higgsfield": {
       "command": "python", "args": ["-m", "higgsfield_mcp.server"],
       "cwd": "/abs/path/to/higgsfield-mcp",
       "env": { "HF_API_KEY": "${HIGGSFIELD_API_KEY}", "HF_SECRET": "${HIGGSFIELD_SECRET}" }
   } } }
   ```

> 키 발급: higgsfield.ai 로그인 → 계정/개발자 설정 → API Key / Secret. `.env`는 절대 커밋 금지.
> 영상 생성에는 Higgsfield 크레딧이 소모된다.

---

## 2. 트렌드 릴스 만드는 순서

도구: `.claude/skills/caracal-instagram-cardnews/assets/reels_trend.py` (2단계)

### (1) 브리프 생성 — 카드 스펙 → 트렌드 샷리스트
```bash
python3 ".claude/skills/caracal-instagram-cardnews/assets/reels_trend.py" brief \
  --spec "marketing-agent/output/cardnews-spec-<번호>.json" \
  --out  "marketing-agent/output/reels-brief-<번호>.json" --maxshots 6
```
- 첫 샷 = **3초 훅**, 가운데 = 빠른 컷 본문(2.6초), 마지막 = **CTA**.
- 각 샷에 Higgsfield용 `prompt`(비주얼 + 카메라 모션), `model`, `source_image`(카드 슬라이드), 번인 `caption`이 채워진다.

### (2) Higgsfield MCP로 샷별 클립 생성
브리프의 각 샷에 대해 Higgsfield MCP 도구를 호출한다(이미지→영상).
- 입력: `source_image`(해당 슬라이드 PNG) + `higgsfield.prompt` + `higgsfield.motion`/`model`.
- 출력 클립을 **`shot_<id>.mp4`** 규칙으로 한 폴더에 저장 (예: `.../clips-<번호>/shot_01.mp4` …).
- 트렌드 포인트: 훅 샷은 강한 푸시인, 이후 샷은 모션을 바꿔 컷에 리듬을 준다(브리프 motion 참고).

### (3) 릴스 조립 — 클립 + 브리프 → 최종 mp4
```bash
python3 ".claude/skills/caracal-instagram-cardnews/assets/reels_trend.py" assemble \
  --brief "marketing-agent/output/reels-brief-<번호>.json" \
  --clips "marketing-agent/output/clips-<번호>" \
  --out   "marketing-agent/output/reels-<번호>.mp4" \
  [--music "트렌딩오디오.m4a"]
```
- 클립을 1080×1920로 정규화 → **빠른 하드컷 연결** → **자막 번인**(훅은 상단 크게, 본문/CTA는 하단) → 음악 믹스 → 인스타 호환 H.264/AAC(+faststart).
- `--music` 미지정 시 저작권 안전 BGM 베드로 폴백. 실제 발행 땐 인스타 음원 라이브러리의 트렌딩 오디오로 교체 권장.
- **Higgsfield 클립이 아직 없을 때**: `--clips` 대신 `--slides <카드뉴스 슬라이드 폴더>`를 주면 슬라이드에 줌·팬(Ken Burns) 모션을 입혀 클립을 자동 생성해 **MCP 없이도 완성본 릴스**가 나온다(프리뷰용). 이후 Higgsfield 클립이 준비되면 `--clips`로 그대로 대체.
  ```bash
  python3 ".../reels_trend.py" assemble --brief <brief.json> \
    --slides "marketing-agent/output/cardnews-<번호>" --out "marketing-agent/output/reels-<번호>.mp4"
  ```

### (4) 검수 → 발행
- 릴스를 사용자에게 보여주고(미리보기) 승인받는다.
- 발행은 기존 2단계 승인 흐름 사용: `buffer_post.py publish --video <공개 URL> --type reel ...`
  (1차 세션 승인 → 2차 휴대폰 Buffer 앱 승인). 자세한 건 SKILL.md의 Buffer 절 참고.

---

## 2026 릴스 트렌드 체크리스트 (브리프에 반영됨)
- [ ] 첫 **3초 훅** + 1~2초 내 텍스트 오버레이
- [ ] 샷당 2~3초 **빠른 컷**, 패턴 인터럽트(급줌/리빌)
- [ ] 총 **15~25초** 목표
- [ ] **트렌딩 오디오** 사용(인스타 음원 라이브러리)
- [ ] 브랜드 포인트 컬러(#E44E12) 자막, 마지막 CTA

## 출처
- Higgsfield AI: https://higgsfield.ai/ , MCP 안내: https://higgsfield.ai/mcp
- 커뮤니티 MCP 예: https://github.com/jfikrat/higgsfield-mcp
- 릴스 트렌드 참고: later.com/blog/instagram-reels-trends, opus.pro/research/best-video-hooks-instagram
