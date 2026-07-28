# Handoff Protocol — Full Reference

<!-- handoff-skill-rev: 2026-07-28 -->
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

---

## Step 1: Verbatim user signals — full rationale

> 5 categories (Reframe / Push-back / Instinct / Mid-session 补充 / Communication preference) 见 slash command Step 1 (不在此重复)。本节只补 rationale。

**Why verbatim, not paraphrase**: Paraphrasing loses ~40% of nuance (tone, urgency markers, scope qualifiers). 尤其 **Instinct** 类 ("我觉得" / "顺便 X") — 这些是 next CC **can't derive from git log** 的唯一信号源, 丢了就永久丢了。Copy original text + approximate timestamp。

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
- `gh pr list --head <current-branch> --state merged` — 本 branch 的 commit 是否已 squash-merged 但 branch 没删

**If**:
- 本 branch 独有 commit 内容**跟你本 turn task 不一致** → 你可能误用了 stale branch, **STOP + ASK user**:
  > "我现在 branch `<X>` 有这些 commit `<list>`, 但跟本 turn task 不一致. 是不是我应该开新 branch?"
- 本 branch 已 squash merged (`gh pr list` 返非空) → **STOP + ASK user**:
  > "本 branch 已经 squash merged 进 main, 你确定要在它上面继续 commit 吗? 一般应该 `git checkout main && git checkout -b <new-branch>`"

### Step 2c: Draft handoff doc — format spec

Write to: `<project>/docs/handoffs/YYYY-MM-DD-<track-id>-<type>.md`
(or follow project's existing handoff convention — Read existing files first to match)

**Required sections (in this exact order)**:

1. **🎯 What this CC took over from / handed to**
   (1 paragraph, citing previous handoff path + next track ID if known)
2. **🔴 Verbatim user signals from this turn** (Step 1 output, with timestamps)
3. **📋 What shipped this turn** (PR list + commit hashes — keep brief, git log has detail; don't repeat)
4. **⚠ What's still pending / deferred** (with `blockedBy:` if applicable)
5. **🚨 Warnings for the next CC** (specific gotchas you learned this turn)
6. **📌 Live state at close** (cite Step 0 output verbatim, with timestamp)

---

## Step 3: Memory hygiene + index — full sub-check protocol

8 sub-checks. Run all 8. Aggregate output as numbered proposal table for user confirm.

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
