#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小红书博主笔记调研（编排器）。站在 cv-cat/Spider_XHS（XhsSkills 封装）之上，
只做「定位博主 → 拿笔记列表 → 拿正文」的编排 + 踩坑规避，不重造签名。

前置（详见 SKILL.md）：
  1. 装 cv-cat/XhsSkills + venv 依赖，并跑 patch_spider_xhs.py 修 split bug
  2. 环境变量 XHS_SKILLS_SCRIPTS 指向 XhsSkills/skills/xhs-apis/scripts
  3. cookie 存本脚本旁 .secrets/xhs_cookie.txt（专用小号 Header String，不上 repo）

用法：
  python probe_and_fetch.py --search "博主名"
  python probe_and_fetch.py --user-url "https://www.xiaohongshu.com/user/profile/ID?xsec_token=...&xsec_source=pc_search"
  python probe_and_fetch.py --user-id ID --xsec-token TOKEN
  可选：--bodies N（抓前 N 篇正文，默认 3；0 = 不抓）
"""
import argparse
import os
import sys
import json
import urllib.parse
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
SECRETS = HERE / ".secrets"


def load_api():
    scripts = os.environ.get("XHS_SKILLS_SCRIPTS")
    if not scripts:
        sys.exit("[!] 未设环境变量 XHS_SKILLS_SCRIPTS（指向 XhsSkills/skills/xhs-apis/scripts）。见 SKILL.md。")
    scripts = Path(scripts)
    runtime = scripts / "runtime" / "spider_xhs_core"
    if not runtime.exists():
        sys.exit(f"[!] 找不到 runtime：{runtime}。确认 XhsSkills 已 clone 且路径对。")
    node_modules = scripts / "node_modules"
    if node_modules.exists():
        os.environ["NODE_PATH"] = str(node_modules)
    os.chdir(runtime)
    sys.path.insert(0, str(runtime))
    try:
        from apis.xhs_pc_apis import XHS_Apis
    except Exception as e:  # noqa: BLE001
        sys.exit(f"[!] import Spider_XHS runtime 失败：{e}\n"
                 "    先装依赖：pip install -r requirements.txt && npm install（在 XhsSkills scripts 目录）")
    return XHS_Apis()


def read_cookie():
    f = SECRETS / "xhs_cookie.txt"
    if not f.exists():
        sys.exit(f"[!] cookie 没配：{f}\n"
                 "    浏览器登录专用小号 → Cookie-Editor 导 Header String → 存这里。见 SKILL.md。")
    for line in f.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s and not s.startswith("#") and "=" in s and "PASTE" not in s:
            return s
    sys.exit(f"[!] {f} 里没有有效 cookie 行")


def g(d, *keys):
    for k in keys:
        v = d.get(k) if isinstance(d, dict) else None
        if isinstance(v, (str, int)) and v not in ("", None):
            return v
    return ""


def check_login(api, cookie):
    s, m, sj = api.get_user_self_info(cookie)
    code = sj.get("code") if isinstance(sj, dict) else "?"
    logged = isinstance(sj, dict) and bool(sj.get("data"))
    print(f"[探针] get_user_self_info: success={s} code={code} logged_in={logged}")
    if not logged:
        sys.exit("[!] cookie 是游客态（code=-100）。小红书搜索游客能用、但看主页笔记流必须登录态。\n"
                 "    确认浏览器里专用小号已登录成功（右上角头像）后重新导出 cookie。")


def resolve_target(api, cookie, args):
    if args.user_url:
        p = urllib.parse.urlparse(args.user_url)
        uid = p.path.split("/")[-1]
        kv = {x.split("=", 1)[0]: x.split("=", 1)[1] for x in p.query.split("&") if "=" in x}
        return uid, kv.get("xsec_token", ""), kv.get("xsec_source", "pc_search")
    if args.user_id:
        return args.user_id, (args.xsec_token or ""), "pc_search"
    # --search：搜候选 + 选 note_count 最高
    s, m, users = api.search_some_user(args.search, 10, cookie)
    if not isinstance(users, list) or not users:
        sys.exit(f"[!] 搜不到用户：{args.search!r}（success={s} msg={m}）")
    print(f"[搜索] {args.search!r} 命中 {len(users)} 个候选：")
    for u in users:
        print(f"    - {str(g(u, 'name'))[:24]:<24} 粉{g(u, 'fans')} 笔记{g(u, 'note_count')} id={g(u, 'id')}")
    def _fans(u):
        f = str(g(u, "fans") or "0").strip()
        try:
            return float(f.replace("万", "")) * 10000 if "万" in f else float(f)
        except ValueError:
            return 0.0

    q = (args.search or "").lower()

    def _score(u):
        name = str(g(u, "name")).lower()
        match = 2 if name.startswith(q) else (1 if q in name else 0)
        return (match, _fans(u))

    best = max(users, key=_score)
    print(f"[选中] {g(best, 'name')}（名字匹配 + 粉丝最多；换人用 --user-id 精确指定）")
    return g(best, "id"), g(best, "xsec_token"), "pc_search"


def main():
    ap = argparse.ArgumentParser(description="小红书博主笔记调研")
    ap.add_argument("--search", help="按名字搜博主（自动选 note_count 最高）")
    ap.add_argument("--user-url", help="博主主页 URL（含 xsec_token）")
    ap.add_argument("--user-id", help="博主 user_id（配 --xsec-token）")
    ap.add_argument("--xsec-token", default="", help="配 --user-id 使用")
    ap.add_argument("--bodies", type=int, default=3, help="抓前 N 篇正文（默认 3；0=不抓）")
    args = ap.parse_args()
    if not (args.search or args.user_url or args.user_id):
        ap.error("至少给一个：--search / --user-url / --user-id")

    cookie = read_cookie()
    api = load_api()
    check_login(api, cookie)

    user_id, xsec_token, xsec_source = resolve_target(api, cookie, args)
    print(f"[抓取] get_user_note_info user_id={str(user_id)[:12]}… source={xsec_source}")
    s, m, rj = api.get_user_note_info(user_id, "", cookie, xsec_token, xsec_source)
    data = rj.get("data", {}) if isinstance(rj, dict) else {}
    notes = data.get("notes") if isinstance(data, dict) else None
    if not notes:
        (HERE / "xhs_last_raw.json").write_text(json.dumps(rj, ensure_ascii=False, indent=2), encoding="utf-8")
        sys.exit(f"[!] 没拿到 notes（success={s} msg={m}）。原始响应存 xhs_last_raw.json。")

    rows = []
    for n in notes:
        nc = n.get("note_card", n) if isinstance(n, dict) else {}
        interact = nc.get("interact_info", {}) if isinstance(nc, dict) else {}
        nid = g(n, "note_id", "id")
        tok = g(n, "xsec_token")
        rows.append({
            "title": g(nc, "display_title", "title") or "(无标题/视频)",
            "note_id": nid,
            "type": g(nc, "type"),
            "liked": interact.get("liked_count", ""),
            "xsec_token": tok,
            "url": f"https://www.xiaohongshu.com/explore/{nid}?xsec_token={tok}" if nid else "",
        })
    print(f"[✓] 拿到 {len(rows)} 篇（has_more={data.get('has_more')}）")

    if args.bodies > 0:
        for r in rows[:args.bodies]:
            nurl = (f"https://www.xiaohongshu.com/explore/{r['note_id']}"
                    f"?xsec_token={r['xsec_token']}&xsec_source=pc_search")
            s2, m2, dj = api.get_note_info(nurl, cookie)
            items = (dj.get("data", {}) or {}).get("items", []) if isinstance(dj, dict) else []
            body = (items[0].get("note_card", {}) or {}).get("desc", "") if items else ""
            r["body"] = body
            print(f"  · {str(r['title'])[:26]}: 正文 {len(body)} 字")

    out = HERE / "xhs_notes.json"
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[✓] 存 {out.name}（{len(rows)} 篇）")


if __name__ == "__main__":
    main()
