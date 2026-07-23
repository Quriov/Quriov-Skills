# Quriov Skills

Quriov 团队的 **AI agent skill 单一来源(SoT)**。

`SKILL.md` 是跨 agent 标准 —— 同一份 skill 装到 **Claude Code / Codex / Cursor / OpenCode** 等任何支持它的 agent 都能用,**不依赖任何插件或 marketplace**(那些只服务单一工具)。

## 安装

```bash
npx skills add Quriov/Quriov-Skills -g --all
```

只装其中几个:

```bash
npx skills add Quriov/Quriov-Skills -g -a '*' -s handoff,deep-intent-analysis
```

先看有哪些、不装:

```bash
npx skills add Quriov/Quriov-Skills --list
```

- `-g` = 装到用户级(所有项目可用),不加则装到当前项目
- `-a '*'` = 装到本机检测到的所有 agent;不加 `-a` 会自动探测并让你选

## 更新

```bash
npx skills update -g
```

每个 skill 顶部都有 `<!-- <name>-skill-rev: <日期> -->` 版本锚点。想确认自己拿到的是哪一版:

```bash
grep -r skill-rev ~/.agents/skills/handoff/SKILL.md
```

日期 ≥ 你预期的更新日 = 拿到了。

## Skills

### 开发协作

| Skill | 干什么 |
|---|---|
| `handoff` | 收尾长 session:产出结构化交接文档 + 下个 session 的接班 prompt。含 live-verify(不信 memory 自报)、逐字用户信号提取、memory hygiene、self-lint 防虚报完成 |
| `deep-intent-analysis` | 动手前做三层意图分析(表面→直接→深层)+ 举一反三,拿到范围确认再写代码 |

### 社媒读 / 发

| Skill | 干什么 |
|---|---|
| `reddit-research` / `reddit-publish` | Reddit 调研(Arctic Shift API,免认证)/ 发帖与回复 |
| `x-research` / `x-publish` | X(推特)调研 / 发推与回复 |
| `youtube-research` / `youtube-publish` | YouTube 调研(Data API v3)/ 发评论与回复 |
| `bili-research` | B 站创作者数据调研 |
| `xhs-research` | 小红书调研 |

发布类 skill 一律 **默认 dry-run**,必须显式加 `--send` 才真发。凭据走各自的 `.secrets/` 或 `*.example` 约定,不进 git。

> 📚 社媒这套工具的完整项目上下文(背景 / 架构 / 决策 / 踩坑台账 / 上手指南)见 [docs/README.md](docs/README.md)。
>
> ⚠️ `x-research` / `x-publish` / `xhs-research` 依赖 Quriov 自有的服务器环境与登录态,**外部使用者装了也跑不通** —— 请当参考实现看。

## 迁移说明

本仓原名 `ai-dev-toolkit`,已改名 `Quriov-Skills`(GitHub 会自动重定向旧链接)。

以下两个独立仓的内容已并入本仓并归档,不再单独维护:

| 旧仓 | 现在在哪 |
|---|---|
| `Qin-C/claude-handoff-skill` | `skills/handoff` |
| `Qin-C/deep-intent-analysis` | `skills/deep-intent-analysis` |

同时移除了早已过时的 `rules/` `hooks/` `commands/` `install.sh`(内容仍在 git history 里)。
skill 分发不再用 `install.sh` 人肉复制,统一走上面的 `npx skills`。

## License

MIT
