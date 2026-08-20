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

# ── 按序探测本仓的 state SoT (命中即停; 第一顺位保持原路径 = 零回归) ──
SOT=""; KIND=""
if   [[ -f "$ROOT/.claude/active-tracks.yaml" ]]; then SOT="$ROOT/.claude/active-tracks.yaml"; KIND=yaml
elif [[ -f "$ROOT/context/active-tracks.md"   ]]; then SOT="$ROOT/context/active-tracks.md";   KIND=md
elif [[ -f "$ROOT/docs/active-tracks.md"      ]]; then SOT="$ROOT/docs/active-tracks.md";      KIND=md
elif [[ -d "$ROOT/context/worklines"          ]]; then SOT="$ROOT/context/worklines";          KIND=dir
else
  # 项目自己声明的指针 (CLAUDE.md / AGENTS.md 里 grep 得到的路径)
  for decl in "$ROOT/CLAUDE.md" "$ROOT/AGENTS.md"; do
    [[ -f "$decl" ]] || continue
    cand=$(grep -oE '(context|docs|\.claude)/[A-Za-z0-9_/.-]*(active-tracks|worklines)[A-Za-z0-9_/.-]*' "$decl" 2>/dev/null | head -1)
    if [[ -n "$cand" && -e "$ROOT/$cand" ]]; then
      SOT="$ROOT/$cand"; KIND=$([[ -d "$ROOT/$cand" ]] && echo dir || echo md); break
    fi
  done
fi

# ── 都没命中 → 不阻塞, 但【绝不印 ✅】(印 ✅ 会被读成"查过了没问题") ──
if [[ -z "$SOT" ]]; then
  cat <<MSG
ℹ️ handoff-freshness: 未检测到 state SoT — 跳过保鲜检查(不阻塞)。
   已查: .claude/active-tracks.yaml · context|docs/active-tracks.md · context/worklines/ · CLAUDE/AGENTS.md 里的声明
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
