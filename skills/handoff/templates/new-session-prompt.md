---
title: New Session Initialization Prompt v2 — Template (skill-bundled generic default)
purpose: Drafted by /handoff for next CC. Designed for max focus, min noise. 本文件是 skill 自带的【通用兜底默认】, 随 skill 分发, 永远存在 — 当项目级 `<project>/.claude/templates/` 与用户级 `~/.claude/templates/` 都没有时由 Step 4 命中。项目想定制就放项目级那份覆盖它。
variables:
  - "{{track}}": 接班轨道 (A / B / 独立任务 / 单支线项目-跳过)
  - "{{type}}": business-continuation / debug / system-upgrade / handoff-take-over / new-independent
  - "{{handoff_doc_path}}": 主交接文档路径
  - "{{warnings_top3}}": 本 turn 学到的 top 3 警告
---

# 接班 prompt — {{track}} 轨道 / {{type}}

你接班的是 **{{track}}** 轨道, 任务类型 **{{type}}**。

## 按顺序做这 6 件事

### 1. Live verify (必跑, 不准信 memory)

- 跑 `git log origin/main --oneline | head -10`
- 跑 `git status --short`
- **Read 项目 CLAUDE.md 找 "live verify" 章节**, 跑里面列的项目特定命令
  (e.g. ssh prod / docker ps / API ping / 项目自定的状态查询)
  - 项目 CLAUDE.md 没这章节 → 此项目没配, 跳过

### 2. 必读 (只这 3 个, 不要扩展)

- **本 turn 交接文档**: {{handoff_doc_path}}
  ← 你的主要 ground truth, **必须主动 Read** (不自动 load)
- **项目 team-shared onboarding doc** (如 `docs/AI-CONTEXT.md`: iron rule + Tier A pointer, git, 跨成员共享)
  ← 有则必主动 Read (常含 iron rule: 沟通语言 / 不代号 / 不假完成 / memory drift 防御)
- **项目 CLAUDE.md**: 自动 load 但**必须主动 review** 当前 state 章节

⚠ **不要预先 Read** 其他 handoff doc / 个人 memory (Tier B/C lookup) / 其他轨道 memory ——
任务真撞到需要时再读, 不要 hoard context (context rot 物理限制)

### 3. 别动这些 (其他轨道地盘 / 单支线项目跳过)

如果项目有 `<project>/.claude/active-tracks.yaml`:
- Read 它, 找出**其他轨道**的 `worktree_path` / `files_to_modify` / `forbidden_files`
- 那些 = 你的 forbidden zone, 不要 Edit / Write

没这 file = 单支线项目, 跳过此 step。

### 4. Top 3 警告 (本 turn 现学的)

{{warnings_top3}}

### 5. 内化复述 (动手前, 写在你第一条回复里 — 防"接班丢设计意图")

读完必读后, **动手前**用 3-5 句复述给用户扫一眼 (不等确认, 不阻塞; 理解错用户会当场打断):

- 本条线的**北极星/目标**一句 + 当前在哪个阶段/档位
- **有意延后 vs 真缺口**: 哪些是设计上故意没做的, 哪些是真 pending
- 本 turn 要做什么 + 它在整条线里的位置

长线 track (有 dossier / 设计 spec) 必做; 纯执行型 ad-hoc 小任务可缩成 1-2 句 (目标 + 不在 scope 的)。
**复述不出"有意延后的是什么" = 你没读懂, 回去重读** — 别带着半懂开工 (真实事故: 接班 CC 顺利执行了任务, 但整条线设计意图没 load, 被用户追问三次才现挖)。

### 6. 第一个 task

Read {{handoff_doc_path}} 的 "⚠ What's still pending" section,
选第一个 unblocked item 开始。

如果起 Plan Mode, 走项目的 Plan Mode 模板 (如有, 含 § Audit Existing 决策表)。

---

## 沟通规则 (cross-cutting)

- **用中文跟用户沟通** (除非用户切英文)
- **不要用代号** ("Phase X / Wave Y / G3") → 直接讲清楚事情
- **不要 claim "完成" / ✅** 除非带 file:line 或 commit hash evidence
- **memory 自报 ≠ ground truth** → 不确定就跑命令 verify
