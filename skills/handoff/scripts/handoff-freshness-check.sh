#!/usr/bin/env bash
# handoff-freshness-check.sh — /handoff Step 7 自检闸门
#
# 防 state-rot: 验证本次 /handoff 真的刷新了「本仓的 state SoT」。
# 把「CC 记得更新 state 吗」从【静默跳过】变成【可见结果】。
#
# 背景: 2026-05-29 发现 CLAUDE.md frozen 145 commit / 5 天没更新, 根因是旧协议
# 允许跳过 state 更新。本脚本是机器级 enforcement。
#
# ⚠ 2026-08-20 改: 原版**写死** .claude/active-tracks.yaml 一条路径, 且文件不存在时
# 印 ✅「单支线项目」——在一个有 45 条工作线、但用 markdown 工作板的仓里, 它把
# 「我不认识这个仓的格式」印成了「查过了没问题」, 上线起一直空转没人知道。
# 这跟本 skill 任务板那段治过的是同一个病(写死单路径 + 静默跳过), 只是当时只补了一半。
# 现在: 多信号探测 + 找不到也要出声 + 不写死任何仓的目录结构。
#
# Usage:
#   bash handoff-freshness-check.sh <track-id>   # 强检查
#   bash handoff-freshness-check.sh              # 弱检查
#
# Exit: 0 = PASS 或 N/A(不阻塞) · 1 = FAIL(state 未刷新) · 2 = 用法/环境错

set -uo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
  echo "❌ handoff-freshness: 不在 git repo 内, 无法检查" >&2
  exit 2
}
TODAY="$(date +%Y-%m-%d)"
TRACK_ID="${1:-}"

# ── 按序探测本仓的 state SoT (命中即停) ──
# ⚠ 顺序有讲究: **项目自己的声明排第一** —— 它是最高置信度信号, 且是唯一能表达
#   「我这个仓的 SoT 不在常见路径上」的方式。2026-08-20 踩过: 本探测原来把声明放在
#   最后的 else 分支, 只要有任一常见路径存在就永远轮不到 —— 于是某仓把线级 state 搬进
#   context/worklines/ 之后, 闸门仍去查那份**已经退化成目录**的 active-tracks.md
#   (那文件自己第一行就写着「这是目录,不是状态板」), 给假红。
#   (同 skill 的任务板探测本来就是声明优先; 这里是补回一致。)
SOT=""; KIND=""
# ① 项目声明 —— ⚠ 必须是【显式标记】, 不是"正文里提到过这个路径"
#    实测教训: 最初版本 grep"任何 context/xxx 路径提及"就当声明, 结果某仓 AGENTS.md 正文
#    散提了 6 次 context/active-tracks.md(都是叙述, 不是声明), 第一个存在的就被选中 ——
#    拿弱信号当强信号的代理, 跟本 skill 一路在治的是同一个错。现在要求同一行里出现
#    显式标记词 + 路径, 才算这个仓"主动指认"了自己的 state SoT。
#    声明写法(项目侧一行即可): > 本仓 state SoT = `context/worklines/`
for decl in "$ROOT/CLAUDE.md" "$ROOT/AGENTS.md"; do
  [[ -f "$decl" ]] || continue
  cand=$(grep -iE '(state[ _-]?sot|状态单源|工作板正本|state 单源)' "$decl" 2>/dev/null \
         | grep -oE '(context|docs|\.claude)/[A-Za-z0-9_/.-]*' \
         | sed 's#[.,;:)`]*$##' \
         | while read -r c; do [[ -e "$ROOT/$c" ]] && { echo "$c"; break; }; done)
  if [[ -n "$cand" ]]; then
    SOT="$ROOT/$cand"; KIND=$([[ -d "$ROOT/$cand" ]] && echo dir || ([[ "$cand" == *.y*ml ]] && echo yaml || echo md)); break
  fi
done
# ② 常见路径 (无声明时的兜底; 第一顺位保持原路径 = 对老仓零回归)
if [[ -z "$SOT" ]]; then
  if   [[ -f "$ROOT/.claude/active-tracks.yaml" ]]; then SOT="$ROOT/.claude/active-tracks.yaml"; KIND=yaml
  elif [[ -f "$ROOT/context/active-tracks.md"   ]]; then SOT="$ROOT/context/active-tracks.md";   KIND=md
  elif [[ -f "$ROOT/docs/active-tracks.md"      ]]; then SOT="$ROOT/docs/active-tracks.md";      KIND=md
  elif [[ -d "$ROOT/context/worklines"          ]]; then SOT="$ROOT/context/worklines";          KIND=dir
  fi
fi

# ── 都没命中 → 不阻塞, 但【绝不印 ✅】(印 ✅ 会被读成"查过了没问题") ──
if [[ -z "$SOT" ]]; then
  cat <<MSG
ℹ️ handoff-freshness: 未检测到 state SoT — 跳过保鲜检查(不阻塞)。
   已查: CLAUDE/AGENTS.md 里的声明(优先) · .claude/active-tracks.yaml · context|docs/active-tracks.md · context/worklines/
   若本仓其实有工作板, 请指出路径 —— 这条是"没查", 不是"没问题"。
MSG
  exit 0
fi

REL="${SOT#$ROOT/}"

# ── 判「今天动过没」的两种口径 ──
# yaml: 沿用原有 last_updated 字段(零回归)
# md/dir: **不要求人填字段** —— 用 git 算(本 session 改过 = 工作区有改动, 或今天已提交)
#         理由: 要人填的字段必然会空(实测某仓 166 张有现状块的卡里 146 张"更新时间"是空的)
touched_today() {  # $1 = 路径
  [[ -n "$(git -C "$ROOT" status --porcelain -- "$1" 2>/dev/null)" ]] && return 0
  local d; d=$(git -C "$ROOT" log -1 --format=%cd --date=format:%Y-%m-%d -- "$1" 2>/dev/null)
  [[ "$d" == "$TODAY" ]]
}

if [[ "$KIND" != "yaml" ]]; then
  TARGET="$SOT"
  if [[ "$KIND" == "dir" && -n "$TRACK_ID" ]]; then
    m=$(find "$SOT" -maxdepth 1 -name "*${TRACK_ID}*" -print -quit 2>/dev/null)
    [[ -n "$m" ]] && TARGET="$m"
  fi
  if touched_today "$TARGET"; then
    echo "✅ handoff-freshness: ${TARGET#$ROOT/} 本次已更新 (git 判定, 非人工声明)"
    exit 0
  fi
  echo "❌ handoff-freshness: ${TARGET#$ROOT/} 今天没被动过" >&2
  echo "   → Step 3b 要求刷新本仓 state SoT。改完再跑本闸。" >&2
  exit 1
fi

# ── yaml 分支: 原逻辑逐字保留 ──
track_last_updated() {
  awk -v tid="$1" '
    /^[[:space:]]*-[[:space:]]*id:/ {
      v = $0
      sub(/^[[:space:]]*-[[:space:]]*id:[[:space:]]*/, "", v)
      sub(/[[:space:]]*$/, "", v)
      cur = (v == tid)
    }
    cur && /last_updated:/ {
      d = $0
      sub(/.*last_updated:[[:space:]]*/, "", d)
      sub(/[[:space:]].*$/, "", d)
      sub(/[[:space:]]*$/, "", d)
      print d
      exit
    }
  ' "$SOT"
}

if [[ -n "$TRACK_ID" ]]; then
  LU="$(track_last_updated "$TRACK_ID")"
  if [[ -z "$LU" ]]; then
    echo "❌ handoff-freshness: track '$TRACK_ID' 不在 $REL" >&2
    echo "   → id 写错? 还是新 track 忘了加? 见 /handoff Step 2a/3b" >&2
    exit 1
  fi
  if [[ "$LU" != "$TODAY" ]]; then
    echo "❌ handoff-freshness: track '$TRACK_ID' last_updated=$LU, 不是今天 ($TODAY)" >&2
    echo "   → state-rot 防御: Step 3b 必须把本 track last_updated 改成 $TODAY" >&2
    exit 1
  fi
  echo "✅ handoff-freshness: track '$TRACK_ID' last_updated=$TODAY (state SoT 已刷新)"
  exit 0
else
  if grep -qE "last_updated:[[:space:]]*${TODAY}([[:space:]\"]|$)" "$SOT"; then
    echo "✅ handoff-freshness: $REL 有 track 今天 ($TODAY) 更新过 (弱检查)"
    echo "   ⚠ 未传 track-id, 只验证了'有 track 今天更新'。强检查: 本脚本 <track-id>"
    exit 0
  fi
  echo "❌ handoff-freshness: $REL 没有任何 track last_updated=$TODAY" >&2
  echo "   → Step 3b 漏了刷新 state SoT" >&2
  exit 1
fi
