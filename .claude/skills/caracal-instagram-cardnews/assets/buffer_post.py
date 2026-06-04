#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Buffer GraphQL API 연동 — 카라칼 카드뉴스 인스타 자동 게시.
Buffer(2026)는 베타 GraphQL API + 개인 API 키 + '이미지 URL만' 허용.

사용 예:
  # 1) 연결 검증 (키 입력 후 최초 1회) — 조직/채널 목록과 인스타 채널 ID 확인
  python3 buffer_post.py verify

  # 2) CreatePostInput 실제 스키마 덤프 (필드/enum 확정용)
  python3 buffer_post.py introspect

  # 3) 게시 (캐러셀 이미지 URL 여러 개 + 캡션)
  #    기본: 승인 알림 모드 — 예약 시각에 휴대폰 Buffer 앱으로 푸시가 오고, 앱에서 '게시'를 눌러야 인스타에 올라감.
  python3 buffer_post.py publish \
     --channel <CHANNEL_ID> \
     --caption-file caption.txt \
     --images "https://.../slide_01.png,https://.../slide_02.png" \
     --due "2026-06-04T19:30:00+09:00"   # 생략 시 Buffer 큐에 추가
  #  → 승인 없이 자동 게시하려면 --auto 추가

환경변수(.env / .env.local 자동 로드): BUFFER_API_KEY, BUFFER_CHANNEL_ID, BUFFER_GRAPHQL_URL
"""
import os, sys, json, argparse, urllib.request, urllib.error

# 파일 위치: <ROOT>/.claude/skills/caracal-instagram-cardnews/assets/buffer_post.py → 5단계 위가 프로젝트 루트
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
# ROOT = 프로젝트 루트(클로드 워크샵)

def load_env():
    for fn in (".env", ".env.local"):
        p = os.path.join(ROOT, fn)
        if not os.path.exists(p):
            continue
        with open(p, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

load_env()
ENDPOINT = os.environ.get("BUFFER_GRAPHQL_URL", "https://api.buffer.com/graphql")
KEY = os.environ.get("BUFFER_API_KEY", "").strip()

def need_key():
    if not KEY:
        print("[!] BUFFER_API_KEY 미설정. .env에 Buffer 개인 API 키를 넣으세요.", file=sys.stderr)
        print("    발급: https://publish.buffer.com/settings/api", file=sys.stderr)
        sys.exit(2)

def gql(query, variables=None):
    need_key()
    body = json.dumps({"query": query, "variables": variables or {}}).encode("utf-8")
    req = urllib.request.Request(ENDPOINT, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {KEY}")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"[HTTP {e.code}] {e.read().decode('utf-8', 'ignore')}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"[연결 실패] {e}  (BUFFER_GRAPHQL_URL 확인: {ENDPOINT})", file=sys.stderr)
        sys.exit(1)
    if data.get("errors"):
        print("[GraphQL 오류]", json.dumps(data["errors"], ensure_ascii=False, indent=2), file=sys.stderr)
    return data.get("data") or {}

def cmd_verify(_):
    d = gql("query { account { id email organizations { id name } } }")
    acc = d.get("account") or {}
    orgs = acc.get("organizations") or []
    print("계정:", acc.get("email"))
    if not orgs:
        print("[!] 조직 없음 — Buffer 계정/연결 확인 필요"); return
    for org in orgs:
        oid = org["id"]
        print(f"\n■ 조직: {org.get('name')} (id={oid})")
        ch = gql("query($in:ChannelsInput!){ channels(input:$in){ id service type name displayName isDisconnected } }",
                 {"in": {"organizationId": oid}})
        for c in (ch.get("channels") or []):
            flag = " (연결끊김)" if c.get("isDisconnected") else ""
            mark = "  ★인스타" if (c.get("service") or "").lower() == "instagram" else ""
            print(f"   - {c.get('service')}/{c.get('type')}  {c.get('displayName') or c.get('name')}  id={c['id']}{mark}{flag}")
    print("\n→ 위 인스타 채널 id를 .env의 BUFFER_CHANNEL_ID에 넣으세요.")

def cmd_introspect(_):
    for t in ("CreatePostInput", "AssetInput"):
        d = gql("query($n:String!){ __type(name:$n){ name inputFields{ name type{ name kind ofType{ name kind } } } } }",
                {"n": t})
        print(json.dumps(d, ensure_ascii=False, indent=2))

def cmd_delete(a):
    if not a.id:
        print("[!] 삭제할 post id 필요 (--id)", file=sys.stderr); sys.exit(2)
    mutation = """
    mutation($input: DeletePostInput!) {
      deletePost(input: $input) {
        __typename
        ... on DeletePostSuccess { id }
        ... on VoidMutationError { message }
      }
    }"""
    d = gql(mutation, {"input": {"id": a.id}})
    print(json.dumps(d, ensure_ascii=False, indent=2))
    res = d.get("deletePost") or {}
    if "Error" not in (res.get("__typename") or ""):
        print(f"\n[OK] 게시물 삭제 완료 (id={a.id})")
    else:
        print(f"\n[실패] {res.get('__typename')}: {res.get('message','')}", file=sys.stderr); sys.exit(1)

def cmd_publish(a):
    channel = a.channel or os.environ.get("BUFFER_CHANNEL_ID", "").strip()
    if not channel:
        print("[!] 채널 ID 필요 (--channel 또는 .env BUFFER_CHANNEL_ID)", file=sys.stderr); sys.exit(2)
    if a.caption_file:
        with open(a.caption_file, encoding="utf-8") as f:
            text = f.read().strip()
    else:
        text = a.caption or ""
    # 영상(릴스) 게시: --video <url> [--thumb <url>]
    if getattr(a, "video", None):
        asset = {"video": {"url": a.video.strip()}}
        if getattr(a, "thumb", None):
            asset["video"]["thumbnailUrl"] = a.thumb.strip()
        assets = [asset]
        ig_type = a.type or "reel"
    else:
        urls = [u.strip() for u in (a.images or "").split(",") if u.strip()]
        if not urls:
            print("[!] 이미지/영상 URL 없음 (--images 또는 --video)", file=sys.stderr); sys.exit(2)
        # AssetInput = { image: { url } }  (Buffer 실제 스키마)
        assets = [{"image": {"url": u}} for u in urls]
        ig_type = a.type or "post"
    # schedulingType: automatic=Buffer가 직접 자동게시 / notification=모바일앱 알림 후 수동게시
    # mode: customScheduled(dueAt 예약) / addToQueue(채널 큐에 추가) / shareNow(즉시)
    # 기본값 notification: 예약 시각에 휴대폰 Buffer 앱으로 '승인' 푸시 알림이 오고,
    #   사용자가 직접 '게시'를 눌러야 인스타에 올라간다(승인 후 게시).
    #   --auto 를 명시할 때만 승인 없이 Buffer가 자동 게시한다.
    sched = "automatic" if a.auto else "notification"
    if a.now:
        mode = "shareNow"
    elif a.due:
        mode = "customScheduled"
    else:
        mode = "addToQueue"
    inp = {
        "channelId": channel,
        "text": text,
        "assets": assets,
        "schedulingType": sched,
        "mode": mode,
        # 인스타 게시물 타입 필수: post(피드/캐러셀) 또는 reel(릴스).
        "metadata": {"instagram": {"type": ig_type, "shouldShareToFeed": True}},
    }
    if a.due and not a.now:
        inp["dueAt"] = a.due
    mutation = """
    mutation($input: CreatePostInput!) {
      createPost(input: $input) {
        __typename
        ... on PostActionSuccess { post { id status dueAt channelId schedulingType } }
        ... on InvalidInputError { message }
        ... on LimitReachedError { message }
        ... on NotFoundError { message }
        ... on UnauthorizedError { message }
        ... on UnexpectedError { message }
        ... on RestProxyError { message code }
      }
    }"""
    d = gql(mutation, {"input": inp})
    res = d.get("createPost") or {}
    print(json.dumps(d, ensure_ascii=False, indent=2))
    tn = res.get("__typename")
    if tn == "PostActionSuccess":
        post = res.get("post") or {}
        when = post.get("dueAt") or ("즉시" if mode == "shareNow" else "큐 추가됨")
        if sched == "automatic":
            kind = "Buffer 자동게시(승인 불필요)"
        else:
            kind = "휴대폰 Buffer 앱 승인 알림 → 탭해서 게시"
        print(f"\n[OK] 게시 등록 완료 — id={post.get('id')} / 예정={when} / 방식={kind}")
        if sched != "automatic":
            print("    ※ 예약 시각에 휴대폰 Buffer 앱으로 승인 알림이 갑니다. 앱에서 '게시'를 눌러야 인스타에 올라갑니다.")
    else:
        print(f"\n[실패] {tn}: {res.get('message','(메시지 없음)')}", file=sys.stderr)
        sys.exit(1)

def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("verify").set_defaults(fn=cmd_verify)
    sub.add_parser("introspect").set_defaults(fn=cmd_introspect)
    pd = sub.add_parser("delete"); pd.set_defaults(fn=cmd_delete); pd.add_argument("--id", required=True)
    p = sub.add_parser("publish"); p.set_defaults(fn=cmd_publish)
    p.add_argument("--channel"); p.add_argument("--caption-file"); p.add_argument("--caption")
    p.add_argument("--images", help="쉼표로 구분된 공개 이미지 URL들")
    p.add_argument("--video", help="릴스/영상 공개 URL (mp4)")
    p.add_argument("--thumb", help="영상 커버 썸네일 URL(선택)")
    p.add_argument("--type", help="인스타 타입: post / reel (기본: 영상이면 reel, 아니면 post)")
    p.add_argument("--due", help="ISO8601 예약 시각(+09:00). 생략 시 큐 추가")
    p.add_argument("--now", action="store_true", help="즉시 게시(shareNow). 단, 기본 승인 알림 모드 유지")
    p.add_argument("--auto", action="store_true",
                   help="승인 없이 Buffer가 자동 게시(automatic 모드). 미지정 시 기본은 휴대폰 앱 승인 알림")
    # 하위호환: 예전 스크립트의 --notify 는 이제 기본 동작이므로 받기만 하고 무시
    p.add_argument("--notify", action="store_true", help="(기본값) 휴대폰 앱 승인 알림 모드 — 하위호환용")
    args = ap.parse_args()
    args.fn(args)

if __name__ == "__main__":
    main()
