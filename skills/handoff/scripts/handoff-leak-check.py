"""handoff-leak-check.py — 量「按【已了结】砍掉交接内容」会漏多少。

用法: python3 handoff-leak-check.py <按时间排序的转录1> <转录2> ... [--control]
      每两个相邻文件构成一个接班对。--control 跑反向对照(排除反向因果)。

⭐ 为什么需要它(宇通 2026-09-03 拍「必须靠实际验证才能说明这套体系可行」):
   三档分法把「已了结且不会再撞上」的事项折叠掉。那个判断【会出错】,
   而错的方向是【看不见的】—— 漏掉的东西不会报错, 只会让下一棒重走一遍弯路。
   ⇒ 这个脚本把「看不见」变成一个可以反复量的数。

📌 首次实测(CI/AI Review 线 7 个接班对, 2026-09-03):
   · 标「已了结」87 个 → 下一棒回头查了 29 个 ⇒ **33%**
     其中 #3541 正是当天独立报回的「卡顶过期两周骗了两棒人」那件 —— 方法被已知案例佐证。
   · 反向对照: 下一棒查过 356 个号, **80% 是交接单里根本没有的**
     ⇒ 查询是【任务驱动】不是【交接单驱动】, 反向因果排除, 那 33% 是真需求。
   · 顺带量到: 交接单只覆盖下一棒查询的 **19%** —— 预测力本来就低, 所以「该砍」也成立。

🚨 自我证伪 / 升级条件:
   三档分法上线后, 每月跑一次。**漏失率若回升到 >20%, 说明 C 档判据太松, 要收紧**
   (最可能的收紧方向: 把「近两周内动过的」一律留在 B 档)。
   ⚠ 反过来若长期 <5%, 说明 B 档留太多, 可以再砍。
"""

import json,sys,re,os
PR = re.compile(r'#(\d{3,4})\b')
ACT = re.compile(r'#(\d{3,4})\b|(?:pr|issue)\s+(?:view|comment|close|edit|reopen)\s+(\d{3,4})\b')
DONE = re.compile(r'已合|已修|已完成|已关|已落地|MERGED|已部署|✅|完成|closed', re.I)

def load(F):
    rows=[]
    for l in open(F,encoding='utf-8'):
        l=l.strip()
        if not l: continue
        try: rows.append(json.loads(l))
        except: pass
    return rows

def handed_docs(rows):
    """上一棒写出的交接类产物正文"""
    out=[]
    for r in rows:
        c=(r.get('message') or {}).get('content')
        if not isinstance(c,list): continue
        for b in c:
            if not (isinstance(b,dict) and b.get('type')=='tool_use'): continue
            i=b.get('input') or {}
            txt=str(i.get('content') or i.get('command') or '')
            fp=str(i.get('file_path',''))
            if len(txt)>1500 and ('handoff' in txt or 'handoff' in fp or '交接' in txt or 'ledger' in fp):
                out.append(txt)
    return out

def acted(rows):
    """下一棒【自己发起的工具调用】里出现的号"""
    s=set()
    for r in rows:
        c=(r.get('message') or {}).get('content')
        if not isinstance(c,list): continue
        for b in c:
            if isinstance(b,dict) and b.get('type')=='tool_use':
                blob=json.dumps(b.get('input') or {},ensure_ascii=False)
                for m in ACT.finditer(blob):
                    s.add(m.group(1) or m.group(2))
    return s

files=sys.argv[1:]
tot_done=tot_leak=0; leaks=[]
print(f"{'上一棒→下一棒':22}{'标已了结':>9}{'下棒回查':>9}{'漏':>5}")
print("-"*50)
for a,b in zip(files, files[1:]):
    ra,rb=load(a),load(b)
    docs=handed_docs(ra)
    if not docs: continue
    done=set()
    for d in docs:
        for line in d.split('\n'):
            if DONE.search(line):
                done |= {m.group(1) for m in PR.finditer(line)}
    if not done: continue
    act=acted(rb)
    leak=done & act
    tot_done+=len(done); tot_leak+=len(leak)
    if leak: leaks.append((os.path.basename(a)[:8],os.path.basename(b)[:8],sorted(leak)))
    print(f"{os.path.basename(a)[:8]}→{os.path.basename(b)[:8]:13}{len(done):>9}{len(leak):>9}{len(leak)*100//max(len(done),1):>4}%")
print("-"*50)
print(f"合计: 标「已了结」{tot_done} 个 · 下一棒回头查了 {tot_leak} 个 ⇒ **{tot_leak*100//max(tot_done,1)}%**")
if leaks:
    print("\n⚠ 具体是哪些(抽样人工核):")
    for a,b,ls in leaks[:4]: print(f"  {a}→{b}: {ls[:10]}")
