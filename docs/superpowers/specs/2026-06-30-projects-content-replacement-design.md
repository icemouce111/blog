# 作品集内容替换设计

## 目标

将作品集页面现有的“个人博客”项目替换为两个已发布作品：

1. `browser-smart`：面向 Hermes Agent 的浏览器操控 Skill。
2. `catenary-defect-review-demo`：接触网 AI 缺陷检测业务复核环节 Demo。

## 展示方案

沿用作品集现有的双列卡片布局和数据驱动实现，不调整页面组件或视觉样式。两张卡片均展示项目名称、简短中文说明、主题标签和 GitHub 按钮。

`browser-smart` 的说明突出智能追踪用户当前浏览标签页的能力，标签覆盖 Hermes Agent、浏览器自动化、Chrome、Shell 和 agent-browser-cli。

`catenary-defect-review-demo` 明确标注为 Demo，说明其用于展示接触网 AI 缺陷检测业务的复核界面与流程原型，避免将其描述为 Skill 或完整产品。

## 链接与交互

- `browser-smart` 的 GitHub 按钮指向 `https://github.com/icemouce111/browser-smart`。
- `catenary-defect-review-demo` 的 GitHub 按钮指向 `https://github.com/icemouce111/catenary-defect-review-demo`。
- 两个仓库当前均不配置独立演示地址，因此卡片不显示“演示”按钮。
- 外部链接继续在新标签页打开，并保留现有安全属性。

## 实现范围

仅修改 `src/data/projects.json`。现有 `ProjectsPage` 已支持多项目渲染、响应式单双列布局和可选演示链接，无需改动组件。

## 验证

- 运行项目构建，确认 JSON 数据与 TypeScript 类型兼容。
- 在本地浏览作品集页面，确认两张卡片在桌面端并排、窄屏下纵向排列。
- 检查项目名称、说明、标签和两个 GitHub 链接，确认不再显示“个人博客”或“演示”按钮。
