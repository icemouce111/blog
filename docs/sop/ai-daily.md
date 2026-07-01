# AI Daily 运行与发布 SOP

## 目标

AI Daily 使用同一条 Python 命令完成数据采集、自动质量控制、日报生成、
Git 发布和 Cloudflare Pages 线上验证。发布过程始终基于最新
`origin/main` 的临时 worktree，不继承当前开发分支的提交或未提交文件。

## 环境要求

- Python 3.10 或更高版本。
- Git，且 `origin` 已配置 `main` 分支写权限。
- 安装 `scripts/requirements.txt` 中的 Python 依赖。
- 运行目录必须是 blog 仓库根目录。
- Cloudflare Pages 继续监听 GitHub `main`，本仓库不增加第二个定时任务。

macOS/Linux：

```bash
python3 -m pip install -r scripts/requirements.txt
python3 scripts/generate-ai-daily.py
```

Windows PowerShell：

```powershell
py -3 -m pip install -r scripts/requirements.txt
py -3 scripts/generate-ai-daily.py
```

CI 使用相同入口。CI 应在运行前完成 Git 凭证配置，并把浅克隆改为完整或
至少包含 `origin/main` 的克隆。

## 命令

完整生成、发布和线上验证：

```bash
python3 scripts/generate-ai-daily.py
```

只生成文件，不执行 Git 操作：

```bash
python3 scripts/generate-ai-daily.py --generate-only
```

只演练采集、分析和质量控制，不写文件：

```bash
python3 scripts/generate-ai-daily.py --dry-run
```

补发或重建指定日期：

```bash
python3 scripts/generate-ai-daily.py --date 2026-07-01 --force
```

`--dry-run` 不发布；`--generate-only` 不发布；默认模式不在当前 checkout
中生成内容，而是在临时 `origin/main` worktree 中调用 `--generate-only`。

## 数据源与凭证

| 来源 | 首选方式 | 降级方式 | 环境变量 |
| --- | --- | --- | --- |
| OpenAI | 官方 RSS | 无 | 无 |
| Anthropic | 官方 Newsroom + Sitemap | 无 | 无 |
| Linux.do | Discourse RSS | `bb-browser linuxdo/latest` | 无 |
| Reddit | 公共 JSON | `bb-browser reddit/hot` | 无 |
| X | 官方 recent search API | `bb-browser twitter/search` | `X_BEARER_TOKEN` |
| 小红书 | 本地登录态 MCP | `bb-browser xiaohongshu/search` | `XIAOHONGSHU_API_BASE` |
| 其他既有来源 | 现有 HTTP 或 `bb-browser` 采集器 | 跳过 | 视来源而定 |

LLM 使用 `DEEPSEEK_API_KEY`，未设置时回退到 `OPENAI_API_KEY`。
密钥可放在进程环境或本机 `scripts/.env`，不得提交到 Git。

小红书 MCP 默认不自动假设地址；只有设置 `XIAOHONGSHU_API_BASE` 后才启用。
浏览器来源不可用时标记为 `skipped` 或 `degraded`，不会阻止官方和公共来源生成日报。

## 自动质量控制

发布前自动执行以下检查：

1. 删除空标题、无效 URL、明显过期和未来日期数据。
2. 对规范化 URL 去重。
3. 报告引用的 URL 必须出现在本次采集证据中。
4. 社区消息必须使用“据社区讨论”“有用户/开发者指出”等归因措辞。
5. 无证据支持的“最快”“第一”“唯一”“明确蓝海”等表述不允许通过。
6. 首次检查失败时调用 LLM 修复一次。
7. 修复仍失败或 LLM 不可用时，自动生成只包含真实来源链接的原始信号归档。

没有人工审批步骤。只有所有核心来源都没有可用数据，或最终 Markdown
无法形成编号栏目时，生成流程才返回非零状态。

## 发布过程

1. 在系统临时目录获取原子锁；六小时以上的锁视为陈旧锁。
2. `git fetch origin main --prune`。
3. 从 `origin/main` 创建 detached 临时 worktree。
4. 在临时 worktree 中运行 `--generate-only`。
5. 拒绝日报、RSS、趋势 JSON 之外的任何文件变化。
6. 只暂存：
   - `src/content/ai-daily/YYYY-MM-DD.md`
   - `public/ai-daily.xml`
   - `src/data/ai-trends.json`
7. 提交并执行非强制 `git push origin HEAD:main`。
8. 非快进失败时，从新的 `origin/main` 完整重试一次。
9. 使用 `git ls-remote` 验证远端 SHA。
10. 轮询 `https://blog.icemouce.cc/ai-daily.xml`，确认目标日期已上线。
11. 在 `finally` 中移除临时 worktree 和锁。

报告已存在时，流程仍会验证远端报告、RSS 和线上状态，不会把
`Everything up-to-date` 当成未经验证的成功。

## 故障处理

- `another AI Daily run is active`：等待现有任务完成；超过六小时会自动回收锁。
- `All core sources returned no usable data`：检查网络、DNS 和官方源状态，不要强制发布空日报。
- `generator changed unexpected files`：检查生成器是否产生了计划外文件，发布器会在推送前停止。
- `git push ... rejected`：系统自动重试一次；再次失败说明 `main` 仍在并发变化或权限异常。
- `remote push succeeded but live RSS does not contain`：GitHub 已更新但 Cloudflare 未完成部署；重跑默认命令会继续验证，不会重复合并开发分支。
- 浏览器来源失败：先运行 `bb-browser daemon status`，必要时登录对应网站；这些来源是可选项。

## 验证

```bash
npm test
npm run build
python3 -m compileall -q scripts
```

Python 行为测试使用固定响应和本地 bare Git 仓库，不调用外部 LLM、GitHub
或 Cloudflare。真实发布完成后还必须确认远端 `main` SHA、线上 RSS 和日报页面。
