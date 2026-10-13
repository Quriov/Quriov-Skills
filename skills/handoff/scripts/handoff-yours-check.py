#!/usr/bin/env python3
"""handoff-yours-check.py — 交接文档 / 检查点的未决表里,每件「等他」的事必须对得上板上的一张卡。

为什么存在(宇通 2026-10-13 拍「两处都做」的第二处):
  电商-投流 v1.6 压缩前检查点未决表 13 行,其中「等宇通」的事从 10-06 起每一棒原样抄进交接文档,
  从没挂过卡,板 lint 全程 PASS —— 他只看板,所以这些事对他等于不存在。
  本 skill Step 3 早有「等他点头的同一轮挂成卡」这句话(09-30 实测 9 件上卡 0 件),光靠那句话不够。

判法(对的是「对不对得上」,不是「填没填」):
  未决表里状态列写着等他的行 ⇒ 行内必须出现一个卡号 / 行编号,而且它此刻真在板的「要你的」里
  (`board.py yours <板> --json` 的 cards[].id 或 rows[].ack)。

用法:
  handoff-yours-check.py --doc <交接文档或检查点.md> --board <板.html> [--board <别的线的板.html> …]
  handoff-yours-check.py --doc <…> --no-board "这条线没有板"      # 没板的线:跳过,但要出声
退出码:0 全对得上(或没板) · 1 有对不上的行 · 2 没法判(没找到未决节 / 读不到板)
"""
import argparse
import json
import os
import re
import subprocess
import sys

BOARD_PY = os.path.expanduser("~/.claude/scripts/board.py")
HEAD_RE = re.compile(r"^(#{2,4})\s.*(未决|pending|Pending|PENDING)")
# 表格行:只看最后一列(状态列)。这一列词汇很窄,所以放得宽。
WAIT_CELL = re.compile(r"^宇通$|^宇通[、,，/ ]|等宇通|球在宇通|宇通没|请宇通|"
                       r"等他|等你|他拍|你拍|他没回|他挂起|球在他|待他|要他(拍|做|删|动手|定)")
# 非表格行(列表 / 段落):整行都是自由文字,只认明确的「等他」说法,免得叙述里提到他就报。
WAIT_LINE = re.compile(r"等宇通|球在宇通|等他拍|等你拍|等他点头|等他回|他没回|等他动手|等你动手")
ASK_RE = re.compile(r"ask-[0-9a-f]{8}")


def pending_section(lines):
    """返回 [(行号, 文本)]:未决节从标题下一行到下一个同级或更高级标题。"""
    start = level = None
    for i, ln in enumerate(lines):
        m = HEAD_RE.match(ln)
        if m:
            start, level = i, len(m.group(1))
            break
    if start is None:
        return None
    out = []
    for j in range(start + 1, len(lines)):
        m = re.match(r"^(#{1,6})\s", lines[j])
        if m and len(m.group(1)) <= level:
            break
        out.append((j + 1, lines[j]))
    return out


def split_items(section):
    """把未决节拆成一件一件:[(行号, 整行文本, 状态文本, 是不是表格行)]。"""
    items, seen_header = [], False
    for no, ln in section:
        s = ln.strip()
        if s.startswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if all(re.fullmatch(r":?-{2,}:?", c or "--") for c in cells):
                continue
            if not seen_header:
                seen_header = True      # 表头那一行
                continue
            items.append((no, s, cells[-1], True))
        else:
            seen_header = False if not s else seen_header
            if re.match(r"^([-*+]|\d+[.、)])\s", s):
                items.append((no, s, s, False))
    return items


def load_yours(board, stub):
    if stub:
        return json.load(open(stub, encoding="utf-8"))
    r = subprocess.run([sys.executable, BOARD_PY, "yours", board, "--json"],
                       capture_output=True, text=True)
    if r.returncode != 0 and "invalid choice: 'yours'" in (r.stderr or ""):
        raise LookupError("本机的 board.py 还没有 yours 命令(状态板工具太旧)")
    if r.returncode != 0:
        raise RuntimeError(f"board.py yours 退出码 {r.returncode}:{(r.stderr or r.stdout).strip()[:300]}")
    return json.loads(r.stdout)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--doc", required=True)
    ap.add_argument("--board", action="append", help="可给多次:等他的事挂在别的线板上时把那块板也给上")
    ap.add_argument("--no-board", metavar="理由")
    ap.add_argument("--yours-json", help="测试用:直接给 board.py yours --json 的输出文件")
    a = ap.parse_args()

    lines = open(a.doc, encoding="utf-8").read().split("\n")
    section = pending_section(lines)
    if section is None:
        print(f"✗ 没法判:{a.doc} 里没找到未决节(标题含「未决」或 pending)。没有未决的事也要留这一节并写「无」。")
        return 2
    items = split_items(section)
    waiting = [it for it in items if (WAIT_CELL if it[3] else WAIT_LINE).search(it[2])]
    print(f"未决节 {len(items)} 件,其中等他的 {len(waiting)} 件")
    if not waiting:
        print("✓ 没有等他的事,不用对板")
        return 0

    if not a.board and not a.yours_json:
        if a.no_board:
            print(f"⏭ 跳过对板(这条线没有板:{a.no_board})。等他的这 {len(waiting)} 件必须写进接班开场白,让下一棒开局就问他:")
            for no, text, _, _ in waiting:
                print(f"   · 第 {no} 行:{text[:70]}")
            return 0
        print("✗ 没法判:有等他的事,但没给 --board。没板的线用 --no-board \"理由\"。")
        return 2
    try:
        if a.yours_json:
            y = load_yours(None, a.yours_json)
        else:
            y = {"cards": [], "rows": []}
            for b in a.board:
                one = load_yours(b, None)
                y["cards"] += one.get("cards", [])
                y["rows"] += one.get("rows", [])
    except LookupError as e:
        print(f"⏭ 跳过对板:{e}。等他的这 {len(waiting)} 件请人工对一遍板上「要你的」。")
        return 0
    except Exception as e:
        print(f"✗ 没法判:读不到板上「要你的」—— {e}")
        return 2
    # 机器卡(rows-on-you / blocked-on-you …)一张里列着好几行,不指向任何一件具体的事 ⇒ 不算对上;
    # 只认手写卡(ask-…)和标着要他的行。
    hand = [c for c in y.get("cards", []) if not c.get("machine")]
    on_board = {c["id"] for c in hand} | {r["ack"] for r in y.get("rows", [])}
    for c in hand:
        if c.get("row"):
            on_board.add(c["row"])
    print(f"板上此刻要他的:手写卡 {len(hand)} 张,标着要他的行 {len(y.get('rows', []))} 行")

    bad = []
    for no, text, status, _ in waiting:
        hit = [i for i in on_board if i and i in text]
        if hit:
            continue
        stale = ASK_RE.findall(text)
        why = (f"写了 {'、'.join(stale)},但板上「要你的」里没有这张卡(答过被拿掉了?那这行就不该还写等他)"
               if stale else "没带卡号")
        bad.append((no, text, status, why))
    if not bad:
        print(f"✓ 等他的 {len(waiting)} 件都对得上板上的卡")
        return 0
    print(f"✗ {len(bad)} 件等他的事在板上没有对应的卡 —— 他只看板,这几件对他等于不存在:")
    for no, text, status, why in bad:
        print(f"   · 第 {no} 行「{text[:60]}…」状态「{status[:40]}」:{why}")
    print("  ⇒ 一件一张卡:`board.py ask <板> --q \"他能直接回答的问题\" --rec \"建议\" --cost \"不拍卡住什么\"`"
          "(要他动手的加 --do --steps),把回来的 ask-xxxxxxxx 写进那一行;")
    print("  ⇒ 一行里并着几件的拆开,一件一行;其实不等他了的,把状态列改成现在真实的状态。")
    return 1


if __name__ == "__main__":
    sys.exit(main())
