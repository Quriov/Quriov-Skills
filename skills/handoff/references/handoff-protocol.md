# Handoff Protocol — Full Reference

<!-- handoff-skill-rev: 2026-08-06 -->
> This is the **detailed protocol reference** for the `handoff` **skill** ([`../SKILL.md`](../SKILL.md)). It contains rationale, incident backgrounds, examples, edge cases not in the skill's executable procedure.
>
> ⚠ **handoff 已从 command 统一为 skill**(单源,跨 Claude + Codex)。本 doc 现位于 `.claude/skills/handoff/references/`;§ Step 3b cross-layer sync 路径 + See also 相对链接已同步更新到 skill 位置。
>
> **Read this doc when**:
> - Slash command brevity loses essential nuance
> - You need to understand WHY a step exists (rationale / incident history)
> - You're handling an edge case the short version doesn't cover
> - Specifically: Step 3 sub-check details, Step 7 fresh-worktree defense, anti-pattern rationale, stale-branch / SessionStart-hook incident background

---

## Why /handoff exists

User is context-fatigued at end of long session and trusts you to leave clean breadcrumbs for the next CC. Without /handoff protocol enforcement, common failures:
- Next CC starts cold, repeats live verify wrong
- User instinct (verbatim) lost to paraphrase
- Stale branch reuse (stale-branch 误用 incident)
- SessionStart hook ground-truth confusion

---

## Step 0: Live-verify — full rationale

> 3 mandatory commands 见 slash command Step 0 (不在此重复)。本节只补 rationale。

**Why blocking**: Memory self-report has drift (真实案例: memory 里标"完全无人用"的服务, live-verify 一查近 30 天其实还在跑 N 个 job). Live verify gives ground truth.

**Cite output verbatim in your handoff doc § 6 (Live state at close)**. Don't paraphrase.

**⚠ `BLOCKING` 约束的是顺序, 不是粒度** (2026-08-25 澄清): 它的含义是「**先**拿到 ground truth, **再**读 memory / handoff doc / CLAUDE.md」—— 防的是拿 memory 自报当事实。它**不要求**这几条命令一条一条分开跑。

这一点此前从未写明, 导致默认路径是"照编号列表一轮一条", 而每轮都要重读几十万上下文。实测 256 次真实 handoff: 昂贵档比便宜档多跑 3.6 倍轮次、上下文只差 1.1 倍, 且 84% 的 Bash 是彼此独立的只读查询。合并模板与**退出码的两个反向坑**见 SKILL.md Step 0 § 批量模板。

> 🔑 那段刻意写成**可直接抄的模板**而不是一句"建议批量化": 合并的自然写法 (`;` 串联 / 管道) **恰好都会吞掉失败**, 只给建议不给写法 = 把成本问题换成静默假绿问题。抄模板自动做对, 靠记纪律会腐。

---

## Step 1: Verbatim user signals — full rationale

> **6 categories** (拍板/裁决 · Reframe · Push-back · Instinct · Mid-session 补充 · Communication preference) 见 SKILL.md Step 1 (不在此重复)。本节只补 rationale。
> (此前本行写「5 categories」, 漏了 2026-08-06 加的「拍板/裁决」那类 —— 2026-08-21 dogfood 发现并修正。)

**Why verbatim, not paraphrase**: Paraphrasing loses ~40% of nuance (tone, urgency markers, scope qualifiers). 尤其 **Instinct** 类 ("我觉得" / "顺便 X") — 这些是 next CC **can't derive from git log** 的唯一信号源, 丢了就永久丢了。Copy original text + approximate timestamp。

**Why 每条还要标「落点」(诉求对账)**: 提取信号回答的是"用户说过什么", **不回答"这些都做了吗"**。
这两件事之间的落差就是丢球发生的地方 —— 一次交接里用户分散提十几条需求是常态, 全靠执笔者自己记住哪条还没落地。
项目侧 `AGENTS.md` 早有「交付前需求对账(防丢球)」这条铁律, 而 handoff 作为**交付前的最后一道**反而没有, 是 2026-08-21 dogfood 找出的唯一一处"最该防却没设防"。
落点行刻意做成**给已有信号加一行**而非另起一张对账表: 另起的表要人重新想内容, 会空会腐; 落点是从已提取信号机械派生的, 且对账发生在写 §🔴 的当下而不是整篇写完后。
格式与四类硬信号的限制见 SKILL.md Step 1 § 诉求对账 —— 那条「`是约束不是活` 只对 Push-back / Communication preference 开放」的限制**就是整个机制的闸门**, 去掉它判据即恒真。

---

## Step 2: Track identification + draft

### Step 2a: Track identification — full anti-pattern background

**Background — stale-branch 误用 incident**: 一个紧急部署 session 跑 handoff 时, 因为 active-tracks 没列它的 track + branch 名字撞了一个 stale branch (上一个 PR merge 时没带 --delete-branch, 分支残留在 remote), CC 凭"最近 handoff doc 是某条轨道"复制了 track 名, ship 出**完全错的** handoff doc + 重复 PR. **从此强制 4-step protocol**:

1. **Read `<project>/.claude/active-tracks.yaml`** if exists. List all:
   - `tracks[].{id, branch, worktree_path}` (long-term 支线)
   - `ad_hoc_sessions[].{id, worktrees}` (短期任务 schema)

2. **Cross-check** current session: `git branch --show-current` + `pwd` (worktree path) vs each entry:
   - **Exact match** (branch + worktree 都对) → 用该 `id`
   - **No match / 多匹配 / 不确定** → **STOP. Use `AskUserQuestion`** with these 4 options:
     > "本 session: branch `<X>`, worktree `<Y>`. active-tracks.yaml 没匹配的轨道. 这是:
     > (a) 新长期轨道 (加进 `tracks[]` + propose schema 给你)
     > (b) 已有 A/B 轨道的子分支 (告诉我哪条)
     > (c) 临时 ad-hoc 任务 — CC propose 加进 `ad_hoc_sessions[]` (短期任务 schema, NOT orphan; sample entry in active-tracks.yaml)
     > (d) 你 manually 指定 (说轨道 id)"

3. **不准凭推断**:
   - ❌ 不准 copy 最近 handoff doc 的 track 名 (那是别人的 session)
   - ❌ 不准从 branch name 模糊匹配 (`claude/foo-fix` 可能跟同名 spec 完全无关)
   - ❌ 不准基于"这 branch 上有什么改动"推断 track (你可能在 stale branch / 别人的 branch / merged-but-not-deleted branch 上, 改动跟你 task 完全无关)

4. **No active-tracks.yaml** = 单支线项目, track 默认用 'main' 或项目特定 default; 不确定就 ASK user.

### Step 2b: Verify branch ownership — full rationale

防 stale-branch 误用二重 trap (即使 Step 2a correct, branch 本身可能是 stale / 已 merged 但没删).

跑:
- `git log origin/main..HEAD --oneline` — 本 branch 独有 commit
- `git status --porcelain` — 工作区干不干净 (下面分流要用)
- `gh pr list --head <current-branch> --state merged` — 本 branch 的 commit 是否已 squash-merged 但 branch 没删

**三种情形分流** (2026-08-21 宇通拍板改的; 此前三种一律 STOP+ASK):

- **已 squash-merged + 工作区干净** → ✅ **自动开新分支, 不问**:
  `git checkout main && git pull && git checkout -b <new>`, 然后告知一行「起手时站在已合并分支 X 上, 已自动切到 Y」
- **已 squash-merged + 工作区脏** → 🛑 **STOP + ASK**:
  > "本 branch 已 merged, 但工作区有未提交改动 `<list>`。切分支会把它们带走或冲突 —— 这些改动要保留吗?"
- **独有 commit 内容跟本 turn task 不一致** → 🛑 **STOP + ASK**:
  > "我现在 branch `<X>` 有这些 commit `<list>`, 但跟本 turn task 不一致. 是不是我应该开新 branch?"

**Why 第一种可以自动**: 它**答案唯一** —— 在已合并分支上继续 commit 是 anti-pattern #8 明令禁止的, 没有第二个选项可选, 问一次纯消耗用户注意力。后两种答案不唯一 (脏工作区那些改动要不要带走 / 这条分支是不是其实该继续用), 必须人判。

⚠ **放松的是"发现之后要不要问", 不是"要不要查"** —— 本步仍是每次必跑的**步骤**。它 2026-08-20/21 两天内在两条线上各救过一次; 眼镜线原话:「我当时并不觉得自己站在死分支上……**如果它是一句『记得检查一下』而不是一个步骤, 我 100% 会跳过**。」把它降级成提醒 = 这道防线消失。

### Step 2c: Draft handoff doc — format spec

Write to: `<project>/docs/handoffs/YYYY-MM-DD-<track-id>-<type>.md`
(or follow project's existing handoff convention — Read existing files first to match)

**Required sections (in this exact order)**:

1. **🎯 What this CC took over from / handed to**
   (1 paragraph, citing previous handoff path + next track ID if known)
2. **🔴 Verbatim user signals from this turn** (Step 1 output, with timestamps; **每条原话紧跟一行 `→ 落点:`** — 见 SKILL.md Step 1 § 诉求对账)
3. **📋 What shipped this turn** (PR list + commit hashes — keep brief, git log has detail; don't repeat)
4. **⚠ What's still pending / deferred** (with `blockedBy:` if applicable)
5. **🚨 Warnings for the next CC** (specific gotchas you learned this turn)
6. **📌 Live state at close** (cite Step 0 output verbatim, with timestamp)

---

## Step 3: Memory hygiene + index — full sub-check protocol

**6 sub-checks (3a–3f)** —— 与 SKILL.md Step 3 表格逐条对应, 以那张表为准。
Aggregate output as numbered proposal table for user confirm.

> ⚠ **本文档把其中的 3b 拆成三小节展开** (`3b` / `3b-extra` / `3b-extra-2`) —— 它们**合起来 = SKILL.md 表格里的那一条 3b**「Context-file health」, 不是三条独立 sub-check。拆开只是为了分别讲清各自的事故来源, 别按小节数去数 sub-check。
> (此前本行写「8 sub-checks. Run all 8」, 与 SKILL.md 的 6 条对不上 —— 2026-08-21 dogfood 发现并修正。)

### Step 3a: Memory drift scan

- Grep: `grep -rEn "(完全无人|已弃用|已停用|wind down|无流量|stub|未实现)" memory/`
- For each hit, cross-validate against Step 0 live-verify output
- If conflict → **propose memory file update** (don't directly edit, list for user confirm)

### Step 3b: MEMORY.md / CLAUDE.md / AGENTS.md health

- Count lines: `wc -l MEMORY.md CLAUDE.md AGENTS.md` (or Read + count)
- MEMORY.md > 200 lines → propose trim (top ≤ 50 line principle)
- CLAUDE.md + AGENTS.md > 300 lines (若项目有总行数上限约定) → propose trim
- Tier A pointer check: each pointed file exists? (`ls memory/*.md`)
- Tier A pointers still reflect current active tracks?
- Dead links (referenced file doesn't exist) → propose delete reference OR restore file
- **State-pin discipline (state-rot 根治核心, 取代旧 "仅 flag warning" bug)**: grep CLAUDE.md / AGENTS.md for inline state headers (`🟢 Current State` / `🟢 当前状态` / `LIVE 业务功能` / date-stamped `## <年份>-`):
  - ⚠ **canonical state 更新 = 更新 `.claude/active-tracks.yaml` 本 track 的 `last_updated`=今天** (强制动作, 非可选 propose; freshness 闸门验它). active-tracks 只承载**约束层** (worktree/forbidden/shared_invariants); **进度与"下一步"不再写进 active-tracks 叙事** (防它膨胀成叙事垃圾场) — "下一步"进 handoff doc (Step 2c pending), 任务进度进任务板 issue (SKILL §Step 3b-任务板接线 走多信号探测判本仓有没有板; 无板仓退回 handoff doc). (旧协议把 state 更新指向 CLAUDE.md 大段又说"不强制改" → frozen 上百 commit; 后改指 active-tracks 又塞进度叙事 → 膨胀+僵尸条目 — 均已废弃.)
  - CLAUDE.md 应保持**指针** (指 active-tracks + 最新 handoff). 若 grep 到内联易腐 state (HEAD hash / ADR 号 / 最新 turn / feature 清单) > 5 行 → **propose 砍成指针** (别让 state 重新堆积; Anthropic 最佳实践: 高频变的别放 auto-loaded CLAUDE.md).

### Step 3b-extra: 团队 onboarding doc health

若项目有团队共享的 onboarding / 接班总纲文档 (常见如 `docs/AI-CONTEXT.md` / `CONTRIBUTING.md` / `AGENTS.md`):

- Read 它, 是否反映最新 active 轨道 (cross-check `.claude/active-tracks.yaml`)?
- 里面的 pointer 是否全部 file exists? (`ls` 验证, dead link → propose fix)
- iron rules 是否该加新条? (本 turn user verbatim 反复出现的 instinct → propose promote 成 iron rule)

项目没有这类 doc → 整段跳过。

> ℹ️ 旧版这里还有一段 "project ↔ user-level 双份副本手工 `cp` 对齐" 检查 —— 那是本 skill 靠人肉复制分发时代的产物。
> 现在 skill 统一走 `npx skills add/update` 分发, 不再存在需要人工对齐的副本, 该段已删除。

### ⭐ 拍板类信号 — 为什么单列一类, 以及必须回卡

**真实事故 (2026-08-05, 眼镜仓 #2246 / 复盘 #2379)**:

拍板发生在**写 handoff 的现场**。执笔者把 verbatim 原话工整记进了 handoff (还标了 ⭐ 和时间 `0805 18:0x`), 就觉得"记下来了" —— 但**没有回到那张卡上**。后果:

```
卡顶没写 → 下一棒只扫卡顶 + pending, handoff 正文里的拍板对它不可见
        → 再下一棒的个人 memory 把「已拍」记成「仍等宇通拍」(方向反了)
        → 拍板人本人的启动包引用了那份错 memory
        → 又一棒照单复述, 无人起疑
```

**两棒无人接手, 直到拍板人本人真机使用时发现还是旧版才暴露。**

**关键机制判断**: 那不是四道防线失守 —— **它们是同一个源头的四份复制品**, 互相派生。源头一错四份全错, 而且**每多一份, 读的人越确信** (口径一致 → 更不会去质疑)。

**推论**: 再补一份同源的复制品 (模板里加个"我已回卡"自检勾选框) **不解决问题** —— 它仍由"执笔者此刻怎么想"派生, 而他此刻正认为自己已经记下来了。真正能拦住的只有两种东西:
1. **独立信源的机器比对** (handoff 文本 vs issue 卡顶编辑史, 两个互不派生的源) —— 由各仓 CI 侧实现
2. **让拍板在 handoff 里可被机器发现** —— 这是本 skill 能做的那半: 单列成类 + 固定格式 `拍板 · #N · <时间> · <结论>`

⚠ **为什么是"格式化已经在写的东西", 不是"新增一个要记得做的动作"**: 任何"记得多写一行 / 记得勾一下"的设计, 都会在**同一个位置**重新裂开 —— 没想到回卡的人, 同样不会想到写那行标记。而拍板 verbatim 本来就会被写进 handoff (本案就写了), 只是没有格式、没有卡号、没被单列成类, 于是机器发现不了、人也不会被提醒回卡。

**机器侧配套判据 (给实现巡查的人)**: 判"卡顶有没有跟进"用 GraphQL `issue.userContentEdits` 的**最后编辑时间**, **不能用 `issue.updatedAt`** —— 后者会被任何评论/引用刷新, 看着很新其实卡顶几天没动, 属于典型的全绿假阴性。比对基准用**拍板发生时间**而非 handoff 的 commit 时间, 否则复述历史拍板会必然误报。

---

### Step 3b-extra-2: Stale branch hygiene (防 stale-branch 误用重演)

防 orphan branch 累积 → 后续 session checkout 误用 (真实案例: 一个 merge 后没删的 stale branch, 几十分钟后被另一 session 误用).

- Run `git ls-remote origin 'refs/heads/claude/*' | wc -l` (stale claude/* 数量)
- 大于 50 → ⚠ 严重累积, propose batch cleanup script
- 本 turn merged PRs check:
  - `gh pr list --state merged --limit 10 --json number,headRefName,mergedAt --jq '.[] | "\(.number) \(.headRefName)"'`
  - For each: `git ls-remote origin <headRefName>` 存在 → propose `git push origin --delete <headRefName>`
- **Future PR merge 必须用** `gh pr merge --delete-branch --squash` (stale-branch 误用 incident 的二级根因: 某次 PR merge 没带 --delete-branch, branch stale 留在 remote, 几十分钟后被误用)
  - 多 worktree env 撞 `gh pr merge` worktree 冲突时, **绕 API**: 见下方 anti-pattern 清单 "multi-worktree gh pr merge" 那条

### Step 3c: Handoff doc deferred 过期

- Read 最近 3-5 个 `docs/handoffs/*.md`
- For each deferred / pending / blocked item:
  - Done (cite commit hash) → propose archive that handoff or strikethrough item
  - Still valid → keep
  - Superseded → propose archive

### Step 3d: CC 自塞垃圾

Pattern (from local-transcript research):
- `next-step-*.md` / `phase[0-9][a-z]-state.md` — short half-life todo backlogs
- Same claim duplicated across files → propose pick canonical, delete others
- Information-density-low meta-meta docs (>500 lines lessons-learned, only <10% actionable) → propose extract gist + archive original

### Step 3e: External KB read-only verify

If project CLAUDE.md mentions an external KB (Notion / Confluence / wiki / 团队表格 等) as Single Source of Truth:
- **read-only verify** (跑该 KB 的只读查询命令, 项目 CLAUDE.md 里通常有给) — CC 直接跑, 跟 git log 同 class, 不需要 user 决策
- **propose write/sync** (修文档 / 新建 record) — 列给 user confirm, do NOT auto-execute (write 有 side effect)

### Step 3f: Output hygiene proposal to user

Aggregate 3a-3e output as a **numbered proposal list**:

| # | File | Change type | Description | Why |
|---|------|-------------|-------------|-----|
| 1 | memory/reference-X.md | UPDATE | "完全无人用" → "30d 内 N jobs (verified <timestamp>)" | 防 memory drift |
| 2 | memory/next-step-Y.md | ARCHIVE | content done, move to archive/ | reduce noise |
| 3 | MEMORY.md | TRIM | currently 138 lines, propose cut Tier B repo canonical to 80 lines | fit startup context |

**Wait for user to confirm / change / reject each item**, do NOT auto-execute.
After user confirms, CC then Edit/Write/Move files.

⚠ Side-effect warning:
- Step 3 has side effects (delete / move file), MUST user confirm first (Step 3e read-only verify 例外, 可直接跑)
- After running, must `git status --short` to verify changes
- After memory file changes, must update `MEMORY.md` index accordingly

---

## Step 4: New-session init prompt template

Use the template (**按顺序 fallback, 命中即停**):
1. `<project>/.claude/templates/new-session-prompt.md` (preferred — team-shared via git)
2. `~/.claude/templates/new-session-prompt.md` (user-level generic, 自己机器跨项目用)
3. skill 自带 `templates/new-session-prompt.md` (本 skill 目录, 随 skill 分发永远存在 — 纯 Codex / 新装 / 无 `~/.claude` 环境兜底, 保证"找不到模板"不会发生)

Fill these variables:
- `{{track}}`: which active track (from active-tracks.yaml `tracks[]` OR `ad_hoc_sessions[]`, or your judgment)
- `{{type}}`: business-continuation / debug / system-upgrade / handoff-take-over / new-independent
- `{{handoff_doc_path}}`: path to handoff doc you just wrote in Step 2c
- `{{warnings_top3}}`: top 3 items from § 5 of handoff doc

⚠ **关键 — template body 含 `bash` code block (Step 1 Live verify)**.
当 Step 6 output 这个 filled prompt 时, 你**必须用 4 反引号** ```` 外 fence 包整段
(内 3 反引号 bash 块就不会破碎外层 fence). 详 Step 6 format spec.

### 「内化复述」段 — 接班 prompt 必含

**Why exists**: 真实事故 — 接班 session 执行任务很顺, 但整条线设计意图 (信任档位 / "有意延后 vs 真没做" / 哪个 TODO 是北极星杠杆) 没 load 进工作记忆, 被用户追问三次才用 episodic-memory 现挖回来。用户: "我感觉遗漏了很多信息""这太影响了"。**关键反证**: 那次接班 prompt 已经超标塞了设计 spec + 北极星进必读, CC 还是没内化 → 证明「加更多必读」无效, 杠杆在「读后强制输出复述」(被动扫读 → 主动加工)。

**要求**: Step 4 生成的接班 prompt 必含一段, 要求接班 CC **动手前**复述 (写在第一条回复, **不等用户确认不阻塞** — 理解错用户当场打断, 但不加审批 friction):
1. 本条线北极星/目标一句 + 当前阶段/档位
2. **有意延后 vs 真缺口** (设计上故意没做的 ≠ 真 pending — 分不清就是没读懂)
3. 本 turn 任务 + 它在整条线的位置

**Conditional**: 长线 track (有 dossier / 设计 spec) 必做完整复述; 纯执行 ad-hoc 小任务缩成 1-2 句 (目标 + 不在 scope 的)。**上面 3 个模板文件万一都找不到时, 生成的 prompt 也必须自带这段** — 这段的本体要求在本 skill, 不依赖模板文件存在。

---

## Step 5: Self-lint handoff doc — anti-inverse-failure

After writing, grep your own doc for:

- `✅` / "shipped" / "完成" / "ship" / "ready" — each MUST be followed by a file:line citation OR commit hash. If not, change to 🟡 designed / pending.
- "已 verified" / "已 test" — MUST cite a command run + timestamp. If not, change to "声称 verified, 未独立验证".
- Any "我们之前讨论的 X" → replace with verbatim user quote + timestamp.
- **Doc-template lint**: 你写的 handoff doc 必须含全 6 个 required section header (🎯 took over / 🔴 verbatim signals / 📋 shipped / ⚠ pending / 🚨 warnings / 📌 live state). grep 自己的 doc, 缺任一 → 补上再 output. (历史: 出现过几个 handoff doc 缺 verbatim+live-state 章节, 退化成 narrative ship-log.)
- **报喜 scope lint**: doc / 本 turn 输出里出现 "闭环 (完成/跑通)" / "全线完成" / "整条线 (通了)" 类**完成性断言** → 必须紧跟「当前档位 + 有意没做的」清单。**局部完成 (单个 Plan / 一段管道) 禁止写成整线闭环** — 接班丢失整条线设计意图的事故里, 一个局部 Plan 完成被报成 "闭环完成", 直接加重用户 "是不是漏了很多" 的感觉。注意是提示性检查: 描述**目标**的 "闭环" ("目标是让 X 闭环") 不算, 只查**声明已达成**的用法。
- **⭐ 诉求对账 lint (防丢球, 2026-08-21 加)**: §🔴 里每条信号必须有 `→ 落点:` 行。两种伪通过要一并查:
  (1) 拍板 / Reframe / Instinct / Mid-session 补充 四类里标了 `是约束不是活` 的 → 判为漏项, 那四类必须落到 §📋 或 §⚠;
  (2) 标 `已做` 却给不出 PR#/commit — 或核实类标了却给不出**可被下一棒复核**的证据(命令+输出/文件:行/具体结论, 光写"已确认"不算) → 按本节第一条降级 🟡。
  ⚠ 这条 lint 的价值全在(1): 没有它, 每条都标"是约束"就能全身而过。
- **接班 prompt lint**: Step 4 生成的接班 prompt 缺「内化复述」段 → 补 (见 Step 4 §「内化复述」)。

---

## Step 6: Output strict format

User 一眼区分 paste 区 vs review 区 vs 决策区. Output in **exact** this order, with `---` horizontal rule + emoji header between every section. **Critical**: section 2 (new-session prompt) MUST be wrapped in **four-backtick** fence ```` to prevent inner bash code block from breaking layout.

---

### 📄 1. Handoff doc 路径

`<markdown link, e.g. [docs/handoffs/2026-MM-DD-...-ship.md](docs/handoffs/...)>`

---

### 📋 2. 新 session 接班 prompt — paste-ready (整段复制)

> ⚠ 外层 4 反引号 ```` (内层 bash code 3 反引号不破碎)

````
# 接班 prompt — {{track}} 轨道 / {{type}}

<完整 filled-in prompt, 含 inner ```bash ... ``` blocks>
````

---

### 📊 3. Self-lint result

✅ 0 warnings — handoff doc 内每个 ship 类断言都带 commit hash / file:line

OR

⚠ N warnings: `<列具体哪几条 + fix 建议>`

---

### 🛠 4. Hygiene Proposal — 要你 confirm / reject 每一项, 我才动

(若 Step 3 有 propose, paste table 在这)

| # | File | Change type | Description | Why |
|---|------|-------------|-------------|-----|
| 1 | ... | UPDATE | ... | ... |

请告诉我: 全批 / 批 #1+#3 / 全 reject / 改某条

---

### ❓ 5. Uncertainty — 任何 unsure 都问 user

`<list, e.g. "Tier A pointer 死链: X 文件不在, 要 fix vs delete?" 或 "none">`

---

## Step 7: Commit + push hygiene changes (BLOCKING — fresh-worktree defense)

**Why exists**: dogfood 时发现. handoff Step 3 propose 表里 user confirm 后, CC 执行 edit 但 protocol 没强制 commit/PR. 在 Claude Desktop 默认 fresh-worktree 模式下:
- 老 session 结束 → uncommitted 改动卡在 worktree (dead)
- 新 session 起 → fresh worktree, 看不到老 session 的 hygiene 改动 → **改动等于丢**

Step 7 是 fresh-worktree defense, 把 hygiene 改动 push 到 main (经 PR).

### 🔒 前置闸门: handoff-freshness-check (state-rot 机器级防御)

**Why exists**: 曾发现 CLAUDE.md frozen 上百个 commit / 多天没更新, 根因是旧 Step 3b 允许跳过 state 更新 (markdown 协议靠 CC 自觉)。重设计 (CLAUDE.md 降级指针 + active-tracks 成 state SoT + Step 3b 强制) 后, 仍是协议级, 不是机器级。本闸门补上机器级 enforcement (能自动化的不人治) — 把"CC 记得刷 state 吗"从【静默跳过】变成【可见 FAIL】。

**怎么用**: commit 前 (Step 7 procedure step 2 之前), 跑 (repo 脚本优先, 没有则 user-level fallback):
```bash
bash scripts/handoff-freshness-check.sh <本 session track-id> \
  || bash ~/.claude/scripts/handoff-freshness-check.sh <本 session track-id>
```
- exit 0 (PASS) → 本 track `last_updated` 已是今天, 继续 commit
- exit 1 (FAIL) → Step 3b 漏刷了, **回 Step 3b 补** (改 active-tracks 本 track `last_updated`=今天), 再重跑闸门, 别带病 commit
- 把 output 贴给用户 (像 status-claim-linter 留 pass/fail 证据)

**脚本逻辑**: 强检查指定 track `last_updated` == `date +%Y-%m-%d`; track 不存在 → FAIL (id 写错/新 track 忘加); 无 track-id → 弱检查 (任一 track 今天更新过); 无 active-tracks.yaml → PASS (单支线项目 N/A)。

**边界**: handoff session 跨午夜时, 23:59 刷的 last_updated 在 00:01 跑闸门会假 FAIL → 重刷一次即可。user-level fallback 项目无此脚本 → handoff.md 指令 conditional, 自动跳过。

### 🔒 前置闸门 2: 改了本 skill 就 bump rev

**触发条件**: 本 turn 改过本 skill 自身 (`SKILL.md` / `references/` / `templates/`)。普通 feature handoff 不碰这些 → 不触发。

**做什么**: 把 `SKILL.md` 顶部 `handoff-skill-rev: <今天>` 锚点改掉, 再推回本 skill 的源仓。使用者跑 `npx skills update -g` 拉新版, **rev 锚点是他们确认"到底拿到没拿到"的唯一凭据** —— 不 bump = 别人静默停在旧版 (跟 CLAUDE.md frozen 同类失败模式)。

> ℹ️ 旧版这里是一个 "project ↔ user-level 双份副本 byte-diff" 闸门 (handoff-sync-check)。
> 那是本 skill 靠人肉 `cp` 到多处分发时代的产物;现在统一走 `npx skills`, 不再存在需要人工对齐的副本, 该闸门已废弃删除。

**重要**: 闸门只负责让"漏做"变【可见】, 不自动改文件 (有 side-effect 的动作按 Step 7 分类 + 用户 confirm)。

### When Step 7 runs

User confirms Step 6 output Section 4 (Hygiene proposal table) 的若干项 → CC 执行 edit (用 Edit/Write) → CC 立即跑 Step 7. 不是 Step 6 output 一部分, 是 user 选完后的 follow-up.

### Procedure

**1. Classify edits by location**

| Location | What it is | Action |
|---|---|---|
| **Git-tracked** | 项目 `docs/handoffs/*.md` / `CLAUDE.md` / `AGENTS.md` / `.claude/active-tracks.yaml` / project-level `memory/*` (if 项目 git track it) | **Commit + 开 PR** (see step 2) |
| **User-level memory** | `~/.claude/projects/<proj>/memory/*` (per-user, NOT in repo) | 直接 edit, **不 commit** (per-machine local) |
| **User-level config** | `~/.claude/commands/*` / `~/.claude/templates/*` (per-user dotfile) | 直接 edit. 如用户有 git 维护那 dir, user 自己 push |

**2. For git-tracked changes — commit + PR**

```bash
git add <files>
git commit -m "chore(hygiene): /handoff close — <短描述, e.g. memory drift fix + 2 deferred archive>"
git checkout -b claude/handoff-hygiene-<short-id>   # e.g. claude/handoff-hygiene-20260525
git push -u origin <branch>
gh pr create --base main --title "chore(hygiene): /handoff close YYYY-MM-DD — <短描述>" --body "..."
```

PR body 应列:
- Which Step 3 sub-checks 触发 (3a memory drift / 3b health / 3b-extra cross-team / etc.)
- Which files changed + 为什么
- Linked /handoff session (handoff doc path)

### ⚠ 先看本仓有没有「可直推」规则 —— 有则拆开走, 别打包成一个 PR

**为什么**: 有些仓把状态指针类文件 (`active-tracks` / 工作板 / 状态行) 定为**免审可直推 main**, 同时用自动合并机制处理交接文档 PR。这类仓里**打包成一个 PR 反而会卡住** —— 自动合并白名单通常只认交接文档目录, 混进别的文件就判 block。

**真实事故 (2026-08-04 确认, 两次现形)**: 某仓 `AGENTS.md` 协议**强制**「Session 结束更新 active-tracks 自己那行」, 而它的 handoff 自动合并判定器白名单只有 `context/handoffs/` 一条 → **每份合规交接 PR 都含这两个文件 → 一律判 block**, 全靠人肉合 (实测 #2080 于 2026-07-31、#2217 于 2026-08-04, 均由人工 merge)。

> 讽刺之处: 自动合并**只对违反协议的交接 PR 生效** (那些忘了更新 active-tracks 的)。越守协议越被卡。

**注意这不是那个仓的 bug**: 他们判定器里明确写了不把 active-tracks 加进白名单的理由 —— 那是给一个握有 `contents: write` 的机制放宽白名单, 爆炸半径不划算; 他们的正解是**分开走**。缺陷在本 skill: Step 7 无条件把所有 git-tracked 改动打包成一个 PR, 没有「这个文件在本仓本可直推」的概念。

**怎么判**: grep 项目 `AGENTS.md` / `CLAUDE.md` 的直推白名单 (关键词 `Ship` / `直推` / `白名单`), 或看 `.github/workflows/` 有无 handoff 自动合并流及其判定脚本 (白名单通常写在判定脚本里)。

**命中则**:
- 交接文档 → **单独** PR (只含它, 让自动合并能认出来)
- 状态指针文件 (在直推白名单内) → 直接 `git commit && git push` 到 main, 不进 PR

**没命中** (多数仓) → 照常打包一个 PR。

⚠ 别自作主张扩大直推范围: 只有**项目明文列进白名单**的路径才直推; 拿不准就走 PR (走 PR 最坏是多等一次人工合, 直推错了是把没审的东西推进 main)。

---

### ⚠ 开完 PR 必须让它真的进 main (否则交接断链)

**为什么是硬要求**: 新 session 读的是 **main 上**的 handoff 文件。只存在于未合并 PR 分支上的文档, **对接班方等于不存在** —— PR 开了但没合, 交接就是断的。

**真实代价 (2026-07-28 实测)**: 某仓两份交接文档分别在未合并 PR 里躺了 **11 天 / 17 天**, 期间每个接班 session 都读不到。根因: Step 7 停在"开 PR + 报给用户", 把"进 main"这一步交给了人去记 —— 靠自觉的环节默认会失效。

**所以开完 PR 二选一, 不许停在"PR 已开"就报完成**:

1. **项目有自动合并机制** (CI 绿即自动合 handoff 类 PR) → 说明"已开 PR #N, 合并由 CI 自动完成", 并**确认最终真的合了**: `gh pr view <N> --json state,mergeCommit`
2. **没有自动合并** → CI 绿后自己合: `gh pr merge <N> --squash --delete-branch`
   (撞 multi-worktree 冲突用下方 anti-pattern 清单 "multi-worktree gh pr merge" 那条的 API workaround)
   **无权限合** → 显式告诉用户"PR #N **需要你点一下 merge, 否则下个 session 看不到这份交接**" + 列进 Step 6 § Uncertainty

**能自己合的判据** (全满足才合):
- All CI green (判红绿看 **job 级 conclusion**, 别看空的 required 集合)
- 0 human negative review
- 改动 scope 全在 hygiene 范围 (`docs/handoffs/` + `memory/` + state-pin 那一行), **不碰 `src/`**

⚠ **混了团队真相文件就别自作主张**: 同一 PR 里若含 `CLAUDE.md` / `AGENTS.md` / `.claude/**` 的**实质**改动 (不是 handoff 流程要求的 `last_updated` state-pin 那一行), 按项目规矩可能需要人审 → 交给人, 别直推。项目若有 Ship/Show/Ask 之类分档规则, 以项目规则为准。

⚠ **标题带 "handoff" ≠ 就是交接文档**: 判据是**文件清单**, 不是 PR 标题。真实教训: 某仓 3 个标题以 "Handoff:" 开头的 PR, 内容其实是 34 个 TypeScript/Kotlin/Python **源码文件** —— 那些本来就该走完整 PR 审, 任何自动合并机制都必须按**文件路径**判定, 绝不能按标题匹配。

**3. Report back to user**

跑完 Step 7 后给 user 一条 follow-up message:

```
✅ Step 7 完成:
- Git-tracked hygiene changes: PR #<N> opened (<URL>)
  - <files list>
- User-level memory updates: <N> files edited (local, no PR)
- 等 CI 绿 OR 你 review 后 squash merge
```

### Edge cases

- **0 confirmed items** → skip Step 7 (报 "no hygiene changes to commit")
- **全部 confirmed items 在 user-level** → no PR (报 "memory updates done, no PR — per-machine")
- **本 session 有 unrelated uncommitted work** → 必 separate commit (hygiene 单独 commit + 单独 branch + 单独 PR, 不要 mix work changes into hygiene PR or vice versa)
- **多 worktree env 撞 `gh pr merge` worktree 冲突** → 用 API workaround (见下方 anti-pattern 清单 "multi-worktree gh pr merge" 那条)
- **Branch protection 不允许 self-merge** → 报 user "PR # 开了, 待你/team review/merge"

### Anti-pattern (Step 7 specific)

- ❌ **Edit 后 leave uncommitted** — fresh-worktree next session 看不见 = 改动丢. 详下方 anti-pattern 清单 "leave uncommitted" 那条.
- ❌ **把 hygiene + work changes mix 进同 commit/PR** — code review 视角不清, deployment 风险 mix. 必 separate.

---

## Anti-patterns (DO NOT) — full catalog

#### 1. Don't write "this turn we did 5 PRs" verbatim
That's git log content. Handoff should be SIGNAL the next CC can't derive (verbatim user instinct, gotchas, lessons), not noise.

#### 2. Don't paraphrase user instinct
Paraphrasing loses ~40% of nuance (tone, urgency markers, scope qualifiers, hedge words). Copy verbatim.

#### 3. Don't skip Step 0 because "I remember the state"
Memory drift is real (真实案例: stale memory entry vs actual prod state). Always live-verify before claiming state.

#### 4. Don't auto-execute Step 3a-d
Step 3a-d are write-action proposals (delete/move/edit files). Must user confirm. Step 3e read-only verify 例外, 可直接跑.

#### 5. Don't write 长段总结 in handoff doc
Bullet + verbatim quote is the format. Long paragraphs hide signal.

#### 6. Don't break Step 6 strict format
User UX 关键, fence + `---` separator + emoji header 三件套必齐. Specifically: section 2 (paste-ready prompt) MUST use 4-backtick fence (not 3) because inner content has bash code blocks with 3-backtick fence.

#### 7. Don't infer track from branch name / recent handoff / branch commits
stale-branch 误用 incident 的 verbatim 根因. If active-tracks.yaml has no match, **MUST `AskUserQuestion`**. CC NEVER copies track from another session's handoff doc.

#### 8. Don't commit on a stale branch you didn't own
Step 2b verify branch ownership. If your task is unrelated to the branch you happen to be checked out on, `git checkout main && git checkout -b <new-branch>`. If unsure, ASK user.

⚠ **2026-08-21 更新**: 「已 squash-merged **且工作区干净**」这一种改为**自动切新分支 + 告知**, 不再 ASK (答案唯一, 问了纯消耗注意力)。工作区脏、或分支内容与本 turn task 不符, 仍然 ASK。详见 Step 2b 三种情形分流表。**禁止在已合并分支上继续 commit 这条本身没有放松。**

#### 9. Don't merge PR without `--delete-branch` flag
`gh pr merge --squash --delete-branch`. Stale branches 累积是 stale-branch 误用 case 的根因 (几十分钟后另一 session 误用). 见下面 "multi-worktree gh pr merge" 那条 for 多 worktree env workaround.

#### 10. Don't trust SessionStart resume hook summary as ground truth
dogfood 时发现. Hook 显示的 `Project:` / `Branch:` / `Worktree:` 可能是 last-resumed session 的 history snapshot, **不是** 当前 session 的真实 state. 在 cross-session resume 场景 hook 信息 ≠ ground truth. **必先**: `pwd` + `git branch --show-current` + `git rev-parse HEAD` 三命令交叉 verify, 跟 hook summary 对比. mismatch → 信 pwd/git, 不信 hook. 这条防 Step 2a/2b 一开始就被 wrong identity 误导.

#### 11. Don't use `gh pr merge --squash --delete-branch` in multi-worktree env without fallback
dogfood 时发现. `gh pr merge` 在背后尝试 `git checkout main` 本地, 但如果 `main` branch 已被另一 worktree checked out, gh 报 `fatal: 'main' is already used by worktree at <X>` 并失败. **Workaround (CC 直接执行, 不需 user 决策)**:
```bash
gh api -X PUT repos/<owner>/<repo>/pulls/<N>/merge -f merge_method=squash
gh api -X DELETE repos/<owner>/<repo>/git/refs/heads/<branch>
```
两步: (a) API 直接 merge (绕 local checkout), (b) API delete remote branch (replace `--delete-branch` 行为). 等价语义, 跳 gh 本地 git 操作.

#### 12. Don't leave Step 3 hygiene edits uncommitted (fresh-worktree defense)
dogfood 真事 — 用户在 Claude Desktop 默认 fresh-worktree 模式下跑 handoff, Step 3 user confirm 后 CC edit 文件没 commit, 老 session 结束 → 新 session fresh worktree 看不见 → hygiene 改动等于丢. **Step 7 强制 commit + 开 PR + 确保它真的进 main** (见上方 §「开完 PR 必须让它真的进 main」).

**Real cause**: handoff protocol 早期设计假设 session 是 long-running 单 worktree, 自然会 commit. 没考虑 fresh-worktree per-session 模式 (Claude Desktop 默认).

**Fix**: Step 7 procedural 把 git-tracked hygiene 改动 → bundle commit → 新 branch → 开 PR → 确保合入 main (自动合或自己合, 无权限则显式告知用户). User-level memory 例外 (per-machine, 不进 git).

⚠ 不准跳 Step 7 — 跳 = 撞这条 fresh-worktree 丢失。

#### 13. Don't use `git show <ref>:<path> > <user-file>` to sync user-level twins on Windows (用 `cp`)
dogfood 真事 — 跑 Step 3b-extra cross-layer sync 时, CC 当时 worktree 在别的 branch, 想从 main 取最新版同步 user-level twin, 自作聪明改用 `git show origin/main:.claude/commands/handoff.md > ~/.claude/commands/handoff.md` 重定向. **三重坑同时炸**:
1. **Windows shell 把 `origin/main:path` 的冒号当路径分隔符** → `git show` 报 `fatal: ambiguous argument 'origin\main;path'` 失败
2. **`>` 在 git show 跑之前就截断目标文件** → 即使 git show 失败, user-level 文件已被清空 (0 bytes)
3. **就算路径对, PowerShell `Set-Content -NoNewline` / git-show 输出拼接会黏掉所有换行** → 文件变成单行 (内容在但全挤一行, 不可用)

**正确做法 (协议 Step 3b-extra 本来就写的)**: `cp <project-worktree>/.claude/commands/handoff.md ~/.claude/commands/handoff.md` — 直接复制 worktree 里的真实文件字节, 无 ref 解析 / 无 truncate-on-failure / 保留换行. 若 worktree 当前在别的 branch 跟 main 不一致, 先 `git checkout main` (或确认该文件 post-merge 已是想要的版本) 再 cp, 别绕 `git show` 重定向.

⚠ 通用教训: cross-layer sync 永远用 `cp <真实文件> <目标>`, 不要用 `<命令> > <目标>` 重定向 (任何 shell 上 `>` 都先截断目标; Windows 冒号解析 + 换行黏连是额外坑).

#### 14. 接班别只扫"任务背景"就开工; 报喜别把局部完成说成整线闭环

真实事故 (接班丢失整条线设计意图; 复盘结论"不全是 handoff 漏写"):

**现象**: 接班 session 执行某个 Plan 很顺, 但整条线设计意图 (信任档位 / 有意延后 vs 真没做 / 哪个 TODO 是北极星杠杆) 全没 load。被用户连续追问 ("为什么不能自动整理?" "为什么不能 AI 分级?" "感觉缺的东西还是比较多啊") 才用 episodic-memory 现挖。用户: "我感觉遗漏了很多信息""这太影响了"。

**根因三条** (主要在执行者, 其次系统):
1. **(执行者)** 把指向的设计文档当"任务背景"扫了, 没真内化 — 接班 prompt 其实已含 spec + 北极星必读, **"多给文档"防不了"不消化"**。
2. **(执行者)** 把某个局部 Plan 做完报成"闭环完成", 没标"这是最保守档、这几块有意没做" → 过度报喜直接加重用户"是不是漏了很多"的感觉。
3. **(系统)** 设计意图 + 完整 TODO + "有意延后 vs 真缺口" 散在 4+ 文档只用指针串, 没有一份能一次内化的全景。

**Fix (全部已落地)**:
- 接班 prompt 必含「内化复述」段 (Step 4 §内化复述): 动手前复述"北极星 + 档位 + 有意延后 vs 真缺口 + 本 turn 位置", 复述不出 = 没读懂回去重读。
- Step 5 报喜 scope lint: 局部完成禁止写成整线闭环, 完成性断言必须紧跟"有意没做的"清单。
- 长线可建「设计 dossier」单一全景源 (可选模式, 若项目的 `docs/handoffs/HOWTO.md` 有 § 设计 dossier 约定则参照)。**注意: dossier 是可选模式非标准件** — 它还没被接班 session 充分验证过 (dogfood 待验证), 有效后再考虑升标准件。

#### 15. 开不了 PR 的环境 (Codex 沙箱) — 做不了可以, 静默不行

**现象**: Codex 成员在另一项目跑 handoff skill, Step 7 commit + push 到 `codex/*` 分支后**静默跳过"开 PR"** — self-lint 报 "0 warnings", 输出全程没提 PR。用户对比自己本地 CC 的行为才发现差异。

**根因**: Codex 云端沙箱**没有 gh CLI、没有可开 PR 的 GitHub token** — Codex 产品里"Create PR"是平台 UI 按钮 (任务跑完人在界面点)。Step 7 指令写"开 PR"但没写"开不了怎么办" → Codex 撞到做不了的步骤就略过, 没告诉任何人。

**真实风险**: handoff doc 只在 codex/* 分支上、没进 main → 接班 prompt 让下个 session 读它 + `git pull` — **下个 session 从 main 起步根本看不到这文件, 交接断链**。

**Fix (Step 7 Edge cases + Step 5 push-only lint 已加)**: 开不了 PR → push 照做 + **必须显式输出**"无法开 PR + 分支名 + 未进 main 下个 session 看不到 + 请人工在 GitHub/Codex UI 开 PR merge" + 列进 § Uncertainty。**通用原则: 环境能力缺失导致协议某步做不了 = 显式降级 (告诉用户哪步没做成 + 怎么补), 永远不是静默跳过。**

---

## See also

- [`../SKILL.md`](../SKILL.md) — handoff skill 的 executable procedure (short, 调用本 doc 当 reference)
- [`../templates/new-session-prompt.md`](../templates/new-session-prompt.md) — 接班 prompt 模板 (Step 4 用; skill 自带的通用兜底版)
- 项目自己的 `.claude/active-tracks.yaml`(`tracks[]` + `ad_hoc_sessions[]`)与团队 onboarding doc(如 `docs/AI-CONTEXT.md`)—— **有则用、无则跳**

---

## 旁白与成本 — 完整来龙去脉

> 从 `SKILL.md` 的「⚡ 全流程通用: 文字与工具调用放【同一次请求】」移来。
> **正文只留了会改变动作的部分; 这里是它的出处与一次撤除记录。**

### 曾挂在那条建议底下、后被全部撤除的一套成本数据

原文写的是「**22.1 条纯旁白轮 / 中位 104 字 / 占总成本 26%**」。**那套数据是错的, 2026-08-25 全部撤除。**

**错在哪**: 统计者按 transcript 的**行**数轮次, 而**一次请求会被拆成多行** ——
`thinking` / `text` / `tool_use` 各占一行, **共享同一个 `requestId` 和同一份 `usage`**。
⇒ 一个"先写文字、再调工具"的**完全正常**的请求, 被数成了「一条纯文字轮 + 一条工具轮」;
成本也被按行重复累加(同一份 usage 算了 N 遍)。

**两次独立实测**(同一份真实 transcript, 复算只用了两条命令):

| | 按行数 | 按 `requestId` 去重 | 差 |
|---|---|---|---|
| assistant 条目 | 227 | **87** | 2.61x |
| 零工具的「纯文字轮」 | 134 | **9** | **14.9x** |
| cache_read 累加 | 58.5M | **23.3M** | 2.52x |

而那 9 条真·纯文字请求的 output 都在 **1200–4500 tokens**(回答用户提问 / 阶段汇报 / 最终交付),
**根本不是"中位 104 字的短旁白"** ⇒ **那个现象不存在。**
全量重算后方向甚至是**反的**: 昂贵档的零工具文字请求占比**更低**(10% vs 便宜档 14%)。

🔑 **由此提炼的那条规矩已升进 `SKILL.md` 的「没有坏消息不是证据」一节**:
**拿别人的统计结论去改共享规则之前, 先要一条你能自己复算的原始口径。**

### 可行性的活体样本(以及它的边界)

加那条建议的那次 dogfood handoff **全程零条纯旁白轮**, 流程完整、用户全程跟得上。
⚠ **但那次执笔者正在做 dogfood(本来就在赶)且刚处理过这个话题(有意识)** ——
**不知情的执笔者默认还是会往旁白那边走**, 所以那条必须明写在 `SKILL.md` 正文里, 不能只留在这里。

### grep 全文的核实结果(支持"从没要求每步旁白")

4 处「要出声 / 说一句 / 告知一行」**全是特定条件触发**(skill 更新了 / 自动切了分支 / 没检测到任务板);
唯一沾边的 `Walk through these 7 steps in order` 说的是**顺序不是汇报**。


## 投递地址的两条过期路径(2026-08-29 实测)

SKILL.md 的 Step 2c 只留了动作(「那一列记线名, 地址现查」)。这里是它的完整依据。

### 样本

| 线 | 上一棒交接单写的 | 接班开局现查 | 换棒了吗 |
|---|---|---|---|
| cc控制 v1.5 | `…7f6553-20` | `…7f6553-12` | **没有**(标题一字未变) |
| 设计系统 v2.4 | `…1101ff-39` | `…1101ff-c6` | **没有**(标题一字未变) |
| 小艾记忆 v2.1→v2.2 | `xiaoai-memory-v2-0-928166-27` | `ezio-memory-framework-analysis-c0e87b-a4` | **换了**, 且**整条线搬了工作目录** ⇒ 连前缀都没了 |

前两行**证伪了「地址只在换棒时失效」** —— 而那正是"把地址写进交接单"这个做法的隐含假设。
第三行说明**换棒时前缀也会变**, 所以「前缀是稳的」只在同一棒之内成立。

⚠ **成因未确证**。接班当时的推断是「重启轮换」(依据: `ListAgents` 里 6 条 peer 全显示 started 3-5m ago),
但那是**相关不是因果**。报回这条的线**刻意没把成因写进自己的正本**, 原话:
> **原因未确证, 但不必知道原因 —— 写法上避开比查清成因便宜得多。**

⭐ 这条本身就是本 skill 那一族(「输出没骗你, 是你手上那条规矩骗了你」)的又一例 ——
只不过这次那条规矩是**接班自己十分钟前刚写下的**。

### 真实后果: 一次误投

同日, 一条线按上一棒交接单里那张「协作方 → 投递地址」表发消息, **发到了另一条线**
(它要找 A 线, 消息进了 B 线; 内容是请对方去动一条**不属于它**的分支)。

那张表顶上写着「⚠ 投递地址与线名交叉错位, **一律按本表原文用**」——
⭐ **那句提醒是对的, 但它保护的是错的东西**: 它防的是「别按线名猜」, **没防「表本身会过期」**。

### 为什么"目录名不携带线身份"要单独写

同一台机器上的三个反例:
- 设计系统 v2.4 的工作目录叫 `smart-glasses-control-v5-1101ff` —— 看着像总控 v5, 而总控 v5.5 在 `smart-glasses-control-v5-5-ae58b1`;
- ⭐⭐ **同一个工作目录会在【不同的线】之间转手, 所以一份【当时正确】的记录也会变成误导**:
  目录 `ezio-memory-framework-analysis-…` 的分支历史(`git reflog` 实证)是
  `ezio-memory-framework-analysis-…` → **`smart-glasses-ios-v4-2-…`**(iOS 线)→ **`xiaoai-memory-v2-2-…`**(记忆线)。
  ⚠ **本节初版把它写成「上一棒记错了」—— 那是错的, 已订正**: 上一棒写下它时它**确实**是 iOS 线的。
  🔑 **所以问题不是"有人记错了", 而是「记对了也会过期」, 而且过期的方向是【看起来仍然合理】** ——
  你看到 `ezio-memory` 会以为那是记忆线, 而它当时是 iOS 线。**这比"名字不携带身份"更能挡住人的直觉。**
- 总控 v5.4 的地址前缀是 `ios-v37-handoff-0a5b55`。

🔑 **目录名是"某一棒建目录时的快照", 而线一直在换棒。它既不能告诉你"这是谁", 也不能告诉你"它在干嘛"。**
唯一权威是 `list_sessions` 的 `title`。


## 「没有坏消息」不是证据 —— 完整实测与出处

SKILL.md 同名节只留动作(规则 / 判别式 / 各条 🔑)。下面是被移出来的实测、规模数字与出处。
判据是「把这段删掉, 执行者会不会做出**不同的动作**」—— 不会的, 都在这里。

📌 实测规模(**收敛后的稳定值**, 两条线各自独立测、一字不差): 某仓 **44 个 open PR 里 22 个正在冲突**,
而它们的检查全都显示"全绿"。

> ```
> 已合并的 PR   连查 3–4 次 → state=MERGED  可合并状态=UNKNOWN   ← 永远不变
>   换 REST 路径交叉验证    → merged=true   mergeable=null       ← 同结论
> 还开着的 PR   →  会收敛到 MERGEABLE/CLEAN                      ← 只有这种收敛
> ```

> ⭐⭐ **这条最该记的是它的形状, 它是本 skill 这一族里最干净的标本**:
> **一个字段返回了一个【合法值】, 而那个值在当前条件下【根本没有定义】。**
> 不是 null、不是报错 —— 是枚举里一个正常的值。

> 📌 **同一晚三条线各自报回一个"量错了", 成因全不同, 而三个输出都是合法值、都不报错**:
> | 表现 | 成因 |
> |---|---|
> | 「45% 的 PR 在冲突」 | **分母**被查询上限悄悄截断 |
> | 「201 个 PR」 | **计数单位**错了 —— 数的是文件不是 PR |
> | 「重查到归零」 | **成因没穷举** —— 漏了「已合并 ⇒ 永久未知」 |
> 🔑 **三个都是「量的不是我以为的那件事」。**
> ⚠ 报第三条的人自陈: 它合并前两次都看到"未知"、读成"懒计算"就合了 ——
> **结论侥幸没错, 但它用的判据是错的。**

> ⛔ **这里刻意不给百分比 —— 而"为什么不给"比那个数值钱。**
> 本节初稿写过一个率, **两条线随后各自撤回了自己给出的率**(一条分母被查询的 `--limit` 悄悄截断;
> 另一条在**指出前者数字有问题的同一条消息里**犯了同样的分母错)。
> 更要命的是: **同一条命令连查两次, 一次得到那个率、一次得到 0** —— 它取决于服务端缓存热不热,
> 而**几次查询之后就再也测不到冷缓存的首次行为了**。

> 本节要支撑的是「**别信第一次**」—— **那句话不需要任何百分比。**
> (上面保留的那个绝对数则相反: 它**收敛后稳定、不依赖缓存热度、且被两个独立视角测出同一结果**。)

> ⚠⚠ **这次是怎么被抓住的, 值得单独记**: 不是任何闸, 是**另一条线问了一句「你分母是什么」**。

> 📌 涉事的四条线里**没有一条是"更仔细"的** —— **每个人都是在自己最用心的那一段里犯的错。**

📌 实测(报回者自己推翻自己, 2026-08-28): 它把「用户说很多线发现不了、干等着」和
「实测冲突 PR 的检查全是终态」讲成了同一件事。全量扫完:**24 个冲突 PR 全部终态、pending 为 0**
⇒ **全终态的话轮询会判"跑完了"往下走, 根本不会等** —— **两个现象都真, 那条因果链是缝的。**

⚠ 顺带一条它主动要求标的边界: **24/24 证的是"机制会这么呈现", 不是"有人真的被骗过"** ——

📌 两个互为镜像的实测:
· 被测对象在**本地**, 而测量路径依赖**远端** —— 远端故障期间数出来的数本身不稳;
· 被测对象在**远端**, 而测量路径依赖**本地状态** —— 本地缺一个引用, 就伪装成"远端没有"
  (实测: 浅克隆不建远程跟踪引用 ⇒ 读远程文件报"空" ⇒ 差点判定推送失败去重推)。
⇒ **两次的解法是同一条: 让测量路径和被测对象解耦。** 上面那次最后是换成一条**服务器侧**的读法才确认的。

📌 实测: 本 skill 曾据一套统计改过**两版**, 而那套数的是 transcript 的**行**、不是请求
(一次请求会被拆成多行、共享同一份用量) ⇒ 关键指标虚高 **14.9 倍**, 那个"现象"根本不存在。
**复算只用了两条命令, 而它推翻了两版改动。**

🔑 **与「提醒必腐、依赖不腐」是一对**: 那条讲**机制会不会被执行**;
这条讲**执行了的机制说的话算不算数**。

> ⚠ **写在这里而不是写在某一步里, 是有理由的**: 📌 实测两次同形状事故, 成因都是
> **「那段当时只写在 Step N 的语境里, 作用域被读窄了」** —— 一次是 Step 0 → Step 4b 探测,
> 一次是 Step 0 → Step 7 推送 —— **后者那一刻交接文档没能进 main, 而 push 打印的是 ✅**。
> (⚠ 时态要说准: 它**最终进去了**, 靠的是执笔者自己多跑的一句回读。**这是一次"差点", 不是一个还开着的窟窿**
> —— 但下一个人不会多跑那一句。**报「某某坏了」要连带报「后来修没修好」**, 否则读的人会去查一个不存在的窟窿。)
> **写在顶上、并在各步就近重申**, 比只写一遍再声明"适用于全流程"有效。


## Step 7 的完整实测与出处

SKILL.md 的 Step 7 只留动作(怎么判 / 怎么拆 / 必须回读 / 两条硬判据)。下面是被移出来的实测与出处。

> 📌 实测: 一棒因为本节没写"怎么拆", 自己选了 `git stash push -- <单个文件>` ——
> **它照本机规矩小心地做对了, 但那是本节把一个需要小心的动作留成了空白。**
>
> 📌 实测: 一次推送打印 `remote rejected … reference already exists` + 退出码 1,
> **而远端分支就停在刚才那个 commit 上 —— 推送本身成功了, 失败的是随后建 upstream 跟踪的那一步。**
> 📌 **实测事故 (2026-08-28, 报回者当场被咬两次)**: 它写的是
> `git push -q origin HEAD:main 2>&1 | grep -v "^remote:" | tail -1 && echo "✅ 已直推 main"`
> —— `&&` 挂在**管道**后面 ⇒ 拿到的是 `tail` 的退出码 ⇒ **push 明明失败却打印了 ✅**。
> 第二次 rebase 之后 sha 全变、推的还是旧 sha, **又失败一次**。**两次失败都不会自己冒出来。**
> ⭐ **救它的不是本 skill, 是它自己多跑的那一句回读** —— 而**下一个人不会多跑那一句**, 所以写进这里。
> ⚠ 它自己的定性比事故本身值钱: 「本 skill **已有**那张退出码表、也写了『适用于全流程』,
> **问题是它长在 Step 0 里** —— 我在 Step 7 写那行时完全没把它调出来。」
> ⇒ **这就是为什么这条要长在直推路径旁边, 而不是靠上面那张表覆盖。**
> 📌 **六例, 四条线, 同一天**(每一例的救援都来自「**去读输出文字**」, 没有一例是靠退出码):
> · `A && reset --hard && B && push` —— **B 参数写错退出而 push 照跑** ⇒ 改动被推没, PR 因 diff 变空被自动关闭
> · 同一条命令里推送失败, 紧接的建 PR 步骤照跑 ⇒ **建出一个装着别的内容的 PR**
> · `push … | … && echo ✅` ⇒ **push 失败却打印 ✅**(见上)
> · `grep … | head -3` 取到 `head` 的退出码 ⇒ **「没找到」被读成「找到了」**
> · `lint … | tail -30 ; echo "exit=$?"` ⇒ **打印 exit=0 而 lint 实际 FAIL**
>   (⚠ 这一例的执行者当时**正在验"这份产物合不合规"** —— **用一个会说谎的判据去验一个判据**)
> · 后台测试命令包了 `| tail` ⇒ 退出码 0, **而里面有一条真的红**, 差点当成全绿
>
> 📌 真实事故: 某仓协议**强制**同轮更新 `active-tracks.md`, 而它的 handoff 自动合并白名单只认 `context/handoffs/` → **每份合规交接 PR 都被判 block**, 全靠人手动合 (实测 #2080 / #2217)。根因就是本 skill 无条件打包、没有"这个文件本可直推"的概念。


## Step 5 的完整实测与出处

SKILL.md 的 Step 5 只留动作与判据。下面是被移出来的实测与出处。

  > 📌 **实测 (2026-08-28, 复验本条时当场发现)**: A 的三条写完后紧跟着 B 那行, 版面上读起来像"三条通用" ——
  > 而复验者一套就把发出方向从 **2 打成 0**。
  > ⭐ **它是本条正在修的那个 bug 的镜像: 同样一条闸, 同样安静地数出 0, 同样"找到了、数了、得到 0"
  > —— 而这次它出现在【修复本身】里。**
  ⭐ **形状参照**(一条真在生产上跑的闸): 它**只验「声明存在且合法」, 不验「声明是真的」** ——
  因为一旦要验真实性就得从 diff 反推语义, 那条路走不通。
  **它的价值不因此打折, 恰恰因为它诚实地写明了自己不保证什么。**
  ⚠ **为什么必须拆开** (2026-08-28 报回者的话, 值得原样留着):
  > **一条"看起来像 lint"的提醒, 比一条老实的提醒更危险** —— 人会信任闸门。它绿了, 读的人就以为
  > 「查过了」, 而它其实什么都没查。
  > 🔑 **为什么这条非加不可**(报回者原话, 原样留着):
  > 「我甚至**跑了 Step 5(自查), 但 Step 5 检查的是文档内容, 不检查「步骤有没有跑完」** ——
  > 我在一个『已经做了自查、而自查通过了』的状态下停手, **主观上完全像跑完了**。」
  > ⇒ 一般式(本 skill 反复在治的那条): **这个检查在「没跑完」的时候, 会不会给出和「跑完了」一样的输出?**
  > 加这条之前, Step 5 的答案是**会**。
  > ⚠ 报回者还补了一句事实: **「我是被用户问出来的, 不是被 skill 问出来的。」**
  📌 **实测(2026-08-29, 就发生在写下产物表的那一棒身上)**: 它的 §📋 写着
  「本仓: **无代码改动**; 本文件 + `_inbox/`(**9 份**)」, 而同一个 PR 实际动了 **12 个文件** ——
  `.claude/active-tracks.yaml`(**一个字都没提**)+ 交接文档 + **10 份** inbox。**而 Step 5 当时是通过的。**
  ⭐⭐ **最值得记的是第 10 份是哪一份**: 正是那份**最后 26 行被 squash 竞态孤儿化**的文件
  (见 Step 4c 第 4 条判据)。**「数错了」和「内容丢了」不是两件事, 是同一个盲区的两个出口** ——
  **那一棒对自己最后几个动作失去了跟踪。** 这一条对账**同时**抓得到它们。


## Step 0.6 的完整实测与出处

SKILL.md 的 Step 0.6 只留动作与判据。下面是被移出来的实测叙述。

🚨 **这一步治的是一个会真的丢信息的故障** (2026-08-25 实测, 就发生在写这条的那一棒身上):
交接文档写完、PR 已合**之后**, 协作方又发来两批消息, 执笔者**顺手全接了** —— 改了 **4 个版本**的 skill、
关掉一张卡、撤销一整套已分发的错数据。**这些一个字都没进那份交接文档。**
下一棒读到的是"skill 现状 X", 而真实已经是 X+4, 中间四版的判断过程它完全看不到。
⇒ **问题不是文档少写了一行, 是「交接状态下还在接活」。**

📌 **实测 (2026-08-28)**: 同一件事, 一边记「未闭合」、另一边记「已闭合」。翻原文才发现:
那边闭的是「**我提的判据被采纳并分发了**」, 而这边等的是「**那个实现被验过了**」——
**两件事, 一列格子。** 而它俩之间隔着的正是本 skill 反复在治的那条:
**一道闸从没触发过, 和它写对了, 输出一模一样。**
⇒ 「提案被采纳」和「实现被验过」**天然会分开发生**, 清单必须能分开记。

📌 **实测 (同日, 上一条的同一位当事人)**: 清单里那条未闭合项只留了一行结论
(「请它验某两条判据的假阳假阴」), **没留原文** ⇒ 球交下来了, **而接得住球的信息没交下来**。
接班的原话: 「**那条内容不在我的上下文里……我这边确实读不到。**」
⇒ 一行结论足够让接班**知道有这件事**, 不足够让它**做这件事**。
🔑 判据: **把这一行给一个没参与过的人看, 他能不能直接开工?** 不能 ⇒ 原文没带够。

📌 **实测 (2026-08-28)**: 一棒按记忆里的 id 给某条线发交接通知, **直接被拒 —— 那条已归档**。
现查才发现: **三天里它换了 6 棒**(v4.7 → v5.3), 另一条协作方也换了一棒(v1.5 → v1.6)。
⇒ **跨天 session 里, 记忆里的协作方标识几乎必然全部作废。**

📌 **实测代价 (2026-08-28)**: 一棒把自己的地址发给 **4 条**协作方做回信地址, **给的是另一个通道的**
⇒ 4 条全部回不来。**第一条协作方 12 分钟内报回**, 其余 3 条当场补正, 零损失。
⚠ 更难看的是: **那棒在同一条消息里刚警告过对方「别用系统自带的 from 值回」** —— 它给出的是同一种错误。
⚠ 而**上一棒犯的是同一个** ⇒ **两个维护者、两轮、同一形态。**

📌 **实测(2026-08-29, 同日真实发生)**: 一条线按上一棒交接单里那张地址表发消息, 请收件人去处理一条
**不属于它**的 PR —— 而收件人是另一条线。**因为首段写了这两句, 收件人当场退回、零损失**;
发信方随后拿到正确地址、重发成功。
⚠ **发信方自陈「这次做对了是运气」** —— 它只是因为拿不准才写的。
⇒ **所以它该是模板里的固定一段, 而不是靠人当时恰好紧张。**
