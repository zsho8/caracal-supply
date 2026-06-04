#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CARACAL 트렌드 릴스 파이프라인 (Higgsfield MCP 연동용) — v1

요즘(2026) 인스타 릴스 트렌드에 맞춘 9:16 릴스를 만든다.
  · 첫 3초 강한 훅 + 1~2초 내 텍스트 오버레이
  · 빠른 컷(하드컷) 편집, 샷마다 카메라 모션
  · 번인 자막(한글, 번들 NanumGothicBold), 브랜드 포인트 컬러
  · 트렌딩 오디오 슬롯(직접 교체) — 없으면 저작권 안전 BGM 베드 폴백

두 단계로 동작한다.
  1) brief    : 카드뉴스 spec.json → 트렌드 샷리스트(brief.json).
                각 샷에 Higgsfield 이미지→영상 프롬프트(카메라 모션/모델)와 자막을 채운다.
                → 이 brief를 보고 Higgsfield MCP 도구로 샷별 클립(mp4)을 생성한다.
  2) assemble : 생성된 클립 폴더 + brief.json → 최종 트렌드 릴스(mp4).
                클립을 1080x1920로 정규화 → 빠른 컷 연결 → 자막 번인 → 음악 믹스 → 인스타 호환 mp4.

사용:
  python3 reels_trend.py brief --spec spec.json --out brief.json [--maxshots 6]
  python3 reels_trend.py assemble --brief brief.json --clips <클립폴더> --out reel.mp4 [--music track.m4a]

클립 파일 규칙: <클립폴더>/shot_<id>.mp4  (예: shot_01.mp4, shot_02.mp4 ...). brief의 샷 순서대로 사용.
"""
import os, sys, json, glob, argparse, subprocess, re
import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

FF = imageio_ffmpeg.get_ffmpeg_exe()
W, H = 1080, 1920
ACCENT = (228, 78, 18)        # #E44E12 카라칼 포인트
ASSET_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_BOLD = os.path.join(ASSET_DIR, "fonts", "NanumGothicBold.ttf")
FONT_REG  = os.path.join(ASSET_DIR, "fonts", "NanumGothic.ttf")

# ── 트렌드 카메라 모션 프리셋(Higgsfield 프롬프트 힌트) ───────────────
# 첫 샷은 강한 푸시인(훅), 이후 샷은 변화를 주어 빠른 컷에 리듬을 준다.
MOTION_CYCLE = [
    ("punch-in",     "camera slowly pushes in, subtle handheld energy, cinematic"),
    ("whip-pan",     "fast whip pan reveal into the subject, dynamic, energetic"),
    ("orbit",        "smooth orbit around the subject, shallow depth of field"),
    ("crane-up",     "crane up reveal, epic, motivational"),
    ("dolly-zoom",   "subtle dolly zoom, dramatic tension"),
    ("speed-ramp",   "speed ramp from slow to fast, kinetic"),
]
HOOK_MOTION = ("punch-in-hard", "fast punch-in on the subject, attention grabbing first frame, cinematic, high energy")
DEFAULT_MODEL = "kling-3.0"   # Higgsfield에서 모션 표현력 좋은 기본 모델(원하면 veo-3 / sora-2 등으로 교체)


def clean(t):
    return re.sub(r"\s+", " ", (t or "").replace("*", "").replace("\n", " ")).strip()


# ======================= 1) BRIEF =======================
def shot_caption(s, role):
    """샷 역할에 맞는 짧은 번인 자막 텍스트."""
    if role == "hook":
        # 훅: kicker > headline 순으로 가장 강한 한 줄
        return clean(s.get("kicker") or s.get("headline") or s.get("subtitle") or "")
    if role == "cta":
        base = clean(s.get("subtitle") or s.get("headline") or "")
        return base or "프로필 링크에서 확인 →"
    # 본문: headline 우선, 너무 길면 컷
    txt = clean(s.get("headline") or s.get("subtitle") or "")
    return txt


def hf_prompt(s, motion_desc):
    """Higgsfield 이미지→영상 프롬프트(샷 비주얼 + 카메라 모션)."""
    visual = clean(s.get("photo_hint") or s.get("headline") or s.get("subtitle") or "running, sports, dynamic")
    return f"{visual}. {motion_desc}. vertical 9:16, brand mood: energetic sports, clean."


def cmd_brief(a):
    spec = json.load(open(a.spec, encoding="utf-8"))
    slides = spec.get("slides", [])
    if not slides:
        print("[!] spec에 slides가 없습니다.", file=sys.stderr); sys.exit(2)
    n = min(len(slides), a.maxshots)
    # 훅(첫) + 본문 + CTA(마지막) 구조로 샷 역할 배정
    shots = []
    for i in range(n):
        s = slides[i]
        if i == 0:
            role = "hook"; mname, mdesc = HOOK_MOTION
            dur = 3.0
        elif i == n - 1:
            role = "cta"; mname, mdesc = MOTION_CYCLE[i % len(MOTION_CYCLE)]
            dur = 3.0
        else:
            role = "point"; mname, mdesc = MOTION_CYCLE[(i - 1) % len(MOTION_CYCLE)]
            dur = 2.6
        src = f"slide_{i+1:02d}.png"   # Higgsfield 입력 이미지(카드뉴스 슬라이드) 참고
        shots.append({
            "id": f"{i+1:02d}",
            "role": role,
            "dur": dur,
            "source_image": src,
            "higgsfield": {"model": a.model, "motion": mname, "prompt": hf_prompt(s, mdesc)},
            "caption": {"text": shot_caption(s, role), "style": role},
        })
    brief = {
        "topic": spec.get("topic") or spec.get("title") or "",
        "aspect": "9:16", "fps": 30,
        "music_hint": "업비트/모멘텀 계열 트렌딩 오디오로 교체(인스타 음원 라이브러리). 미지정 시 안전 BGM 폴백.",
        "trend_notes": "첫 3초 훅 고정, 샷당 2~3초 빠른 컷, 자막은 1~2초 내 노출. 총 15~25초 목표.",
        "shots": shots,
    }
    json.dump(brief, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"[OK] 트렌드 브리프 생성 — {a.out}  (샷 {len(shots)}개, 모델 {a.model})")
    print("  다음 단계: Higgsfield MCP로 각 샷의 prompt/source_image로 클립을 만들어")
    print(f"            shot_<id>.mp4 로 저장 후 → assemble 실행.")
    for sh in shots:
        print(f"   - shot_{sh['id']} [{sh['role']}/{sh['higgsfield']['motion']}] \"{sh['caption']['text'][:24]}\"")


# ======================= 2) ASSEMBLE =======================
def _font(path, size):
    return ImageFont.truetype(path if os.path.exists(path) else FONT_REG, size)

def _wrap(draw, text, font, maxw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textbbox((0, 0), t, font=font)[2] <= maxw:
            cur = t
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)
    return lines or [text]

def render_caption_png(text, style, out_path):
    """투명 배경 1080x1920 자막 오버레이 PNG 생성(번인용)."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if not text:
        img.save(out_path); return
    hook = (style == "hook")
    size = 92 if hook else 72
    font = _font(FONT_BOLD, size)
    maxw = W - 160
    lines = _wrap(d, text, font, maxw)
    lh = int(size * 1.28)
    block_h = lh * len(lines)
    # 훅은 화면 상단 1/3, 본문/CTA는 하단
    y0 = int(H * 0.16) if hook else H - block_h - int(H * 0.16)
    pad = 34
    # 반투명 배경 바(가독성)
    bar_top = y0 - pad; bar_bot = y0 + block_h + pad
    d.rectangle([0, bar_top, W, bar_bot], fill=(12, 12, 14, 150))
    if hook:  # 훅엔 포인트 컬러 강조 바
        d.rectangle([0, bar_top, 18, bar_bot], fill=ACCENT + (255,))
    y = y0
    for ln in lines:
        tw = d.textbbox((0, 0), ln, font=font)[2]
        x = (W - tw) // 2
        # 외곽선(그림자)으로 어떤 배경에도 또렷하게
        for dx, dy in ((-3,0),(3,0),(0,-3),(0,3)):
            d.text((x+dx, y+dy), ln, font=font, fill=(0, 0, 0, 220))
        d.text((x, y), ln, font=font, fill=(255, 255, 255, 255))
        y += lh
    img.save(out_path)

def run(cmd, desc=""):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"[ffmpeg 실패] {desc}\n" + r.stderr[-1800:], file=sys.stderr); sys.exit(1)
    return r

def kenburns_clip(img, dur, fps, motion, out):
    """Higgsfield 클립이 없을 때, 슬라이드 PNG에 줌·팬 모션을 입혀 클립 생성(폴백 프리뷰).
    실제 발행용은 Higgsfield 영상으로 대체 권장."""
    frames = max(1, int(round(dur * fps)))
    # 모션별로 줌 방향/패닝을 달리해 빠른 컷에 리듬을 준다.
    if motion in ("whip-pan",):
        z = "1.12"; x = "(iw-iw/zoom)*on/{f}".format(f=frames); y = "ih/2-(ih/zoom/2)"
    elif motion in ("crane-up",):
        z = "min(zoom+0.0012,1.18)"; x = "iw/2-(iw/zoom/2)"; y = "(ih-ih/zoom)*(1-on/{f})".format(f=frames)
    elif motion in ("orbit", "dolly-zoom"):
        z = "if(lte(on,1),1.18,max(zoom-0.0010,1.0))"; x = "iw/2-(iw/zoom/2)"; y = "ih/2-(ih/zoom/2)"
    else:  # punch-in / punch-in-hard / speed-ramp 기본: 줌 인
        step = 0.0016 if motion == "punch-in-hard" else 0.0011
        z = f"min(zoom+{step},1.2)"; x = "iw/2-(iw/zoom/2)"; y = "ih/2-(ih/zoom/2)"
    # 출력(1080x1920)보다 약간 큰 1.25x로만 프리스케일 → 줌·팬 여유 확보하면서 가볍고 빠르게.
    PS_W, PS_H = 1350, 2400
    vf = (f"scale={PS_W}:{PS_H}:force_original_aspect_ratio=increase,crop={PS_W}:{PS_H},"
          f"zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s={W}x{H}:fps={fps},format=yuv420p")
    run([FF, "-y", "-loop", "1", "-t", f"{dur:.3f}", "-i", img, "-an",
         "-vf", vf, "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", out], f"kenburns {os.path.basename(img)}")
    return out

def cmd_assemble(a):
    brief = json.load(open(a.brief, encoding="utf-8"))
    shots = brief["shots"]
    fps = int(brief.get("fps", 30))
    tmp = "/tmp/caracal_trend_reels"; os.makedirs(tmp, exist_ok=True)

    # 1) 각 샷 클립을 1080x1920·동일 코덱·정확한 길이로 정규화
    norm = []
    for sh in shots:
        clip = os.path.join(a.clips, f"shot_{sh['id']}.mp4") if a.clips else None
        if clip and not os.path.exists(clip):
            cand = glob.glob(os.path.join(a.clips, f"*{sh['id']}*.mp4"))
            clip = cand[0] if cand else None
        # Higgsfield 클립이 없으면 --slides 폴백(슬라이드 줌·팬)
        if not clip and a.slides:
            src = os.path.join(a.slides, sh.get("source_image", f"slide_{sh['id']}.png"))
            if os.path.exists(src):
                clip = kenburns_clip(src, sh["dur"], fps, sh["higgsfield"]["motion"], f"{tmp}/kb_{sh['id']}.mp4")
        if not clip:
            print(f"[!] 클립 없음: shot_{sh['id']}.mp4 — Higgsfield로 생성하거나 --slides <폴더>로 폴백하세요.", file=sys.stderr); sys.exit(3)
        outc = f"{tmp}/n_{sh['id']}.mp4"
        vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
              f"setsar=1,fps={fps},format=yuv420p")
        run([FF, "-y", "-i", clip, "-t", f"{sh['dur']:.3f}", "-an",
             "-vf", vf, "-c:v", "libx264", "-preset", "medium", "-crf", "20", outc], f"norm {sh['id']}")
        norm.append(outc)

    # 2) 빠른 하드컷 연결(concat demuxer)
    listf = f"{tmp}/list.txt"
    with open(listf, "w") as f:
        for p in norm: f.write(f"file '{p}'\n")
    joined = f"{tmp}/joined.mp4"
    run([FF, "-y", "-f", "concat", "-safe", "0", "-i", listf, "-c", "copy", joined], "concat")

    # 3) 자막 번인(샷별 PNG 오버레이 + 노출 구간 enable)
    inputs = [FF, "-y", "-i", joined]
    overlays = []; prev = "0:v"; t0 = 0.0; cap_idx = 1
    has_cap = False
    for sh in shots:
        cap = (sh.get("caption") or {}).get("text", "")
        t1 = t0 + sh["dur"]
        if cap:
            png = f"{tmp}/cap_{sh['id']}.png"
            render_caption_png(cap, (sh.get("caption") or {}).get("style", "point"), png)
            inputs += ["-i", png]
            lbl = f"c{cap_idx}"
            # 훅 자막은 0.2s, 본문은 0.3s 뒤부터 노출(트렌드: 1~2초 내 텍스트)
            s_on = t0 + (0.2 if sh.get("role") == "hook" else 0.3)
            overlays.append(f"[{prev}][{cap_idx}:v]overlay=0:0:enable='between(t,{s_on:.2f},{t1:.2f})'[{lbl}]")
            prev = lbl; cap_idx += 1; has_cap = True
        t0 = t1
    total = t0
    captioned = f"{tmp}/captioned.mp4"
    if has_cap:
        inputs += ["-filter_complex", ";".join(overlays), "-map", f"[{prev}]",
                   "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-r", str(fps), captioned]
        run(inputs, "captions")
    else:
        captioned = joined

    # 4) 오디오: --music 있으면 사용(트렌딩 오디오), 없으면 안전 BGM 베드 폴백
    audio = f"{tmp}/audio.m4a"
    if a.music and os.path.exists(a.music):
        run([FF, "-y", "-i", a.music, "-t", f"{total:.3f}",
             "-af", f"afade=t=in:d=0.6,afade=t=out:st={max(0,total-1.2):.2f}:d=1.2,volume=0.9",
             "-c:a", "aac", "-b:a", "192k", audio], "music")
    else:
        chord = [146.83, 220.0, 277.18, 329.63]
        bcmd = [FF, "-y"]
        for f0 in chord: bcmd += ["-f", "lavfi", "-t", f"{total:.3f}", "-i", f"sine=frequency={f0}"]
        mix = "".join(f"[{i}]" for i in range(len(chord)))
        bcmd += ["-filter_complex",
                 f"{mix}amix=inputs={len(chord)}:normalize=0,tremolo=f=2.1:d=0.5,lowpass=f=2600,"
                 f"volume=0.18,afade=t=in:d=0.8,afade=t=out:st={max(0,total-1.4):.2f}:d=1.4[a]",
                 "-map", "[a]", "-c:a", "aac", "-b:a", "128k", audio]
        run(bcmd, "bgm")

    # 5) mux → 인스타 호환(H.264/AAC/+faststart)
    run([FF, "-y", "-i", captioned, "-i", audio, "-c:v", "copy", "-c:a", "aac",
         "-shortest", "-movflags", "+faststart", a.out], "mux")
    kb = os.path.getsize(a.out) // 1024
    mus = "트렌딩 오디오" if (a.music and os.path.exists(a.music)) else "안전 BGM 폴백"
    print(f"[OK] 트렌드 릴스: {a.out}  ({kb}KB, 약 {total:.1f}초, 샷 {len(shots)}개, 음악={mus})")


def main():
    ap = argparse.ArgumentParser(description="CARACAL 트렌드 릴스 (Higgsfield MCP 연동)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("brief"); b.set_defaults(fn=cmd_brief)
    b.add_argument("--spec", required=True); b.add_argument("--out", required=True)
    b.add_argument("--maxshots", type=int, default=6)
    b.add_argument("--model", default=DEFAULT_MODEL, help="Higgsfield 모델(kling-3.0/veo-3/sora-2 등)")
    s = sub.add_parser("assemble"); s.set_defaults(fn=cmd_assemble)
    s.add_argument("--brief", required=True)
    s.add_argument("--clips", default="", help="Higgsfield 클립 폴더(shot_<id>.mp4)")
    s.add_argument("--slides", default="", help="클립 없을 때 폴백: 슬라이드 PNG 폴더(줌·팬 모션 생성)")
    s.add_argument("--out", required=True); s.add_argument("--music", default="")
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
