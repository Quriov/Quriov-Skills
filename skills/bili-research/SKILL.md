---
name: bili-research
description: B站（Bilibili）UP 主内容调研：按名字或 UID 拿指定 UP 主的视频列表 + 详情（简介/字幕/AI总结）+ 互动数据，视频可切 ASR 片段转写。基于 bili-cli（游客态、零账号）。当用户说"调研B站 xxx"、"拿 xxx 的B站视频"、"B站对标 xxx"、"xxx 在B站发了什么"、"抓B站UP主内容"时触发。与 x-research/xhs-research/reddit-research/youtube-research 同属社媒调研 skill 家族。
---

# B站（Bilibili）调研 Skill

## 特点：游客态、零账号、零成本

B站 UP 主的视频列表/详情是**公开数据**，`bili-cli` 游客态就能拿，**不用登录、不用任何号**（`bili login` 只给点赞/投币/发动态等写操作用）。这是它比小红书（要登录态）、抖音（要小号）省事的地方。

## 安装

```
pipx install bilibili-cli    # 第三方，非 B站官方；走 web API
```

> ⚠️ **Windows**：bili-cli 输出含 emoji（📺），GBK console 会 `UnicodeEncodeError`。命令前加 `PYTHONIOENCODING=utf-8`（本 skill 的脚本已内建）。

## 直接用 bili-cli（原生够用）

```
# 名字 → 视频列表（user-videos 可直接传用户名，自动搜第一个匹配）
bili user-videos "dontbesilent聊赚钱" --json
# 搜 UP 主（拿 UID + 粉丝/视频数，用来选对本尊）
bili search "名字" --type user --json
# 单视频详情（标题+简介+字幕+B站AI总结+互动）
bili video BV1TGKm6wEUu --json
# 下音频切 ASR-ready WAV（25s/段，16kHz mono，喂转写 API）
bili audio BV1TGKm6wEUu
```

所有查询命令都有 `--json` / `--yaml`（推荐给 AI Agent）。

## 一句话封装（选对本尊 + 串详情）

`user-videos 传名字`只取"搜索第一个匹配"，可能不是本尊（同名号）。本 skill 脚本按"名字匹配 + 粉丝最多"选对人，并串联详情：

```
python scripts/fetch_bili_creator.py --search "博主名"
python scripts/fetch_bili_creator.py --uid 275565632 -n 30
python scripts/fetch_bili_creator.py --search "博主名" --details 5   # 前 5 个拿简介/字幕/AI总结
```

输出 `scripts/bili_videos.json`（每个：标题 / bvid / url / 播放 / 点赞 +（`--details`）简介 / 字幕 / AI总结）。

## 文本层说明

- **标题**：游客即得（信息量大）。
- **简介 `description` / 字幕 `subtitle` / B站 AI 总结 `ai_summary`**：`bili video` 一并拿——**有则直接是文本**（有 CC 字幕的视频等于免费拿全文）。
- **完整口播（无字幕时）**：`bili audio` 切 ASR-ready WAV → 喂语音转文字（归"内容理解"层，同抖音）。B站的优势是切片链路 bili-cli 内建了。

## 风控红线

- 只读公开数据、游客态，风险极低；无需账号即无封号风险。
- 若做写操作（点赞/投币）才需 `bili login`，那时用专用小号、别用主号。

## 与其他社媒调研 skill 的关系

| Skill | 数据源 | 账号 |
|---|---|---|
| `reddit-research` | Reddit | 免认证 API |
| `x-research` | X 推文 | SSH 服务器 twikit（小号） |
| `xhs-research` | 小红书 | 专用小号 cookie |
| **`bili-research`（本 skill）** | B站视频 | **游客态、零账号** |
| `youtube-research` | YouTube | 见该 skill |
