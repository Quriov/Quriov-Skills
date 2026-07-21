#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
B站 UP 主视频调研（bili-cli 薄封装）。游客态、零账号。
按名字选对本尊 + 拿视频列表 + 可选详情（简介/字幕/AI总结）。

前置：pipx install bilibili-cli
用法：
  python fetch_bili_creator.py --search "博主名"
  python fetch_bili_creator.py --uid 275565632 -n 30
  python fetch_bili_creator.py --search "博主名" --details 5
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).resolve().parent


def bili(*args):
    """调 bili-cli --json；PYTHONIOENCODING=utf-8 避 Windows GBK emoji 崩。"""
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    try:
        r = subprocess.run(["bili", *args, "--json"], capture_output=True,
                           text=True, encoding="utf-8", errors="replace", env=env, timeout=120)
    except FileNotFoundError:
        sys.exit("[!] 没找到 bili 命令。先装：pipx install bilibili-cli")
    try:
        return json.loads(r.stdout)
    except Exception:
        return {"ok": False, "_raw": (r.stdout or "")[-500:], "_err": (r.stderr or "")[-500:]}


def main():
    ap = argparse.ArgumentParser(description="B站 UP 主视频调研")
    ap.add_argument("--search", help="按名字搜 UP 主（自动选名字匹配+粉丝最多）")
    ap.add_argument("--uid", help="直接指定 UID")
    ap.add_argument("-n", "--max", type=int, default=20, help="视频数量（默认 20）")
    ap.add_argument("--details", type=int, default=0, help="对前 N 个视频拿简介/字幕/AI总结（默认 0）")
    args = ap.parse_args()
    if not (args.search or args.uid):
        ap.error("给 --search 或 --uid")

    if args.uid:
        uid = args.uid
    else:
        res = bili("search", args.search, "--type", "user", "-n", "10")
        users = res.get("data", []) if res.get("ok") else []
        if not users:
            sys.exit(f"[!] 搜不到 UP 主：{args.search!r}")
        print(f"[搜索] {args.search!r} 命中 {len(users)} 个：")
        for u in users:
            print(f"    - {str(u.get('name'))[:24]:<24} 粉{u.get('fans')} 视频{u.get('videos')} id={u.get('id')}")
        q = args.search.lower()

        def score(u):
            name = str(u.get("name", "")).lower()
            match = 2 if name.startswith(q) else (1 if q in name else 0)
            return (match, u.get("fans", 0) or 0)

        best = max(users, key=score)
        uid = best.get("id")
        print(f"[选中] {best.get('name')}（名字匹配 + 粉丝最多；换人用 --uid）")

    res = bili("user-videos", str(uid), "-n", str(args.max))
    vids = res.get("data", []) if res.get("ok") else []
    if not vids:
        sys.exit(f"[!] 没拿到视频（{json.dumps(res, ensure_ascii=False)[:300]}）")
    rows = []
    for v in vids:
        st = v.get("stats", {}) or {}
        rows.append({
            "title": v.get("title"), "bvid": v.get("bvid"), "url": v.get("url"),
            "view": st.get("view"), "like": st.get("like"),
        })
    print(f"[✓] 拿到 {len(rows)} 个视频")

    if args.details > 0:
        for r in rows[:args.details]:
            d = bili("video", r["bvid"])
            data = d.get("data", {}) if d.get("ok") else {}
            vd = data.get("video", {}) or {}
            sub = data.get("subtitle", {}) or {}
            r["description"] = vd.get("description", "")
            r["subtitle"] = sub.get("text", "") if sub.get("available") else ""
            r["ai_summary"] = data.get("ai_summary", "")
            print(f"  · {str(r['title'])[:26]}: 简介{len(r['description'])}字 "
                  f"字幕{len(r['subtitle'])}字 AI总结{len(r['ai_summary'])}字")

    out = HERE / "bili_videos.json"
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[✓] 存 {out.name}（{len(rows)} 个）")
    for i, r in enumerate(rows[:15], 1):
        print(f"  {i:>2}. {str(r['title'])[:40]:<40} | 播放{r['view']}")


if __name__ == "__main__":
    main()
