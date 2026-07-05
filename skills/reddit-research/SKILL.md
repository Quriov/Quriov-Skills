---
name: reddit-research
description: Reddit 深度调研：通过 Arctic Shift API（免认证、已实测可用）抓取 subreddit 帖子、评论树、做痛点/口碑分析。当用户说"调研 reddit"、"看看 r/xxx"、"reddit 用户怎么看"、"reddit 上 xxx 的反馈/痛点/口碑"、"reddit 高赞帖"，或做市场/产品/竞品/选品调研需要 Reddit 数据源时触发本 skill。
---

# Reddit 调研 Skill（指针）

> ⚠️ **本 skill 的方法论内容已单源化到公开仓库 [Quriov/reddit-research](https://github.com/Quriov/reddit-research)，那边是唯一事实源。**
> 本文件自 2026-07-05 起只做触发入口，不再维护正文——旧正文已确认多处过时（`limit` 实测上限 100 而非 auto→1000；服务端关键词过滤 `title`/`selftext`/`body` 处于 "Under maintenance"，需改走全量拉取+本地过滤）。

## 怎么用

触发本 skill 后，**先读取并遵循最新方法论**（端点可用性快照、分页/重试 SOP、评论树、痛点提取 SOP、来源引用格式、合规边界）：

```
https://raw.githubusercontent.com/Quriov/reddit-research/main/SKILL.md
```

参考脚本（翻页全量抓取 / 本地吐槽过滤+主题归类）在同仓库 `examples/` 目录，可直接下载运行：

```
https://raw.githubusercontent.com/Quriov/reddit-research/main/examples/fetch_subreddit.sh
https://raw.githubusercontent.com/Quriov/reddit-research/main/examples/filter_and_rank.py
```

## 为什么指针化

两处维护同一份方法论必然分叉（本文件 2026-06 版与 2026-07 实测已经分叉过一次）。机制优于自觉：内容只活在公开仓库一处，这里永远只有指针。
