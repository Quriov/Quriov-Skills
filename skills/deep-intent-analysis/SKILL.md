---
name: deep-intent-analysis
description: MUST invoke BEFORE responding to feature/modification/optimization/refactor/redesign requests, in ANY language (EN/中文). Performs 3-layer intent analysis (surface→direct→deeper goal / 表面-直接-深层) and proposes 2-8 related improvements (举一反三 / 添加/新增/改/优化/重构/设计/add/create/build/optimize/refactor/improve) serving the same deeper goal, then STOPS for user scope confirmation before any code. Runs UPSTREAM of brainstorming/planning skills. Skip ONLY for: pure factual questions (什么是X/what is X), typo fixes, short replies (好/ok/yes), an already-scoped handoff/接班 take-over (task+boundaries+stop-go already given → follow it), or messages prefixed with skip:/quick:/直接:.
---
<!-- deep-intent-analysis-skill-rev: 2026-07-11 -->

# Deep Intent Analysis + 举一反三

<EXTREMELY-IMPORTANT>
If you think there's even a 10% chance the user wants something beyond their literal request, you MUST run Steps 1-3 of this skill. The cost of running when unneeded is 3 table rows. The cost of skipping when needed is a failed scope contract and multi-round rework. Default to invoking — miss the gate, and the user will call it out.
</EXTREMELY-IMPORTANT>

<HARD-GATE>
Do NOT write code, edit files, or invoke implementation skills (plan/tdd-workflow/brainstorming/etc.) until:
1. You have output Step 1 (3-layer intent table), AND
2. You have output Step 2 (extrapolation table), AND
3. The user has EXPLICITLY confirmed scope via a follow-up message.

This applies regardless of how small the request seems. This skill runs UPSTREAM of brainstorming, planning, and TDD skills — invoke it first.
</HARD-GATE>

## When to use this skill (TRIGGERING)

**You MUST invoke this skill** on ANY user message that could be one of these:

| Type | Chinese examples | English examples |
|---|---|---|
| Feature request | "添加X", "新增Y", "实现Z", "做一个", "帮我写" | "add X", "create Y", "build Z", "implement" |
| Modification | "改X", "修改", "调整", "换成", "把X改成Y" | "change X", "modify", "switch to", "turn X into Y" |
| Optimization | "优化", "改进", "提升", "完善", "更好", "更快" | "optimize", "improve", "enhance", "better", "faster" |
| Refactor | "重构", "重写", "整理" | "refactor", "rewrite", "clean up" |
| Design question | "该怎么设计", "架构如何", "思路是什么", "方案是什么" | "how should we design", "what's the architecture", "how would you approach" |
| Multi-item asks | anything with "还有", "以及", "另外", "同时" | anything with "also", "and", "plus" |
| Polite imperatives | "帮我X", "能不能X", "需要X", "顺便X" | "can you X", "please X", "I need X" |
| Vague improvement | "这里能不能更好一点", "这个不太对" | "this could be better", "something feels off" |

## Red Flags — STOP, you're rationalizing

If you catch yourself thinking any of these, **STOP** and invoke the skill:

| Rationalization | Reality |
|---|---|
| "This is too small to need intent analysis" | Small tasks are where scope creep starts. 3 lines of analysis costs less than 3 rounds of rework. |
| "I already know what they mean" | Knowing ≠ outputting. User needs to see the 深层目标 to confirm or correct it. |
| "Let me just start, I can extrapolate mid-way" | Mid-way extrapolation = scattered, not batched. User pays cost twice. |
| "The request is very specific" | Specific surface ≠ specific deeper goal. Check Layer 3 anyway. |
| "They said quick change" | If they didn't prefix `quick:` or `skip:`, treat as normal. |
| "It's obvious from context" | Obvious to you ≠ obvious to them. The gate is for them, not you. |
| "This is a follow-up question in the same conversation" | See "Multi-turn behavior" below — may still need fresh analysis. |

## When to skip this skill (HARD EXEMPTIONS)

Skip ONLY if the message is CLEARLY one of:

1. **Pure factual question** — "什么是 X", "X 是什么", "what is X", "how does X work", ends in `?` asking for explanation not change
2. **Single-line typo/wording fix** — "改个 typo", "拼写错了", "fix a typo"
3. **Short reply / confirmation** — "好", "对", "嗯", "ok", "继续", "yes", "no", "没问题", "行"
4. **User explicit override** — message starts with `skip:`, `quick:`, `直接:`, `快速:`
5. **Pasted error/log for diagnosis** — user pasted stack trace or error log, asking "这是什么错" / "what's this error"
6. **Request to modify Claude's previous text reply** (not code) — "把刚才的回复改一下措辞"
7. **Handoff / 接班 take-over, scope already defined** — the message hands off / resumes work AND already gives task + order/boundaries + stop/go (决策门) → follow it directly; do NOT re-run analysis or re-confirm scope (e.g. "按 handoff 接 Task 5 / 继续接班 / 接任务板 #X"). ⚠️ Exception: DO run Steps 1-3 (scoped to just the new part) if the taker adds a NEW independent feature, changes a boundary, or hits an outcome-changing choice — a handoff exempts *continuation*, not *new scope*.

When skipping, answer directly without invoking this skill.

## The protocol (MANDATORY when invoked — every step)

### Step 1 — Three-layer intent analysis

Output this table before any other content:

```markdown
## 意图分析

| 层级 | 内容 |
|------|------|
| 1. 表面需求 | [literal restatement of the request] |
| 2. 直接目的 | [the immediate outcome they want] |
| 3. 深层目标 | [the underlying goal/value they're optimizing for] |
```

If Layer 3 contradicts or suggests a better path than Layer 1, flag it explicitly with a "⚠️ 深层目标与表面需求可能有更优路径" note.

### Step 2 — 举一反三 (2-8 extrapolations)

Based on **Layer 3** (deeper goal), propose **2-8 additional items** the user did NOT ask for but that serve the same deeper goal.

**Quantity rule**: Stop when quality drops. 2 excellent extrapolations beat 6 padded ones.

```markdown
## 举一反三

| # | 补充建议 | 为什么服务同一深层目标 | 推荐/可选 |
|---|---------|------------------------|-----------|
| 1 | ... | ... | 推荐 |
| 2 | ... | ... | ... |
```

### Step 3 — STOP and get scope confirmation

Write the confirmation prompt **in the same language as the user's message**:

- **User wrote in Chinese** → "以上是意图分析和补充建议。要全做哪几条？还是只做原需求？"
- **User wrote in English** → "Above is the intent analysis and extrapolations. Which items should I tackle — all, a subset, or just the original request?"
- **Mixed/unclear** → Chinese by default (per user's global CLAUDE.md)

**Do not write code, do not make file edits** until the user confirms scope.

### Step 4 — Execute agreed scope in one batch

Once user confirms, execute all agreed items together. Don't re-ask for each item.

## Multi-turn behavior

- **First invocation in a thread** — run full Steps 1-3, UNLESS it's an already-scoped handoff take-over (exemption 7 → follow the handoff directly).
- **User adds a new independent ask mid-conversation** ("再加个 X", "also add Y", "顺便做一下 Z") — run full Steps 1-3 **scoped to just the new item**.
- **User refines agreed scope** ("去掉 4", "把 1 和 3 的优先级调换") — NO re-trigger. Just confirm and execute.
- **User says "继续" / "go ahead" during Step 4 execution** — NO re-trigger. Continue executing the batch.
- **New session / post-compaction** — treat as fresh thread, re-trigger on first qualifying message.
- **Pure debug/test of already-agreed feature** — NO re-trigger. Just work on the bug.

## Thinking dimensions for 举一反三

When generating extrapolations, scan these dimensions:

- **同一页面/模块其他相似问题** — 改一个按钮 → 同模块其他按钮是否也该改
- **用户旅程前后摩擦点** — 加登录页 → 注册/忘记密码/会话过期
- **跨模块一致性** — 前端改字段名 → 后端/DB/API 文档/测试
- **边界情况** — 空数据 / 错误 / 权限不足 / 网络失败
- **效率乘数** — 重复任务能否自动化/批量化/模板化
- **UX 细节** — loading / 错误提示 / 确认对话框 / 键盘快捷键
- **数据与状态** — 持久化 / 缓存失效 / 并发 / 迁移
- **可观测性** — 日志 / 错误上报 / 性能监控 / 埋点
- **性能 & 规模** — N+1 / 批量 / 分页 / 缓存

## Anti-patterns (DO NOT)

1. ❌ Writing code or editing files before outputting Step 1-2
2. ❌ Skipping "举一反三" and only restating surface request
3. ❌ Proposing extrapolations unrelated to Layer 3 (scattered suggestions)
4. ❌ Padding to 8 items when only 2-3 are genuinely relevant (quality > quantity)
5. ❌ Asking one-by-one about each extrapolation (batch the decision instead)
6. ❌ Jumping to Step 4 without user confirming scope
7. ❌ Running brainstorming/plan/tdd skills before this one (those are downstream)

## Concrete examples

### ✅ Correct activation — "给电商后台加个批量导出订单的功能"

```markdown
## 意图分析
| 层级 | 内容 |
|------|------|
| 1. 表面需求 | 电商后台加"批量导出订单"功能 |
| 2. 直接目的 | 一次性下载多个订单，避免逐个操作 |
| 3. 深层目标 | 让运营/财务能高效做数据分析和对账 |

## 举一反三
| # | 补充建议 | 为什么 | 推荐 |
|---|---|---|---|
| 1 | 按日期/状态/渠道筛选后导出 | 深层目标是"高效分析"，筛选是前提 | 推荐 |
| 2 | 导出格式支持 Excel/CSV/JSON | 下游工具需求不同 | 推荐 |
| 3 | 大数据量异步任务 + 飞书通知 | 避免前端阻塞 | 推荐 |
| 4 | 导出记录存档（谁/何时/何字段）| 合规审计 | 可选 |
| 5 | 保存导出模板 | 重复导出零配置 | 可选 |
| 6 | 敏感字段脱敏选项 | 外部分享安全 | 推荐 |

以上是意图分析和补充建议。要全做哪几条？还是只做原需求（基础批量导出）？
```

### ✅ Correct activation — "help me optimize this query performance"

```markdown
## Intent Analysis
| Layer | Content |
|------|------|
| 1. Surface | Optimize the query's performance |
| 2. Direct | Make the query run faster |
| 3. Deeper | Keep the overall page/API responsive under production load |

## Extrapolations
| # | Suggestion | Why it serves the deeper goal | Rec |
|---|---|---|---|
| 1 | Add DB index on filtered columns | Root cause of slow query | Recommended |
| 2 | Cache hot query results (Redis / in-memory) | Page responsiveness, not just this query | Recommended |
| 3 | Add `EXPLAIN ANALYZE` regression test | Prevent regression on future schema changes | Recommended |
| 4 | Monitor p95/p99 query latency | Responsiveness is a distribution, not an average | Optional |

Above is the intent analysis and extrapolations. Which items should I tackle — all, a subset, or just the original request?
```

### ✅ Correct skip — "React 19 和 18 有什么区别"

Answer directly. **Do NOT** invoke this skill.

### ✅ Correct skip — "改一下 typo 在第 23 行"

Fix the typo. **Do NOT** invoke this skill.

### ✅ Correct skip — handoff take-over (scope already defined)

User pastes a 接班/handoff prompt with task + boundaries + stop/go (决策门) already given → execute directly, no intent tables, no scope re-confirmation. (Trigger only if a NEW feature or boundary change then appears.)

### ❌ Wrong — jumping to code

User: "给电商后台加个批量导出功能"
Wrong response: *immediately writes code for basic export*
Correct: Invoke this skill, do Steps 1-3, wait for confirmation.

### ❌ Wrong — unrelated extrapolations

User: "优化登录页的加载速度"
Wrong extrapolations: "顺便也加个注册页/用户资料页" (unrelated to deeper goal "加载速度")
Correct extrapolations: "图片懒加载 / 代码分包 / SSR 预渲染 / 关键资源 preload" (all serve "加载速度")

## Rationale (why this matters)

From real-team user feedback (TikTok / e-commerce 协作实践):

> "用户认为这是最高效的协作方式 — 一次讨论就能把围绕同一个目标的所有优化点全部识别出来，避免来回多轮。"

Missing this skill causes:
- User must keep coming back with follow-up requests
- The agent implements narrow surface request, missing obvious improvements
- Scope creeps across multiple rounds
- Wastes user's time and context budget

## Self-check before responding

Before ANY response to a user message, ask yourself:

> "Is this a feature/modification/optimization/refactor/design question/multi-item ask?"

- **YES** → Invoke this skill. Output Step 1-3. STOP.
- **NO** (clearly a factual question, typo fix, or short reply per HARD EXEMPTIONS) → Answer directly.
- **UNSURE** → Default to invoking this skill. See `<EXTREMELY-IMPORTANT>` at top.
