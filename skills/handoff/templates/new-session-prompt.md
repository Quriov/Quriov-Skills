---
title: New Session Initialization Prompt v2 — Template (skill-bundled generic default)
purpose: Drafted by /handoff for next CC. Designed for max focus, min noise. 本文件是 skill 自带的【通用兜底默认】, 随 skill 分发, 永远存在 — 当项目级 `<project>/.claude/templates/` 与用户级 `~/.claude/templates/` 都没有时由 Step 4 命中。项目想定制就放项目级那份覆盖它。
variables:
  - "{{track}}": 接班轨道 (A / B / 独立任务 / 单支线项目-跳过)
  - "{{type}}": business-continuation / debug / system-upgrade / handoff-take-over / new-independent
  - "{{handoff_doc_path}}": 主交接文档路径
  - "{{warnings_top3}}": 本 turn 学到的 top 3 警告
  - "{{worktree_reclaim}}": Step 4c 算出的前任 worktree 回收段 (无结论时整节删掉)
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

### 0. 开局回访 (交接文档里有 §🤝 协作方清单时才做; 没有则整段跳过)

⚠ **在动手做事之前**。照 §🤝 里标【未闭合】的那几条, 各发一句:

> 「我已接班 {{session_title}}, 上一棒已交接完。之前发给它、没收到回应的, 请重发给我。」

- ⭐ **先确认那条还没闭合, 再去接** —— 你写"未闭合"到接班读到它之间, 它可能已经办完了
  (实测: 一小时内两条线各来问一件早已闭合的事)。**一句话的成本, 省掉重做一件已完成的事。**
- ⚠ **发之前先确认对方还在、现在叫什么**: 清单记的是【上一棒交接那一刻】的标识, 而协作方自己也在换棒。
  ⛔ **别按线名匹配**(线名多半不是投递地址); ⛔⛔ **也别按【工作目录名】认线** ——
  目录名携带的是**上一个住户**的身份, 而那多半是另一条真实存在、此刻还活着的线
  (实证 2026-09-03: 有线照此发 cc控制、发到了 CI —— **它读过规则、记得规则, 规则本身把它送错了**)。
  ✅ **地址现查, 只走这一条**: `list_sessions` 按标题找到线 → 取它的 `sessionId`(`local_…`)
  → `ccd send_message` 直接发。**消息第一行写收件人** —— 发错时收信那条当轮就会说"这不是给我的"。
  ⭐ 理由是**【地址形式】不是工具好坏**: 传 sessionId 时回执自带收件方标题(发错当场暴露);
  传工作目录名时回执只有 `(another Claude session)`。
- **已闭合的不用发** —— 清单留着是给你以后找人用的, 不是让你挨个打招呼。

如果起 Plan Mode, 走项目的 Plan Mode 模板 (如有, 含 § Audit Existing 决策表)。

---

### 7. 前任 worktree (Step 4c 有结论时才写; 没有则整段跳过)

{{worktree_reclaim}}

> ⚠ **这一段是 Step 4c 的产物, 而它以前不在本模板里** —— 于是它能不能出现在启动包里,
> 全看执笔者**记不记得手工加**(提醒, 必腐)。加这个槽位就是为了让它变成**依赖**。
> ⛔ **Step 4c 判定"不可回收"时, 别把这一段留空** —— 按 Step 4c 写成如实说明
> (例:`⚠ 前任 worktree <路径> 有未提交改动, 先别删`)。**空着和"没有前任 worktree"长得一样。**
>
> **可回收时, `{{worktree_reclaim}}` 至少要展开成这四样(一样都不能省)**:
> ```
> ♻️ 绝对路径 + 分支
> 🛑 第 0 步:pwd 自查 —— 这是不是【我自己】的工作目录
>    ⚠ 它只挡「我的 cwd」, 挡不住「别人的 cwd」—— 那是下一步的事
> 🛑 第 0.5 步:有没有【别人】住在里面(⚠ 在该目录【之外】跑, 否则这检查会自己制造占用)
>    首选:反查有没有 session 的 cwd 落在该路径下 —— 它告诉你【是谁】
>    退路:lsof +D "<路径>"
>    ⛔ 别用 pgrep -f —— 它必然返回 0, 而那个 0 和「真的没人」长得一模一样
> 两步都过了才 git worktree remove(不加 --force)
> ```
> ⚠ **这几行写在这里, 是因为【纯 fallback 环境】(新装 / 没有项目级和用户级模板)
> 除了本文件没有别的依靠** —— 而上面那句 ⛔ 只说了"别留空", **没说非空长什么样**。
> **禁令给了、写法没给, 正是本 skill 反复在治的那一类。**

## 沟通规则 (cross-cutting)

- **用中文跟用户沟通** (除非用户切英文)
- **不要用代号** ("Phase X / Wave Y / G3") → 直接讲清楚事情
- **不要 claim "完成" / ✅** 除非带 file:line 或 commit hash evidence
- **memory 自报 ≠ ground truth** → 不确定就跑命令 verify

## 📒 开棒第一天就把【账本】建起来 —— ⛔ 不是收尾才写

在 `<本项目 handoff 文档所在目录>/<YYYY-MM-DD>-<线名 slug>-ledger.md` 建一份, **今天就建**, 然后全程追加。

它装三类**状态板装不下**的东西:
- **🔴 用户的原话拍板**(逐字, 带日期) —— 只追加, 不改写
- **🚨 警告 / 已判定不该做的**(每条带判据)
- **🧠 被否掉的选项与为什么否**(⭐ 一行一条结论, ⛔ 不是过程复述)

**两个挂点, 都是每轮必经的动作, 别靠"记得写"**:
1. **从板上删掉一条**时 → 那是「曾经成立、现在不成立」产生的那一刻
2. ⭐ **写下「我们做 A」那张卡的同一动作** → 你刚否掉了 B 和 C, 而**板上只会出现 A**

**入账与汰换用同一条判据(双向)**:**下一棒重新遇到同一个问题, 会不会走弯路?** 会 ⇒ 留;不会 ⇒ 别记 / 清掉。
⚠ 账本**必须汰换, 不是只增不减** —— 它会进下一棒的必读清单, 越长开局越贵。**结账(收尾)那一刻逐条过一遍。**

🔑 **为什么必须开棒就建**:交接文档是**收尾时**才写的 ⇒ 中途根本没有可追加的对象。
实测:一次收尾里原话 / 警告 / 被否选项 **29 项全靠回忆重写**, 而能从板上抄的只有 6 项 ——
**那 29 项正是从没上过板的那批。**
