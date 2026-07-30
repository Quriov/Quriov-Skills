#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""服务器连接配置读取 + SSH 连接 —— search_x / timeline_x / set_cookie 三者共用。

**为什么抽出来**：原先这三个脚本各自复制了一份 `load_server_config` + `connect_ssh`，
一共三份几乎相同的代码。改认证方式要同时改三处，漏一处就是隐性 bug
（违反"两处相同逻辑就抽共享模块"）。现在只有这一份。

**认证方式**（由 `.secrets/server.json` 里给了什么字段自动决定，无需改代码）：

  1. 给了 `password`      → 密码认证。**向后兼容**：老的 server.json 零改动继续可用。
  2. 给了 `key_filename`  → 指定私钥认证。**推荐**：配合 Tailscale 内网 IP，
                            本机不必存服务器密码，也不必暴露公网 22 端口。
  3. 两个都没给          → 用 ssh-agent + `~/.ssh` 下的默认私钥。

配置示例（推荐形态，走 Tailscale + 私钥，无密码）：

    {"host": "100.102.0.123", "port": 22, "user": "Administrator",
     "key_filename": "~/.ssh/id_ed25519"}

安全：本模块不打印密码、不打印私钥内容，异常信息里也只带异常类型和 paramiko 的原文。
"""
import sys
import json
import time
from pathlib import Path

import paramiko

SKILL_ROOT = Path(__file__).resolve().parent.parent
SERVER_JSON = SKILL_ROOT / ".secrets" / "server.json"

_CONFIG_HELP = (
    '请创建 .secrets/server.json。推荐形态(走 Tailscale 内网 IP + 私钥，本机不存密码)：\n'
    '  {"host":"100.102.0.123","port":22,"user":"Administrator",'
    '"key_filename":"~/.ssh/id_ed25519"}\n'
    '也支持密码形态(向后兼容)：\n'
    '  {"host":"...","port":22,"user":"...","password":"..."}'
)


def load_server_config() -> dict:
    """读 .secrets/server.json 并校验必填字段；缺啥说清楚，不抛栈。"""
    if not SERVER_JSON.exists():
        print(f"[错误] 找不到服务器连接配置：{SERVER_JSON}\n{_CONFIG_HELP}", file=sys.stderr)
        sys.exit(2)
    try:
        with open(SERVER_JSON, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except json.JSONDecodeError as e:
        print(f"[错误] {SERVER_JSON} 不是合法 JSON：{e}\n{_CONFIG_HELP}", file=sys.stderr)
        sys.exit(2)
    if not isinstance(cfg, dict):
        print(f"[错误] {SERVER_JSON} 顶层必须是 JSON 对象。\n{_CONFIG_HELP}", file=sys.stderr)
        sys.exit(2)
    for k in ("host", "port", "user"):
        if not cfg.get(k):
            print(f"[错误] server.json 缺少字段或为空：{k}\n{_CONFIG_HELP}", file=sys.stderr)
            sys.exit(2)
    return cfg


def _auth_kwargs(cfg: dict) -> tuple[dict, str]:
    """按配置决定认证方式；返回 (传给 paramiko.connect 的 kwargs, 给人看的方式名)。"""
    if cfg.get("password"):
        return (
            {"password": cfg["password"], "look_for_keys": False, "allow_agent": False},
            "密码",
        )
    if cfg.get("key_filename"):
        key = str(Path(cfg["key_filename"]).expanduser())
        if not Path(key).exists():
            print(f"[错误] server.json 里的私钥不存在：{key}", file=sys.stderr)
            sys.exit(2)
        return (
            {"key_filename": key, "look_for_keys": True, "allow_agent": True},
            f"私钥({Path(key).name})",
        )
    return ({"look_for_keys": True, "allow_agent": True}, "ssh-agent/默认私钥")


def connect_ssh(cfg: dict, attempts: int = 2) -> paramiko.SSHClient:
    """连服务器；握手失败退避重连（服务器对密集新连接有限流）。"""
    auth, how = _auth_kwargs(cfg)
    last_err = None
    # serial-ok: 退避重连，第 2 次依赖第 1 次失败结果，本质串行不可并发
    for attempt in range(max(1, attempts)):
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(
                hostname=cfg["host"],
                port=int(cfg["port"]),
                username=cfg["user"],
                timeout=30,
                banner_timeout=30,
                auth_timeout=30,
                **auth,
            )
            return client
        except Exception as e:  # noqa: BLE001
            last_err = e
            try:
                client.close()
            except Exception:  # noqa: BLE001
                pass
            if attempt < max(1, attempts) - 1:
                print(
                    f"[信息] SSH 握手失败({type(e).__name__})，5 秒后退避重连一次…",
                    file=sys.stderr,
                )
                time.sleep(5)
    print(
        f"[SSH 连接失败] {type(last_err).__name__}: {last_err}\n"
        f"[信息] 认证方式={how} host={cfg['host']} user={cfg['user']}",
        file=sys.stderr,
    )
    sys.exit(1)
