"""handoff-cost-baseline.py — 量一次 handoff 的【收尾成本】, 并按工作量归一化。

用法: python3 handoff-cost-baseline.py <转录1.jsonl> <转录2.jsonl> ...
      每个文件出一行; 同一条线的多份转录一起给, 就得到该线的【自比基线】。

⭐ 为什么必须归一化 —— 这是 2026-09-03 实测出来的, 不归一化会【假红】:
   某次实测收尾 32 轮, 对照组中位 32.5 ⇒ 光看轮数结论是「毫无改善」。
   但那一棒交接了 63 个 PR(历史最高档), 每 PR 读入 338k vs 对照组中位 632k ——
   **七次里最低, 降约 47%。**
   ⭐ 最硬的是一个天然配对: 历史上另一次【也正好 63 个 PR】, 它 34 轮 / 26.7M / 423k;
      本次 32 轮 / 21.3M / 338k ⇒ 同件数下读入降 20%, 而且本次还多背了账本 + 自检脚本两样新动作。
   🔑 **轮数受「那一棒干了多少活」支配, 它不是衡量流程好坏的量。主判据用【每件事的读入】。**

⚠ 三条实现纪律(都是踩出来的):
   · 起点 = `Skill(skill="handoff")` 那次 tool_use, 不是 `/handoff` 字符串
     (实测: 历史转录里一份 `command-name>/handoff` 都匹配不到)
   · 按 `requestId` 去重数轮次 —— **一行 ≠ 一轮**(thinking/text/tool_use 各占一行但共享 requestId)
   · 每轮读入 = input + cache_read + cache_creation, 三项都要算
"""
import json, sys, os, re

def run(F):
    rows = []
    for l in open(F, encoding='utf-8'):
        l = l.strip()
        if not l: continue
        try: rows.append(json.loads(l))
        except Exception: pass
    st = None
    for i, r in enumerate(rows):
        c = (r.get('message') or {}).get('content')
        if isinstance(c, list):
            for b in c:
                if isinstance(b, dict) and b.get('type') == 'tool_use' \
                   and b.get('name') == 'Skill' and (b.get('input') or {}).get('skill') == 'handoff':
                    st = i; break
        if st is not None: break
    if st is None: return None
    seg = rows[st:]
    reqs, ins, out = [], [], []
    for r in seg:
        if r.get('type') != 'assistant': continue
        rid = r.get('requestId')
        if rid and rid not in reqs:
            reqs.append(rid)
            u = (r.get('message') or {}).get('usage') or {}
            t = u.get('input_tokens',0)+u.get('cache_read_input_tokens',0)+u.get('cache_creation_input_tokens',0)
            if t: ins.append(t)
            out.append(u.get('output_tokens', 0))
    blob = json.dumps(seg, ensure_ascii=False)
    prs = len(set(re.findall(r'#(\d{3,4})', blob)))
    return dict(f=os.path.basename(F)[:8], turns=len(reqs), tot=sum(ins), prs=prs,
                lps=len(re.findall(r'落点:', blob)), per_pr=sum(ins)//prs if prs else 0,
                out=sum(out), ledger=('ledger' in blob or '账本' in blob),
                selfcheck=('handoff-selfcheck' in blob))

rows = [r for r in (run(F) for F in sys.argv[1:]) if r]
if not rows:
    print("❌ 没有一份转录里找得到 Skill(handoff) —— 换文件, 或那几棒没跑过本 skill"); raise SystemExit(1)
print(f"{'转录':10}{'轮数':>6}{'收尾总读入':>13}{'PR数':>6}{'落点':>5}{'⭐每PR读入':>12}{'总产出':>9}  账本 自检")
print("-" * 80)
for r in sorted(rows, key=lambda x: x['per_pr']):
    print(f"{r['f']:10}{r['turns']:>6}{r['tot']:>13,}{r['prs']:>6}{r['lps']:>5}{r['per_pr']:>12,}{r['out']:>9,}"
          f"   {'✓' if r['ledger'] else '✗'}   {'✓' if r['selfcheck'] else '✗'}")
if len(rows) > 1:
    pp = sorted(x['per_pr'] for x in rows); tn = sorted(x['turns'] for x in rows)
    print("-" * 80)
    print(f"  轮数中位 {tn[len(tn)//2]}  ·  ⭐ 每 PR 读入中位 {pp[len(pp)//2]:,}  ← 主判据用这个")
