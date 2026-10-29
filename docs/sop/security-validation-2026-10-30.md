# 安全防护验收记录：2026-10-30

执行从 2026-10-29 持续至 2026-10-30，日期均按 Asia/Shanghai。

## 交付状态

| 项目 | 代码/配置状态 | 验证结果 |
| --- | --- | --- |
| 私密配置忽略规则、0600 权限、统一加载 | 已实现，本机已安装 | 暂存真实配置拒绝；示例允许；进程环境优先 |
| Gitleaks 8.30.1 和已知密钥匹配 | 已实现并安装 | 本地全部可用历史、当前文件、暂存区及 dist 扫描通过 |
| 防扫描自豁免 | 已实现 | 文章内 `gitleaks:allow` 无法放行；目标配置和环境变量不能削弱扫描 |
| 日志与错误脱敏 | 已实现 | 合成密钥、Bearer、认证 URL 和 token 查询参数均有测试 |
| GitHub CI、主分支保护 | 已上线并回读确认 | `security`、`tests`、`build` 绑定 GitHub Actions；管理员受保护；禁止强推和删除 |
| 自动日报 PR | 已上线 | PR #13 只修改单日 JSON，通过三项检查后自动合并，无直推 main |
| 依赖安全 | 已更新，安全更新已开启 | npm 全量及生产依赖审计均为 0 项；保留原静态样式和其第三方许可 |
| CSP、禁止嵌入等响应头 | 已部署 | 首页、日报与 RSS 返回 CSP；X-Frame-Options 为 DENY |
| 敏感路径阻断 | Cloudflare 活动规则 | `/.env`、`/.git/config` 返回 403；正常文章、RSS、`.well-known` 路径未被阻断 |
| 文章限流 | Cloudflare 活动规则 | 博客 hostname + 文章路径 + 排除 verified bots；100 次/10 秒，阻断 10 秒；效果待真实命中验证 |
| 预览访问保护 | Cloudflare Access 已启用 | 匿名预览请求转入 Access 登录；正式站和 RSS 保持公开 |
| 生产默认域名收敛 | 账号级批量重定向已启用 | pages.dev 访问返回 301；路径和查询参数完整保留 |

## 实际验证证据

- 安全实现：[PR #4](https://github.com/icemouce111/blog/pull/4)，合并提交 `2fd74463c5c9c2eab8ed9244ece46594fbcf169e`。含密钥防护、PR 发布和依赖修复。
- 真实日报：[PR #13](https://github.com/icemouce111/blog/pull/13)，合并提交 `6d51fca54e921f6b9b9e48df548a3fb636e73911`。仅修改 `src/data/github-daily/2026-10-29.json`，记录模式为 `analyzed`，包含 11 个项目。
- [线上日报](https://blog.icemouce.cc/github/2026-10-29) 返回 200，并带 CSP。
- 在隔离 checkout 运行 14 项 TypeScript、118 项 Python 测试，全部通过；构建及产物扫描通过。其后的 PR #4、#13 服务器端必需检查也均通过。
- `https://blog-9is.pages.dev/ai-daily?security_probe=1` 返回 `301`，Location 为 `https://blog.icemouce.cc/ai-daily?security_probe=1`。
- 仅进行了低流量 GET/HEAD 验证，没有对生产站进行阈值压测。控制台截图保存在本机忽略目录，不上传账号界面或凭证至公开仓库。

页面资源核对发现既有 Cloudflare Web Analytics beacon。CSP 对 `static.cloudflareinsights.com` 的脚本和 `cloudflareinsights.com` 的统计连接保留精确许可，避免拦截既有功能；不允许任意脚本来源。参考 [Cloudflare CSP 要求](https://developers.cloudflare.com/fundamentals/reference/policies-compliances/content-security-policies/)。

## 剩余风险与维护边界

1. 限流已配置，但尚无真实触发证据；不能宣称已验证拦截效率。首次误拦应调整或撤回对应边缘规则，保留主分支和密钥门禁。
2. 公开 GitHub 内容和前端包仍可复制，低频镜像无法完全阻止。没有新增公开 AI 接口，也没有把域名判断当作认证。
3. 发布器仍使用当前 gh 登录身份。程序不使用管理员绕过，但外部凭证自身的授权范围需要账号维护者另行确认；模型平台的专用密钥、消费上限和告警也由平台设置决定。
4. 当前扫描不是完整隐私审计：截图、二维码、图片元数据、客户材料、第三方素材和 Fork 缓存需另行核对。无需为本次扫描结果自动重写公共历史。
5. 不改项目整体许可证。保留的静态 shadcn 样式附带原有第三方 MIT 声明，不代表为整个项目选择了 MIT。
6. 计划于 2026-11-06 人工复核发布失败、依赖告警、边缘拦截和正常访问；本次未新增日报调度或其他后台定时任务。

## 回滚

代码回滚仍经 PR 和三项检查。边缘规则通过 Cloudflare 控制台按规则名停用或恢复，不回退到全站验证码或影响其他业务的宽泛规则。凭证一旦泄漏，先撤销/换新，再处理历史与旧部署；不能以回滚代码代替撤销凭证。
