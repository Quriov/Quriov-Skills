#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
拉取指定 X (Twitter) 博主的时间线推文 —— 编排器(orchestrator)。

架构：与 search_x.py 完全一致——本机过不了 X 反爬，把任务通过 SSH 发到美国硅谷
服务器上跑(twikit 环境已验证)，结果(JSON)传回本机 stdout。区别只在"干什么"：
  - search_x.py  → 按关键词搜推文(client.search_tweet)
  - timeline_x.py→ 按博主拉时间线(client.get_user_by_screen_name + user.get_tweets)
两者共用同一台服务器、同一份 search.json cookie、同一套 SSH/SFTP 编排模式。

逻辑(同 search_x.py)：
  1. 从 .secrets/server.json 读服务器连接信息(不写死)。
  2. paramiko 连服务器(AutoAddPolicy, timeout 30; 握手失败退避重连 1 次)。
  3. SFTP 上传远程脚本到服务器临时路径。
  4. 用服务器 venv 的 python 执行远程脚本，捕获 stdout。
  5. 删除远程临时脚本。
  6. 把远程脚本的 JSON 输出原样打到本机 stdout(给 AI 读)。
  7. 关连接。

用法：
  python timeline_x.py dontbesilent
  python timeline_x.py @dontbesilent --count 30
  python timeline_x.py dontbesilent --type Replies

参数：
  screen_name        博主的 X 用户名(位置参数，必填；带不带 @ 都行)
  --count N          返回推文条数(默认 20)
  --type MODE        Tweets(默认) / Replies / Media / Likes

安全：服务器密码只从 .secrets/server.json 读，不打印密码、不打印 cookie。
"""
import sys
import json
import time
import uuid
import argparse
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import paramiko  # noqa: E402

SKILL_ROOT = Path(__file__).resolve().parent.parent
SERVER_JSON = SKILL_ROOT / ".secrets" / "server.json"

# 服务器上的固定路径(独立 X 工具箱 QuriovXTools，与 ai-infohub 分开)——与 search_x.py 一致
REMOTE_PYTHON = r"C:\QuriovXTools\.venv\Scripts\python.exe"
REMOTE_COOKIES = r"C:\QuriovXTools\cookies\search.json"
REMOTE_TEMP_DIR = r"C:\Users\Administrator\AppData\Local\Temp"

# 远程脚本(上传到服务器执行)。字段用 getattr 兜底，避免单字段缺失导致整脚本崩。
REMOTE_SCRIPT = r'''
import asyncio, sys, json
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from twikit import Client

async def main():
    screen_name = sys.argv[1].lstrip("@")
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    tweet_type = sys.argv[3] if len(sys.argv) > 3 else "Tweets"
    client = Client(language="en-US")
    client.load_cookies(r"C:\QuriovXTools\cookies\search.json")
    user = await client.get_user_by_screen_name(screen_name)
    tweets = await user.get_tweets(tweet_type, count=count)
    out = []
    for t in list(tweets)[:count]:
        tid = getattr(t, "id", None)
        out.append({
            "text": getattr(t, "full_text", None) or getattr(t, "text", None),
            "likes": getattr(t, "favorite_count", None),
            "retweets": getattr(t, "retweet_count", None),
            "replies": getattr(t, "reply_count", None),
            "quotes": getattr(t, "quote_count", None),
            "views": getattr(t, "view_count", None),
            "created_at": str(getattr(t, "created_at", "")),
            "lang": getattr(t, "lang", None),
            "tweet_id": tid,
            "url": f"https://x.com/{screen_name}/status/{tid}" if tid else None,
        })
    print(json.dumps({
        "user": screen_name,
        "user_name": getattr(user, "name", None),
        "followers": getattr(user, "followers_count", None),
        "total_tweets": getattr(user, "statuses_count", None),
        "type": tweet_type,
        "count": len(out),
        "tweets": out,
    }, ensure_ascii=False))

asyncio.run(main())
'''


def load_server_config() -> dict:
    if not SERVER_JSON.exists():
        print(
            f"[错误] 找不到服务器连接配置：{SERVER_JSON}\n"
            '请创建 .secrets/server.json，格式：\n'
            '{"host":"...","port":22,"user":"...","password":"..."}',
            file=sys.stderr,
        )
        sys.exit(2)
    with open(SERVER_JSON, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    for k in ("host", "port", "user", "password"):
        if k not in cfg:
            print(f"[错误] server.json 缺少字段：{k}", file=sys.stderr)
            sys.exit(2)
    return cfg


def connect_ssh(cfg: dict) -> paramiko.SSHClient:
    """连服务器；握手失败退避重连 1 次(服务器对密集新连接有限流)。"""
    last_err = None
    # serial-ok: 退避重连，第 2 次依赖第 1 次失败结果，本质串行不可并发
    for attempt in range(2):
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(
                hostname=cfg["host"],
                port=int(cfg["port"]),
                username=cfg["user"],
                password=cfg["password"],
                timeout=30,
                banner_timeout=30,
                auth_timeout=30,
                look_for_keys=False,
                allow_agent=False,
            )
            return client
        except Exception as e:  # noqa: BLE001
            last_err = e
            try:
                client.close()
            except Exception:  # noqa: BLE001
                pass
            if attempt == 0:
                print(
                    f"[信息] SSH 握手失败，{type(e).__name__}，5 秒后退避重连一次…",
                    file=sys.stderr,
                )
                time.sleep(5)
    print(f"[SSH 连接失败] {type(last_err).__name__}: {last_err}", file=sys.stderr)
    sys.exit(1)


def main() -> int:
    parser = argparse.ArgumentParser(description="拉取指定 X 博主时间线(走硅谷服务器)")
    parser.add_argument("screen_name", help="博主 X 用户名(带不带 @ 都行)")
    parser.add_argument("--count", type=int, default=20, help="返回条数(默认 20)")
    parser.add_argument(
        "--type",
        choices=["Tweets", "Replies", "Media", "Likes"],
        default="Tweets",
        help="时间线类型：Tweets(默认) / Replies / Media / Likes",
    )
    args = parser.parse_args()

    screen_name = args.screen_name.lstrip("@")

    cfg = load_server_config()
    ssh = connect_ssh(cfg)

    remote_script_path = f"{REMOTE_TEMP_DIR}\\_xtimeline_{uuid.uuid4().hex[:12]}.py"

    try:
        # 0. 预检：搜索账号 cookie 必须已配置(search.json 存在)，否则友好提示并退出，不崩、不白跑远程
        sftp = ssh.open_sftp()
        try:
            try:
                sftp.stat(REMOTE_COOKIES)
            except IOError:
                print(
                    "[搜索 cookie 未配置] 服务器上找不到搜索 cookie："
                    f"{REMOTE_COOKIES}\n"
                    "请先跑 `python scripts\\set_cookie.py --role search --from-firefox` "
                    "配好搜索账号 cookie(会上传为 search.json)，再来拉时间线。",
                    file=sys.stderr,
                )
                return 2
        finally:
            sftp.close()

        # 1. SFTP 上传远程脚本
        sftp = ssh.open_sftp()
        try:
            with sftp.open(remote_script_path, "w") as rf:
                rf.write(REMOTE_SCRIPT)
        finally:
            sftp.close()

        # 2. 执行远程脚本(参数用双引号包，防用户名含特殊字符)
        cmd = (
            f'"{REMOTE_PYTHON}" "{remote_script_path}" '
            f'"{screen_name}" {args.count} {args.type}'
        )
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=120)
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        exit_code = stdout.channel.recv_exit_status()

        # 3. 删除远程临时脚本
        try:
            ssh.exec_command(f'del /f /q "{remote_script_path}"')
        except Exception:  # noqa: BLE001
            pass

        if exit_code != 0 or not out.strip():
            print(
                f"[远程执行失败] exit_code={exit_code}\n"
                f"--- 远程 stderr ---\n{err.strip()}",
                file=sys.stderr,
            )
            print(
                "[排查方向] (1) 服务器 venv/twikit 是否可用(C:\\QuriovXTools\\.venv) "
                "(2) cookie 是否过期(C:\\QuriovXTools\\cookies\\search.json) "
                "(3) 用户名是否拼错/账号是否存在 (4) X 风控。"
                "cookie 失效需重新提取并上传 search.json。",
                file=sys.stderr,
            )
            return 1

        # 4. 远程输出原样打到本机 stdout(它已是 JSON)
        sys.stdout.write(out)
        if not out.endswith("\n"):
            sys.stdout.write("\n")

        # 解析一下报条数(失败不影响主输出)
        try:
            data = json.loads(out.strip().splitlines()[-1])
            print(
                f"[信息] @{data.get('user')} 共返回 {data.get('count')} 条 "
                f"(type={args.type}, followers={data.get('followers')})",
                file=sys.stderr,
            )
        except Exception:  # noqa: BLE001
            pass
        return 0
    finally:
        ssh.close()


if __name__ == "__main__":
    raise SystemExit(main())
