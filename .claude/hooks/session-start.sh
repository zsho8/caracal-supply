#!/bin/bash
# 카라칼 카드뉴스 스킬을 Claude Code on the web(원격/모바일 세션)에서도
# 그대로 쓸 수 있도록 의존성을 준비한다.
#
# 한글 폰트(나눔고딕)는 저장소에 번들로 포함돼 있어 별도 설치가 필요 없다.
# (cardnews_gen.py가 리눅스에서 .../assets/fonts 의 폰트로 자동 폴백한다.)
set -euo pipefail

# 로컬(예: macOS) 세션에서는 기존 환경을 그대로 사용하므로 아무것도 하지 않는다.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

echo "[caracal] 카드뉴스 스킬 의존성 설치 중..."

# Python 패키지 — 카드뉴스 PNG(Pillow) / 릴스(imageio-ffmpeg, ffmpeg 내장) 생성용
pip3 install --quiet --no-input Pillow imageio-ffmpeg

echo "[caracal] 준비 완료 — 카드뉴스 스킬을 폰에서도 실행할 수 있습니다."
