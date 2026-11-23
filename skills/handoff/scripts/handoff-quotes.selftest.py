#!/usr/bin/env python3
"""交接原话命令的自测，仅用临时转录。"""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).with_name("handoff-quotes.py")


def user(body, origin="human", **fields):
    return {"type": "user", "origin": {"kind": origin}, "message": {"content": body}, **fields}


def queued(body, origin="human"):
    return {"type": "attachment", "attachment": {"type": "queued_command",
            "origin": {"kind": origin}, "prompt": body}}


class HandoffQuotesTests(unittest.TestCase):
    def run_cli(self, *recs):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "session.jsonl"
            path.write_text("损坏的 JSON 行\n" +
                            "\n".join(json.dumps(r, ensure_ascii=False) for r in recs), encoding="utf-8")
            return subprocess.check_output([sys.executable, str(SCRIPT), str(path)], text=True)

    def test_last_boundary_only_and_verbatim_text(self):
        mark = {"type": "system", "compactMetadata": {}}
        result = self.run_cli(
            user("最早的话"), mark, user("上一个压缩段的话"), mark,
            user("<system-reminder>系统附加\n一并清理</system-reminder><pasted_content id='1'>先核账。\n  因为钱要对上。</pasted_content>"),
            queued([{"type": "image"}, {"type": "text", "text": "这句来自队列。"}]),
            user("好")
        )
        self.assertEqual(result, "## 上一棒最后一次压缩后他说的话\n\n"
                                 "**原话 1**\n\n先核账。\n  因为钱要对上。\n\n"
                                 "**原话 2**\n\n这句来自队列。\n\n**原话 3**\n\n好\n")

    def test_machine_transcript_records_are_excluded(self):
        result = self.run_cli(
            user("插件内容", origin="plugin"),
            user("摘要", isCompactSummary=True),
            user("元消息", isMeta=True),
            {"type": "queue-operation", "content": "只有入队记录"},
            {"type": "user", "message": {"content": "没有来源"}},
            queued("定时任务", origin="scheduled_task"),
            user("<system-reminder>提示</system-reminder><task-notification>结束</task-notification>"),
            queued("Background (from the session that started this one)"),
            queued("/compact 保留内容"),
            user("<pasted_content>你是 FDE-总控 v1.2(第 3 任)。</pasted_content>"),
            user("发给业务同事：原话仍然属于本人。"),
        )
        self.assertEqual(result, "## 上一棒最后一次压缩后他说的话\n\n"
                                 "**原话 1**\n\n发给业务同事：原话仍然属于本人。\n")

    def test_first_segment_keeps_repeated_short_quotes(self):
        result = self.run_cli(user("继续"), queued("继续"))
        self.assertEqual(result.count("\n继续\n"), 2)

    def test_empty_segment_is_explicit(self):
        result = self.run_cli(user("压缩前的话"), {"compactMetadata": {}})
        self.assertEqual(result, "## 上一棒最后一次压缩后他说的话\n\n（本段无本人文字。）\n")


if __name__ == "__main__":
    unittest.main()
