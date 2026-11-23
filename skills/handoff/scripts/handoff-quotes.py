#!/usr/bin/env python3
"""从本会话转录抽最后一次压缩后的原话，生成可直接贴进开场白的一节。

下面的转录解析函数(records / human_text / is_boundary 等)内联自作者本机 checkpoint 技能的
his_words.py,本仓没有 checkpoint 技能,内联后本脚本自包含、不依赖别的技能。两边口径要同步改。
"""
import argparse
import json
from pathlib import Path
import re


# ---- 内联自 checkpoint/scripts/his_words.py ----
# 识别机器插入的开头(与作者本机 hooks/board-reply-sync.js 的 classifyStart 同口径)。
MACHINE_HEAD = re.compile(
    r"^(?:<(?:ci-monitor-event|side-sessions-event|task-notification|scheduled-task|"
    r"cross-session-message|command-name|command-message|command-args|local-command-stdout|"
    r"local-command-stderr|local-command-caveat|bash-input|bash-stdout|bash-stderr)\b|"
    r"Background \(from the session that started this one\)|Another Claude session sent a message|"
    r"The [\w-]+ plugin sent a message|\[Request interrupted|Continue from where you left off|"
    r"Your response above was cut off|【机器压缩】|/(?:compact|checkpoint|handoff)\b|!)"
)
INIT_PROMPT = re.compile(r"^你是\s*\S{1,40}?\s*v\d+(?:\.\d+)?\s*(?:[(（]第\s*\d+\s*任|[,，。])")
REMINDER = re.compile(r"<system-reminder>.*?</system-reminder>", re.S)
PASTED = re.compile(r"</?pasted_content\b[^>]*>")


def records(path):
    with open(path, encoding="utf-8") as stream:
        for line in stream:
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(record, dict):
                yield record


def clean_text(text):
    return PASTED.sub("", REMINDER.sub("", text)).strip()


def body_of(content):
    if isinstance(content, str):
        return clean_text(content)
    if isinstance(content, list):
        return clean_text("\n".join(
            block["text"] for block in content
            if isinstance(block, dict) and block.get("type") == "text"
            and isinstance(block.get("text"), str)
        ))
    return ""


def human_text(record):
    source = record
    if record.get("isMeta") or record.get("isCompactSummary") or record.get("isSidechain"):
        return ""
    if record.get("type") == "attachment":
        source = record.get("attachment") or {}
        if source.get("type") != "queued_command":
            return ""
        content = source.get("prompt")
    elif record.get("type") == "user":
        content = (record.get("message") or {}).get("content")
    else:
        return ""
    if (source.get("origin") or {}).get("kind") != "human":
        return ""
    body = body_of(content)
    return "" if MACHINE_HEAD.match(body) or INIT_PROMPT.match(body) else body


def is_boundary(record):
    return record.get("compactMetadata") is not None or record.get("subtype") == "compact_boundary"
# ---- 内联结束 ----


def last_words(recs):
    words = []
    for record in recs:
        if is_boundary(record):
            words.clear()
        else:
            body = human_text(record)
            if body:
                words.append(body)
    return words


def render_quotes(words):
    heading = "## 上一棒最后一次压缩后他说的话"
    if not words:
        return heading + "\n\n（本段无本人文字。）"
    entries = [f"**原话 {i}**\n\n{word}" for i, word in enumerate(words, 1)]
    return "\n\n".join([heading, *entries])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("transcript", type=Path)
    args = parser.parse_args()
    try:
        print(render_quotes(last_words(records(args.transcript))))
    except (OSError, UnicodeError) as exc:
        parser.exit(2, f"转录读不到：{exc}\n")


if __name__ == "__main__":
    main()
