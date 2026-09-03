#!/usr/bin/env bash
# handoff-selfcheck.sh — 一条命令跑完 handoff 收尾要引用的全部只读核对。
#
# 为什么存在: 2026-09-02 读 7 份 handoff 收尾转录, 三大成本来源之一是
# 「到收尾才第一次去数数」—— 最长那份连着 5 次调用只为拿准一个跨线消息数。
# 这些全是彼此独立的只读查询, 每跑一条都要重读几十万上下文。
#
# 纪律(照 handoff skill Step 0 那张退出码表):
#   · 每段 `=== [n] ... ===` 分隔 —— 防「前一条的输出填满后一条的空位」
#   · 每条独立 `|| echo ❌` 判成败, 绝不用总退出码
#   · 不用管道截断(`| head`), 用命令自带的限制参数 —— 避免 pipefail 假红 / 无 pipefail 假绿
#
# 用法:
#   handoff-selfcheck.sh                          # 在当前仓跑
#   handoff-selfcheck.sh --repo <path>            # 指定仓/工作树
#   handoff-selfcheck.sh --label workline:xxx     # 顺带数本线 open issue
#   handoff-selfcheck.sh --transcript <jsonl>     # 指定转录(默认按 cwd 推最近那份)

set -u
REPO="$PWD"; LABEL=""; TRANSCRIPT=""
while [ $# -gt 0 ]; do
  case "$1" in
    --repo)       REPO="$2"; shift 2 ;;
    --label)      LABEL="$2"; shift 2 ;;
    --transcript) TRANSCRIPT="$2"; shift 2 ;;
    -h|--help)    sed -n '2,20p' "$0"; exit 0 ;;
    *) echo "❌ 未知参数: $1"; exit 2 ;;
  esac
done

echo "=== [0] 今天几号(⛔ 别靠记忆 — session 会跨天) ==="
date "+%Y-%m-%d %H:%M %Z" || echo "❌ [0] 失败(exit $?)"

echo
echo "=== [1] 仓 / 分支 / 落后 / 自有提交 / 工作区 ==="
echo "repo: $REPO"
git -C "$REPO" rev-parse --abbrev-ref HEAD          || echo "❌ [1a] 取分支失败(exit $?)"
git -C "$REPO" fetch -q origin 2>/dev/null; echo "(fetch 已跑, 失败不阻断)"
echo "-- 落后 origin/main 几个 commit(⭐ 不是 0 就先拉平再量任何东西) --"
git -C "$REPO" rev-list --count HEAD..origin/main   || echo "❌ [1b] 失败(exit $?)"
echo "-- 自有提交几个(领先 origin/main) --"
git -C "$REPO" rev-list --count origin/main..HEAD   || echo "❌ [1c] 失败(exit $?)"
echo "-- 工作区(空 = 干净) --"
git -C "$REPO" status --short                       || echo "❌ [1d] 失败(exit $?)"

echo
echo "=== [2] 本分支的自有提交(⚠ 这些还没进 main) ==="
git -C "$REPO" log origin/main..HEAD --oneline -n 40 || echo "❌ [2] 失败(exit $?)"
echo "(空 = 全部已进 main。⛔ 但「分支未进 main」在 squash 之后不可信 — 以 [3] 的 PR 状态为准)"

# ⚠ BSD sed(macOS 自带)不支持 lazy 量词 `+?` —— 用它会报
#   "RE error: repetition-operator operand invalid", 而 $(...) 吃掉错误后**返回空串**,
#   gh 拿到空 --repo 会**静默回落到 cwd 的仓** ⇒ 假绿。所以这里既换写法, 也校验非空。
ORIGIN_URL="$(git -C "$REPO" remote get-url origin 2>/dev/null)"
NWO="$(printf '%s' "${ORIGIN_URL:-}" | sed -E 's#^.*[:/]([^/]+)/([^/]+)$#\1/\2#; s#\.git$##')"
case "${NWO:-}" in
  */*) : ;;
  *)   NWO=""; echo "⚠ 解析不出 owner/repo(origin=${ORIGIN_URL:-<空>}) — [3][4][7] 会跳过, 不会拿默认仓充数" ;;
esac

echo
echo "=== [3] 本分支相关 PR 及状态(判「已合没合」只有这个算数) ==="
BR="$(git -C "$REPO" rev-parse --abbrev-ref HEAD 2>/dev/null)"
if [ -n "${BR:-}" ] && [ -n "${NWO:-}" ]; then
  echo "repo=$NWO  branch=$BR"
  gh pr list --repo "$NWO" --head "$BR" --state all --limit 10 \
     --json number,state,title,mergedAt \
     --jq '.[] | "#\(.number) \(.state) \(.mergedAt // "-") \(.title)"' \
     || echo "❌ [3] 失败(exit $?) — 「本分支没有 PR」和「gh 出错」不是一回事, 自己分清"
  echo "(以上为空 = 本分支没开过 PR)"
else
  echo "❌ [3] 缺分支名或 owner/repo, 跳过"
fi

echo
echo "=== [4] 最近进 main 的 PR(近 20 个, 对账用) ==="
if [ -n "${NWO:-}" ]; then
  gh pr list --repo "$NWO" --state merged --limit 20 --json number,mergedAt,title \
     --jq '.[] | "#\(.number) \(.mergedAt) \(.title)"' \
     || echo "❌ [4] 失败(exit $?)"
else
  echo "❌ [4] 无 owner/repo, 跳过"
fi

echo
echo "=== [5] handoff 目录在哪(⛔ 别假设是 docs/handoffs) ==="
FOUND=0
for d in docs/handoffs context/handoffs handoffs .claude/handoffs; do
  if [ -d "$REPO/$d" ]; then
    N=$(find "$REPO/$d" -name '*.md' -type f 2>/dev/null | wc -l | tr -d ' ')
    echo "✅ $d  ($N 份)"
    # ⚠ 别用 mtime 排 —— checkout / 切分支会把 archive 里的老文件刷成「最新」。
    #   按【文件名里的日期】排, 并排除 archive/(实测: mtime 排法把两份 7 月的归档文件排进了前三)。
    echo "   最近三份(按文件名日期, 已排除 archive/):"
    # ⚠ 只认 20xx- 打头: 字符串倒序时大写字母(HOWTO/TEMPLATE/README/NEXT-…)排在数字前面,
    #   实测把 NEXT-SESSION-PROMPT.md 和 HOWTO.md 排进了「最近三份」。
    # ⚠ 排除 archive/ 与 attachments/ —— 后者是交接单的附件, 不是交接单本身
    #   (CI/AI Review v6.7 2026-09-03 实测: 它那次「最近三份」前两名都是 attachment)
    find "$REPO/$d" -name '20*.md' -type f -not -path '*/archive/*' -not -path '*/attachments/*' 2>/dev/null \
      | sed "s#^$REPO/##" | sort -r | head -3 | sed 's/^/     /'
    FOUND=1
  fi
done
[ "$FOUND" = "0" ] && echo "⚠ 四个常见路径都不存在 — 本仓没有 handoff 目录, 或它在别处。别猜, 去 grep 项目 CLAUDE.md/AGENTS.md"

echo
echo "=== [6] 跨线消息统计(⭐ 这一段就是本脚本存在的理由) ==="
# 🚨 结构性坑(实测撞到): 转录按【session 的 cwd】归档, 而本脚本的 cwd 是你运行它的地方 ——
#    两者经常不同(典型: session 的工作树被回收, cwd 被重置回仓根, 而你在工作树里跑脚本)。
#    ⇒ ⛔ 不许「推一个 slug 就当答案」。没给 --transcript 时, 只【列候选】让人自己挑。
if [ -z "$TRANSCRIPT" ]; then
  echo "⚠ 没给 --transcript。转录按【session 的 cwd】归档, 而脚本不知道那是什么 ——"
  echo "   下面列出全机最近改动的 5 份转录, ⭐【自己认哪份是本 session】, 然后重跑并加 --transcript:"
  find "$HOME/.claude/projects" -maxdepth 2 -name '*.jsonl' -type f -mmin -600 2>/dev/null \
    -exec ls -lt {} + 2>/dev/null | head -5 | awk '{print "     "$6" "$7" "$8"  "$NF}' \
    || echo "   ❌ 列举失败(exit $?)"
  echo "   (判据: 本 session 那份【正在被写】, mtime 就是刚刚; 拿不准就 grep 一句你刚说过的话)"
fi
if [ -n "${TRANSCRIPT:-}" ] && [ -f "$TRANSCRIPT" ]; then
  echo "转录: $TRANSCRIPT"
  echo "mtime: $(date -r "$TRANSCRIPT" '+%Y-%m-%d %H:%M' 2>/dev/null)"
  python3 - "$TRANSCRIPT" <<'PYEOF' || echo "❌ [6] 解析失败(exit $?)"
import json, sys, re, collections
F = sys.argv[1]
sent = collections.Counter(); recv = collections.Counter(); compacts = []
recv_names = {}   # 地址 → 该地址期间用过的名字(可能不止一个)
n = 0
with open(F, encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line: continue
        try: r = json.loads(line)
        except Exception: continue
        n += 1
        # 🚨 别在 json.dumps 的结果上正则匹配内容 —— dumps 把内层引号转义成 \" 、冒号后加空格
        #    ⇒ 形如 from="x" / "preTokens":123 的正则【永远匹配不到】, 而结果是一个看起来很正常的 0。
        #    实测两个都中过。⇒ 结构化的走 dict 取值; 文本的走 txt() 提取出来的原文。
        cm = r.get('compactMetadata') or (r.get('message') or {}).get('compactMetadata') or {}
        if cm:
            compacts.append((str(cm.get('preTokens', '?')), str(cm.get('postTokens', '?'))))
        c = (r.get('message') or {}).get('content')
        body = ''
        if isinstance(c, str):
            body = c
        elif isinstance(c, list):
            for b in c:
                if not isinstance(b, dict): continue
                if b.get('type') == 'text':
                    body += b.get('text') or ''
                elif b.get('type') == 'tool_use' and 'send' in (b.get('name') or '').lower():
                    # 🚨 别按单一工具名过滤 —— 两个工具都会发跨线消息:
                    #    ccd 的叫 send_message(参数 session_id), 内置的叫 SendMessage(参数 to)。
                    #    原判据写的是 `'send_message' in name`, 匹配不到 SendMessage ⇒ 整整一个通道无声漏掉,
                    #    而它打印出来的是一个【量出来的、错的 0】—— 比不打印更可信。(CI/AI Review v6.7 报, 2026-09-03)
                    i = b.get('input') or {}
                    tgt = str(i.get('session_id') or i.get('to') or '?')
                    sent[tgt] += 1
        # 🚨 属性名有两种: local_ 通道是 name=, uds 通道是 from-name= —— 只认一种会漏掉一整个通道。
        #    原正则还要求 name 紧跟 from, 中间有别的属性就断。(CI/AI Review v6.7 报, 2026-09-03)
        for m2 in re.finditer(r'<cross-session-message\s+from="([^"]+)"([^>]*)>', body):
            frm, rest = m2.group(1), m2.group(2)
            nm = re.search(r'(?:from-)?name="([^"]*)"', rest)
            nm = nm.group(1) if nm else ''
            # ⚠ 按【地址】计数, 名字只作显示 —— 同一个地址在一段时间里可能有【两个名字】
            #    (对方改过 session 标题就会这样)。按「名字+地址」当 key 会把同一条线拆成两行。
            #    📌 实测(总控 v6.1 报, 2026-09-03): 同一个 local_6f97eeb1… 以
            #    「Handoff体系 v1.9」和「协作基建-Handoff体系 v1.9」占了两行 —— 那天它改过标题。
            recv[frm] += 1
            recv_names.setdefault(frm, [])
            if nm and nm not in recv_names[frm]: recv_names[frm].append(nm)
print(f"转录行数: {n}")
print(f"本 session 压缩过 {len(compacts)} 次" + (f": {', '.join(a+'→'+b for a,b in compacts)}" if compacts else ""))
# 🚨🚨 【刻意不打印「N 条线」】—— 机器归并不了「线」, 打印一个算不准的数比不打印更危险。
#    uds 通道的名字是 **cwd 目录名**(worktree 首任起的), local_ 通道的名字是 **session 标题**,
#    两者之间没有可靠映射 —— 那正是「用 cwd 名找收件线」这条规则 2026-09-03 被作废的同一个根源:
#    **worktree 会换住户。**
#    📌 实测(本 skill 作者自己那条 session): 按名字去重得「8 条线」, 真值是 **5 条** ——
#    「智能眼镜-总控 v6.1 / competent-borg-f7485f-01 / -98」是同一条,
#    「智能眼镜-IOS v5.0 / smart-glasses-ios-v4-3-cb1077-2e」是同一条。
#    ⇒ 只按通道分组、把两边都摆出来, **线数留给人认**。

def _disp(a):
    ns = recv_names.get(a) or []
    if not ns: return f"(无名) [{a}]"
    if len(ns) == 1: return f"{ns[0]} [{a[:24]}…]"
    return f"{ns[-1]} [{a[:24]}…] ⚠ 期间还用过: {', '.join(ns[:-1])}"

print(f"\n发出的跨线消息: {sum(sent.values())} 条 · 目标地址 {len(sent)} 个")
for k, v in sent.most_common(): print(f"  → {k}: {v}")
print(f"\n收到的跨线消息: {sum(recv.values())} 条 · 来源地址 {len(recv)} 个")
for a, v in recv.most_common(): print(f"  ← {_disp(a)}: {v}")
loc = {a: v for a, v in recv.items() if a.startswith('local_')}
uds = {a: v for a, v in recv.items() if not a.startswith('local_')}
print(f"\n⭐ 按【通道】分组 —— ⛔ 这里【不报线数】, 机器归并不了(理由见脚本注释):")
print(f"   local_ 通道 {len(loc)} 个来源(名字 = session 标题, 是真名):")
for a, v in sorted(loc.items(), key=lambda x: -x[1]): print(f"     {_disp(a)}: {v}")
print(f"   uds 通道 {len(uds)} 个来源(名字 = cwd 目录名, ⚠ worktree 首任起的, 可能已换住户):")
for a, v in sorted(uds.items(), key=lambda x: -x[1]): print(f"     {_disp(a)}: {v}")
print("   🔑 上下两组【很可能指向同一批线】—— 同一条线走两个通道就会各出现一次。")
print("      要线数请自己认(对 cwd 名用 list_sessions 查它现在的住户, 别按名字猜)。")
PYEOF
else
  echo "⇒ 本段未运行(见上)。⛔ 别把这当成「跨线消息 0 条」。"
fi

if [ -n "$LABEL" ]; then
  echo
  echo "=== [7] 本线 open issue (label=$LABEL) ==="
  if [ -n "${NWO:-}" ]; then
    gh issue list --repo "$NWO" --label "$LABEL" --state open --limit 200 --json number --jq 'length' \
       || echo "❌ [7] 失败(exit $?)"
  else
    echo "❌ [7] 无 owner/repo, 跳过"
  fi
fi

echo
echo "=== 完 ==="
echo "⚠ 每段独立判成败 — 上面出现 ❌ 的那几段【不算跑过】, 别把它们当成「空结果」。"
