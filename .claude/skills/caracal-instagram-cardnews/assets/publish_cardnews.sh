#!/usr/bin/env bash
# 카드뉴스 게시 오케스트레이터 (2단계 승인)
#  [1차 승인] --approved 없이 실행하면 미리보기(슬라이드·캡션·예약시각)만 출력하고
#             외부 동작(이미지 push·Buffer 전송) 없이 멈춘다. 내용 확인 후 --approved 로 재실행.
#  [본 작업]  1) PNG를 GitHub(=Vercel 사이트)로 push → 공개 이미지 URL 생성
#             2) Vercel 배포 완료 대기(URL 200 응답까지 폴링)
#             3) Buffer GraphQL로 인스타 캐러셀 예약(기본=승인 알림 모드)
#  [2차 승인] 예약 시각에 휴대폰 Buffer 앱 푸시 → 앱에서 '게시' 눌러 최종 업로드.
#
# 사용:
#   # 1차: 미리보기
#   bash publish_cardnews.sh --dir marketing-agent/output/cardnews-T2 --caption marketing-agent/output/caption-T2.txt --due "2026-06-04T19:30:00+09:00"
#   # 승인 후: 실제 예약
#   bash publish_cardnews.sh --dir ... --caption ... --due ... --approved
set -euo pipefail

# 프로젝트 루트 = assets에서 4단계 위(assets→caracal-instagram-cardnews→skills→.claude→ROOT).
# macOS·리눅스(폰/웹) 모두에서 동작하도록 하드코딩 대신 스크립트 위치로 계산한다.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
cd "$ROOT"

DIR=""; CAPTION=""; DUE=""; CHANNEL=""; BUST=""; AUTO=""; APPROVED=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dir) DIR="$2"; shift 2;;
    --caption) CAPTION="$2"; shift 2;;
    --due) DUE="$2"; shift 2;;
    --channel) CHANNEL="$2"; shift 2;;
    --bust) BUST="$2"; shift 2;;   # 이미지 갱신 시 캐시 무력화 토큰(?v=...)
    --auto) AUTO="1"; shift;;       # 게시 시각 자동 게시(기본은 휴대폰 앱 승인 알림 = 2차 승인)
    --approved) APPROVED="1"; shift;; # 1차 승인 완료 표시(이게 없으면 미리보기만 하고 멈춤)
    *) echo "알 수 없는 인자: $1"; exit 2;;
  esac
done
[[ -z "$DIR" || -z "$CAPTION" ]] && { echo "사용법: --dir <png폴더> --caption <txt> [--due ISO] [--channel ID]"; exit 2; }
[[ ! -d "$DIR" ]] && { echo "[!] 폴더 없음: $DIR"; exit 1; }

# .env 로드 (PUBLIC_BASE_URL, BUFFER_*)
set -a; [[ -f .env ]] && source .env; set +a
GITHUB_TOKEN="$(grep -E '^GITHUB_TOKEN=' .env.local 2>/dev/null | cut -d= -f2- || true)"
PUBLIC_BASE_URL="${PUBLIC_BASE_URL:-https://kimbiseooososo.vercel.app}"

if [[ -z "${BUFFER_API_KEY:-}" ]]; then
  echo "[중단] BUFFER_API_KEY 미설정 → 자동 게시 불가. .env에 키 입력 후 다시 실행하세요."
  echo "       (그 전까지는 검수 후 수동 업로드로 운영됩니다.)"
  exit 3
fi

# ── 1차 승인 게이트 ───────────────────────────────────────────────
# --approved 가 없으면 어떤 외부 동작도 하지 않고 미리보기만 출력하고 멈춘다.
SLIDES=$(ls "$DIR"/slide_*.png 2>/dev/null | sort)
NSLIDES=$(printf '%s\n' "$SLIDES" | grep -c . || true)
SCHED_LABEL=$([[ -n "$AUTO" ]] && echo "게시 시각 자동 게시(2차 승인 없음)" || echo "휴대폰 Buffer 앱 승인 알림(2차 승인)")
WHEN_LABEL=${DUE:-"Buffer 큐에 추가(시각 미지정)"}
echo "════════ 게시 미리보기 (1차 승인용) ════════"
echo "  폴더      : $DIR"
echo "  슬라이드  : ${NSLIDES}장"
echo "  예약 시각 : $WHEN_LABEL"
echo "  채널      : ${CHANNEL:-${BUFFER_CHANNEL_ID:-'(.env BUFFER_CHANNEL_ID)'}}"
echo "  게시 방식 : $SCHED_LABEL"
echo "  ── 캡션 ──"
sed 's/^/  | /' "$CAPTION"
echo "════════════════════════════════════════════"
if [[ -z "$APPROVED" ]]; then
  echo
  echo "[1차 승인 대기] 위 내용을 확인하세요. 외부로 나간 것은 아직 없습니다(이미지 push·Buffer 전송 안 함)."
  echo "               승인하면 동일 명령에 --approved 를 붙여 다시 실행하면 예약이 진행됩니다."
  exit 10
fi
echo "[1차 승인 확인됨 --approved] 예약을 진행합니다."

echo "▶ 1/3 이미지 GitHub push (공개 URL 생성)"
git add "$DIR"
git commit -m "cardnews: publish $(basename "$DIR")" >/dev/null 2>&1 || echo "  (변경 없음/이미 커밋됨)"
if [[ -n "$GITHUB_TOKEN" ]]; then
  git push "https://${GITHUB_TOKEN}@github.com/zsho8/kimbiseooososo.git" HEAD:main >/dev/null 2>&1 \
    && echo "  push 완료" || { echo "  [!] push 실패 — 토큰/권한 확인"; exit 1; }
else
  git push origin HEAD:main >/dev/null 2>&1 || { echo "  [!] push 실패(토큰 없음)"; exit 1; }
fi

# 이미지 URL 목록 (slide_01.png 순서대로)
URLS=""
for f in $(ls "$DIR"/slide_*.png | sort); do
  rel="${f#$ROOT/}"
  url="${PUBLIC_BASE_URL}/${rel}"
  [[ -n "$BUST" ]] && url="${url}?v=${BUST}"
  URLS="${URLS:+$URLS,}${url}"
done
FIRST="${URLS%%,*}"
LAST="${URLS##*,}"   # 마지막 슬라이드도 확인(전체 배포 완료 보장)
echo "  대표 URL: $FIRST"

echo "▶ 2/3 Vercel 배포 대기 (최대 150초) — 첫·마지막 슬라이드 모두 200 확인"
for i in $(seq 1 30); do
  c1="$(curl -s -o /dev/null -w '%{http_code}' "$FIRST" || true)"
  c2="$(curl -s -o /dev/null -w '%{http_code}' "$LAST" || true)"
  [[ "$c1" == "200" && "$c2" == "200" ]] && { echo "  배포 확인(첫=$c1, 끝=$c2)"; sleep 3; break; }
  sleep 5
  [[ $i -eq 30 ]] && echo "  [경고] 아직 200 아님(첫=$c1, 끝=$c2) — 그래도 게시 시도"
done

if [[ -n "$AUTO" ]]; then
  echo "▶ 3/3 Buffer 인스타 예약 게시 (자동 게시 — 승인 불필요)"
else
  echo "▶ 3/3 Buffer 인스타 예약 게시 (승인 알림 모드 — 휴대폰 Buffer 앱에서 '게시' 눌러야 업로드)"
fi
ARGS=(publish --caption-file "$CAPTION" --images "$URLS")
[[ -n "$DUE" ]] && ARGS+=(--due "$DUE")
[[ -n "$CHANNEL" ]] && ARGS+=(--channel "$CHANNEL")
[[ -n "$AUTO" ]] && ARGS+=(--auto)
python3 ".claude/skills/caracal-instagram-cardnews/assets/buffer_post.py" "${ARGS[@]}"
if [[ -z "$AUTO" ]]; then
  echo "완료 — 예약 등록됨. 예약 시각에 휴대폰 Buffer 앱 알림에서 '게시'를 눌러 승인하세요."
else
  echo "완료."
fi
