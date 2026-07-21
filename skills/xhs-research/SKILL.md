---
name: xhs-research
description: 小红书（XHS）博主内容调研：按名字或主页链接，批量拿指定博主的笔记列表 + 正文 + 互动数据。基于 cv-cat/Spider_XHS（逆向签名、纯 API）。当用户说"调研小红书 xxx"、"拿 xxx 的小红书笔记"、"小红书对标 xxx"、"抓小红书博主内容"、"xxx 在小红书发了什么"时触发。需专用小号 cookie（有风控风险，别用主号）。与 x-research / reddit-research / youtube-research 同属社媒调研 skill 家族。
---

# 小红书（XHS）调研 Skill

## 架构：站在 Spider_XHS 之上，不重造签名

小红书强制 `x-s`/`x-t`/`x-s-common` 签名（约每月一变），裸爬 / `requests` 因 TLS 指纹秒封。本 skill 站在 **[cv-cat/Spider_XHS](https://github.com/cv-cat/Spider_XHS)**（逆向了完整签名、纯 API 无需浏览器）之上，只做「定位博主 → 拿笔记 → 拿正文」的编排 + 踩坑规避。

> 本 skill **不 vendored** Spider_XHS 代码（第三方 + 仅供学习 license）。你需自己装它的官方 skill 封装 `XhsSkills`；本 skill 只放**通用编排脚本 + 补丁 + SOP**。cookie 是你自己的专用小号、走 `.secrets/` 不上 repo——**换个人配自己的账号就能跑**。

## 一次性安装

1. **clone XhsSkills**（cv-cat 官方 Spider_XHS skill 封装，自带裁剪运行时）：
   ```
   git clone https://github.com/cv-cat/XhsSkills.git <你选的目录>
   ```
2. **装依赖**（Python 3.10+ / Node 20+）：
   ```
   cd <XhsSkills>/skills/xhs-apis/scripts
   python -m venv .venv
   .venv/Scripts/python -m pip install -r requirements.txt   # Windows；*nix 用 .venv/bin/python
   npm install
   ```
3. **打补丁**（修 Spider_XHS 的 `split('=')` 截断 base64 token bug，见踩坑 #2）：
   ```
   python <本skill>/scripts/patch_spider_xhs.py <XhsSkills>/skills/xhs-apis/scripts
   ```
4. **设环境变量**指向 XhsSkills 的 scripts 目录：
   ```
   XHS_SKILLS_SCRIPTS=<XhsSkills>/skills/xhs-apis/scripts
   ```

## 配 cookie（专用小号，不上 repo）

1. 浏览器登录**专用小号** `xiaohongshu.com`——**确认登录成功**（右上角是你的头像，不是"登录"按钮）
2. `Cookie-Editor` 扩展 → Export → **Header String**（密码留空）
3. 存到 `scripts/.secrets/xhs_cookie.txt`（`.gitignore` 已忽略，不上 repo）

## 用法

```
# 按名字搜博主（自动选 note_count 最高的那个）
python scripts/probe_and_fetch.py --search "博主名"

# 已知主页链接（从小红书 App 分享/复制，含 xsec_token）
python scripts/probe_and_fetch.py --user-url "https://www.xiaohongshu.com/user/profile/ID?xsec_token=...&xsec_source=pc_search"

# 已知 user_id + token
python scripts/probe_and_fetch.py --user-id ID --xsec-token TOKEN

# 抓前 5 篇正文（默认 3；0 = 不抓正文）
python scripts/probe_and_fetch.py --search "博主名" --bodies 5
```

输出：`scripts/xhs_notes.json`（每篇：标题 / note_id / type / 点赞 / xsec_token / 链接 / 正文）。

## 三个坑（踩过的，务必知道）

1. **游客态 cookie**：小红书**搜索游客也能用**，但看博主主页笔记流（`user_posted`）**必须登录态**，游客态一律 `code=-100 登录已过期`。脚本内建 `get_user_self_info` 探针（`data` 空 = 游客）先拦。**新注册小号易被风控登出 → 变游客态**；症状是"搜得到人、抓不到笔记"，重登再导 cookie 即可。
2. **Spider_XHS `split('=')` bug**：`get_user_all_notes` / `get_note_info` / `get_note_all_comment` 用 `kv.split('=')[1]` 解析 URL，会**截断 base64 `xsec_token` 末尾的 `=`** → token 失效 → 返回误导的"登录已过期"。`patch_spider_xhs.py` 改成 `split('=', 1)` 修复（幂等）。**这也是为什么脚本走 `get_user_note_info`（显式传 token）而非 `get_user_all_notes`（走 URL 解析）**。值得回 PR 给上游。
3. **视频笔记 desc = 话题标签**：小红书视频笔记的 `desc` 是话题标签（`#xxx#`），**完整口播要转写**（同抖音）；图文笔记（`type=normal`）的 `desc` 才是完整文字正文。所以"文本"层：视频 = 标题 + 标签，图文 = 完整正文。

## 风控红线

- **只用专用小号**，别用主号（逆向 API 属 ToS 灰色地带，有封号风险）。
- 低频、小批量；批量翻页时留间隔（2–3s）。
- 触发验证码/风控是预期内，如实报，别为绕风控反复换号硬试。

## 与其他社媒调研 skill 的关系

| Skill | 数据源 | 取数方式 |
|---|---|---|
| `reddit-research` | Reddit | Arctic Shift API（免认证） |
| `x-research` / `timeline_x.py` | X 推文 | SSH 硅谷服务器 twikit |
| **`xhs-research`（本 skill）** | 小红书笔记 | Spider_XHS 逆向签名 API（本地 + 专用小号 cookie） |
| `youtube-research` | YouTube | 见该 skill |
