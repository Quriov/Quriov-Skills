#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修 cv-cat/Spider_XHS 的 split('=') bug（幂等）。

get_user_all_notes / get_note_info / get_note_all_comment 用
`{kv.split('=')[0]: kv.split('=')[1] for kv in kvs}` 解析 URL 参数，
会截断 base64 `xsec_token` 末尾的 '='（如 ...RB2S8= → ...RB2S8）→ token 失效
→ 小红书返回误导的 code=-100「登录已过期」。本补丁改成 split('=', 1)（只在第一个
'=' 分割，保留末尾 '='）。

用法：
  python patch_spider_xhs.py <XhsSkills/skills/xhs-apis/scripts 目录>
  （或先设 XHS_SKILLS_SCRIPTS 环境变量，则可省略参数）
"""
import os
import sys
from pathlib import Path

OLD = "{kv.split('=')[0]: kv.split('=')[1] for kv in kvs}"
NEW = "{kv.split('=', 1)[0]: kv.split('=', 1)[1] for kv in kvs}"


def main():
    scripts = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("XHS_SKILLS_SCRIPTS", "")
    if not scripts:
        sys.exit("用法: python patch_spider_xhs.py <XhsSkills/skills/xhs-apis/scripts>")
    target = Path(scripts) / "runtime" / "spider_xhs_core" / "apis" / "xhs_pc_apis.py"
    if not target.exists():
        sys.exit(f"[!] 找不到 {target}")
    src = target.read_text(encoding="utf-8")
    if OLD not in src:
        if NEW in src:
            print("[=] 已打过补丁，跳过。")
        else:
            print("[?] 没找到目标代码（上游可能已改结构）。请手动核对 xhs_pc_apis.py 里 split('=') 的用法。")
        return
    count = src.count(OLD)
    target.write_text(src.replace(OLD, NEW), encoding="utf-8")
    print(f"[✓] 已修复 {count} 处 split('=') → split('=', 1)：{target}")


if __name__ == "__main__":
    main()
