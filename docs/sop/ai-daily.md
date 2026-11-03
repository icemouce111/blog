# AI Daily 运行与发布 SOP

## 目标

AI Daily 使用同一条 Python 命令完成数据采集、自动质量控制、日报生成、
GitHub PR 发布和 Cloudflare Pages 线上验证。发布过程始终基于最新
`origin/main` 的临时 worktree，不继承当前开发分支的提交或未提交文件。

## 环境要求

- Python 3.10 或更高版本。
- Git 和已登录的 GitHub CLI；发布身份需要本仓库内容及 PR 写权限，无需绕过保护。
- 安装 `scripts/requirements.lock` 中的固定依赖及 Gitleaks 8.30.1。
- 运行目录必须是 blog 仓库根目录。
- Cloudflare Pages 继续监听 GitHub `main`，本仓库不增加第二个定时任务。

macOS/Linux：

```bash
python3 -m pip install --require-hashes -r scripts/requirements.lock
python3 scripts/install_gitleaks.py
python3 scripts/generate-ai-daily.py
```

Windows PowerShell：

```powershell
py -3 -m pip install --require-hashes -r scripts/requirements.lock
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

指定过去日期时，生成器启用历史模式：只接受发布日期可验证且等于目标日期的证据。
Hacker News、GitHub 和 Hugging Face Papers 使用按日查询；没有可回溯查询的实时
排行榜和社区来源会被明确跳过，绝不会把当天的榜单换上历史日期发布。

`--dry-run` 不发布；`--generate-only` 不发布；默认模式不在当前 checkout
中生成内容，而是在临时 `origin/main` worktree 中调用 `--generate-only`。

## 数据源与凭证

默认主流程启用官方、项目和经过限额的社区来源：OpenAI、Anthropic、GitHub Changelog、Cloudflare Blog、LangChain Blog、GitHub Trending、HuggingFace Papers、V2EX、Linux.do、Reddit、Stack Overflow、Medium AI、DEV Community、博客园、Google Trends、AI Creator Opportunities。

Hacker News、Product Hunt、X/Twitter、Follow Builders、YouTube、Bilibili、Zhihu 和小红书的适配器仍保留在代码中，但默认不进入日报主流程；重新启用前应先补充来源级过滤和测试。

| 来源 | 首选方式 | 信号类型 | 环境变量 |
| --- | --- | --- | --- |
| OpenAI | 官方 RSS | story | 无 |
| Anthropic | 官方 Newsroom + Sitemap | story | 无 |
| GitHub Changelog | 官方 RSS + 主题关键词 | story | 无 |
| Cloudflare Blog | 官方 RSS + AI 关键词 | story | 无 |
| LangChain Blog | 官方 RSS + Agent 关键词 | story | 无 |
| GitHub Trending | Trending HTML / GitHub API | story | `GITHUB_TOKEN`（可选） |
| HuggingFace Papers | Daily Papers API | story | 无 |
| Google Trends | `pytrends` | trend | 无 |
| V2EX | 热门主题 API | social | 无 |
| Linux.do | Discourse RSS / 浏览器降级 | social | 无 |
| Reddit | 公共 JSON / 浏览器降级 | social | 无 |
| Stack Overflow | Atom/RSS | social | 无 |
| Medium AI | Medium 标签 RSS | social | 无 |
| DEV Community | DEV 标签 RSS | social | 无 |
| 博客园 | Atom RSS | social | 无 |
| Google Trends | `pytrends` | trend | 无 |
| AI Creator Opportunities | 每日搜索发现、来源目录、官方规则复核、Agent 筛选 | opportunity | 使用同一 LLM 配置 |

LLM 使用 `DEEPSEEK_API_KEY`，未设置时回退到 `OPENAI_API_KEY`。
DeepSeek 使用官方端点 `https://api.deepseek.com/v1`，默认模型为
`deepseek-flash`；可用 `DEEPSEEK_MODEL` 覆盖。日报请求显式关闭思考模式，
保留既有最终正文的输出预算与超时。模型名及参数以
[DeepSeek 官方文档](https://api-docs.deepseek.com/zh-cn/)为准。
两个生成器都依次读取进程环境、`scripts/.env`、兼容文件 `scripts/dc-config.env`；已有值不会被覆盖。配置文件权限为 0600（POSIX），不得提交到 Git。安装及应急操作见 [安全 SOP](security.md)。

本机接入时只编辑被忽略的 `scripts/.env`，不要在聊天、示例文件、前端变量或
Cloudflare 构建中填写真实密钥：

```dotenv
DEEPSEEK_API_KEY=你的密钥
DEEPSEEK_MODEL=deepseek-flash
```

首次验证可运行 `python3 scripts/generate-ai-daily.py --dry-run`；会产生模型调用费用，
但不写文章或发布。正式运行仍使用上面的发布命令。

小红书 MCP 默认不自动假设地址；只有设置 `XIAOHONGSHU_API_BASE` 后才启用。
创作者机会按不足千粉、每周 5—10 小时、AI 内容制作与个人 IP 方向筛选。
每次当天日报生成前刷新；同日补救复用已完成的刷新，历史补档不抓未来活动。
公开规则不完整、核验超过 7 天、截止冲突或官方身份未确认的线索单独展示，
不进入正文的可参与推荐；高粉丝门槛与重制作任务留在“后续再看”。
完整来源、字段和故障处理见 [创作者机会 SOP](creator-opportunities.md)。
浏览器来源只作为 Linux.do、Reddit 等来源的降级路径；标记为 `skipped` 或 `degraded`，不能阻止官方来源生成日报。

## 自动质量控制

发布前自动执行以下检查：

1. **脚本固定**：来源白名单、URL、日期、条数配额、明显垃圾信息、规范化 URL 去重和证据边界。
2. **Agent 判断**：语义相关性、跨来源事件合并、重要性排序、栏目归类、解释和下一步动作。
3. 删除空标题、无效 URL、明显过期和未来日期数据。
4. 报告引用的 URL 必须出现在本次采集证据中；金额、单位、比例、绝对表述和来源归因只与该条引用的资料比较，不能借用整批材料中的其他文章。
5. 趋势信号只能写成趋势、搜索热度或后续观察；活动机会必须保留报名、截止、奖励或资格语义。
6. 无证据支持的“最快”“第一”“唯一”“明确蓝海”等表述不允许通过。
7. 首次检查失败时调用 LLM 修复一次；修复仍失败则只保留真实来源链接。
8. 编辑正文使用 `1. **标题**` 编号条目，事实段落都放在对应条目内；格式不合规先进入修复。通过固定检查后再进行一次批量逐条核验：核对主体、限制条件和语义，为每个引用提供可在该来源中定位的短摘录。摘录还要通过程序核对，不能只相信模型的 `supported` 字段。
9. 只有标题、没有有效摘要的条目先进入既有修复/删除流程；无法留下合格条目、核验响应缺项、摘录不存在、存在无新增内容的旧事件或核验接口失败时，自动降级为来源速览。每次生成最多增加一次批量核验调用，使用现有模型配置、关闭思考模式并限制输入、输出及超时。
10. 编辑版将逐条 URL、短摘录、原发及更新时间、材料哈希写入当期 Markdown 的 `evidence` frontmatter；不增加日报发布白名单之外的数据文件。正文哈希不匹配时，不信任旧核验记录。

没有人工审批步骤。所有核心来源抓取失败，或最终 Markdown
无法形成编号栏目时，生成流程才返回非零状态。

### 新鲜度与跨日重复

- 官方新闻与默认普通新闻候选窗口为目标日及此前两个自然日，日期统一按北京时间判断；未来日期不进入新闻。历史补档仍要求原发日期等于目标日，且不能使用目标日之后的修订内容。
- RSS/Atom 的 `updated` 单独保存，不再补成 `published_at`。原发时间未知的新闻不按新发布处理；榜单快照、搜索趋势和活动截止日期继续使用各自的时间语义。
- 读取已有日报作为持久历史，兼容编号、无编号粗体标题和来源速览：同一规范 URL 不重复刊登；同标题不同 URL 进入增量核验；语义核验还比较最近 40 条历史并补入明确命中的旧记录。历史补档不读取当日之后的日报，同日重跑不受自身记录干扰。
- 同 URL 的后续只在已有材料哈希、材料实际改变、存在更新日期时重新进入候选，且必须引用未刊登过的新事实摘录。旧归档缺少哈希时保守跳过同 URL；不会为旧文章批量重做模型调用。
- Stars、浏览数等独立热度字段不作为材料变化。每日榜单和趋势快照，以及机会栏目的既定刷新周期，不按普通新闻重复规则删除。
- 核心源正常响应但没有新条目时生成空期来源速览，不编造新闻，也不再次调用编辑模型；全部核心抓取失败仍报错。

语义核验使用现有模型，是额外的证据约束，不是独立事实裁判。程序能验证引用范围、摘录、数字和历史记录，但不能保证来源本身真实或模型语义判断零漏判。

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
   - `src/data/ai-opportunities.json`
7. 扫描待发布文件后提交至 `codex/ai-daily-YYYY-MM-DD` 分支，创建 PR；GitHub 日报使用 `codex/github-daily-YYYY-MM-DD`。
8. 等待 `security`、`tests`、`build` 全部成功，按已扫描 head SHA 请求自动 squash 合并；不使用管理员绕过。
9. 最多等待十分钟；超时、冲突、检查失败或 head 被替换时返回非零，并给出 PR 链接。重跑复用待合并 PR，不重新调用模型；待合并时不接受 `--force` 覆盖。
10. 拉取远端 `main`，验证合并提交是其祖先且目标文件存在。
11. 轮询正式站的构建指纹与目标页面，确认该期源文件 SHA-256、页面入口资源清单和实际 JS/CSS 字节都与同一构建一致；AI 日报额外解析 RSS，核对唯一的目标文章链接、标题和正文预览。GitHub 榜单同样验证线上构建，不能只凭远端 Git 提交成功结束。
12. 在 `finally` 中移除临时 worktree 和锁。

报告已存在时，流程仍会验证远端报告、RSS 和线上状态，不会把
`Everything up-to-date` 当成未经验证的成功。

`npm run build` 在 Vite 构建后生成 `dist/daily-publication.json`，其中仅包含已公开日报/榜单及入口资源的路径和哈希，随后进入现有产物安全扫描。该文件与站点一起部署，不新增调度或公开模型接口。上线新发布器前须先合入并部署包含此构建步骤的代码；缺少指纹或 CDN 仍提供旧资源时发布器等待，超时返回非零，重跑继续验收。

## 故障处理

- `another AI Daily run is active`：等待现有任务完成；超过六小时会自动回收锁。
- `All core sources returned no usable data`：检查网络、DNS 和官方源状态，不要强制发布空日报。
- `generator changed unexpected files`：检查生成器是否产生了计划外文件，发布器会在推送前停止。
- `git push ... rejected`：系统自动重试一次；再次失败说明 `main` 仍在并发变化或权限异常。
- `live content fingerprint/RSS verification failed`：GitHub 已更新但线上指纹、页面资源或 RSS 与目标内容不一致；先检查构建指纹是否生成及 Cloudflare 部署/缓存状态。重跑默认命令会继续验收，不会重复合并开发分支。
- 浏览器来源失败：先运行 `bb-browser daemon status`，必要时登录对应网站；这些来源是可选项。

## 验证

```bash
npm test
npm run build
python3 -m compileall -q scripts
```

Python 行为测试使用固定响应和本地 bare Git 仓库，不调用外部 LLM、GitHub
或 Cloudflare。真实发布完成后还必须确认远端 `main` SHA、线上 RSS 和日报页面。
