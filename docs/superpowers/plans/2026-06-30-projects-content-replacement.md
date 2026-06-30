# 作品集内容替换实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用 browser-smart Skill 和接触网缺陷复核 Demo 替换作品集中的个人博客卡片。

**Architecture:** 保留 `ProjectsPage` 现有的数据驱动卡片渲染，只更新 `src/data/projects.json`。增加一项数据契约测试，固定项目数量、名称、仓库地址和无独立演示按钮的要求。

**Tech Stack:** JSON、Node.js Test Runner、TypeScript、React、Vite

---

### Task 1: 固定作品集数据契约

**Files:**
- Create: `tests/projects-data.test.ts`
- Test: `tests/projects-data.test.ts`

- [x] **Step 1: 编写失败测试**

```ts
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

interface Project {
  name: string
  description: string
  tags: string[]
  github?: string
  demo?: string
}

test('作品集只展示 browser-smart Skill 和接触网缺陷复核 Demo', async () => {
  const projectsUrl = new URL('../src/data/projects.json', import.meta.url)
  const projects = JSON.parse(await readFile(projectsUrl, 'utf8')) as Project[]

  assert.deepEqual(
    projects.map(({ name, github, demo }) => ({ name, github, demo })),
    [
      {
        name: 'browser-smart',
        github: 'https://github.com/icemouce111/browser-smart',
        demo: undefined,
      },
      {
        name: '接触网缺陷复核 Demo',
        github: 'https://github.com/icemouce111/catenary-defect-review-demo',
        demo: undefined,
      },
    ],
  )

  for (const project of projects) {
    assert.ok(project.description.length > 0)
    assert.ok(project.tags.length > 0)
  }
})
```

- [x] **Step 2: 运行测试并确认失败**

Run: `node --test --experimental-strip-types tests/projects-data.test.ts`

Expected: FAIL，因为当前数据仍只有“个人博客”项目。

### Task 2: 替换作品集数据

**Files:**
- Modify: `src/data/projects.json`
- Test: `tests/projects-data.test.ts`

- [x] **Step 1: 写入两个作品的数据**

```json
[
  {
    "name": "browser-smart",
    "description": "面向 Hermes Agent 的智能浏览器操控 Skill，可自动定位用户当前正在浏览的 Chrome 标签页",
    "tags": ["Hermes Agent", "浏览器自动化", "Chrome", "Shell", "agent-browser-cli"],
    "github": "https://github.com/icemouce111/browser-smart"
  },
  {
    "name": "接触网缺陷复核 Demo",
    "description": "面向接触网 AI 缺陷检测业务的复核环节 Demo，用于展示缺陷审阅界面与业务流程原型",
    "tags": ["AI 缺陷检测", "接触网", "业务原型", "UI Demo"],
    "github": "https://github.com/icemouce111/catenary-defect-review-demo"
  }
]
```

- [x] **Step 2: 运行数据测试**

Run: `node --test --experimental-strip-types tests/projects-data.test.ts`

Expected: PASS，输出 `tests 1`、`pass 1`、`fail 0`。

- [x] **Step 3: 运行完整构建**

Run: `npm run build`

Expected: TypeScript 检查和 Vite 构建成功完成。

- [x] **Step 4: 在浏览器中验证页面**

启动本地开发服务器并打开 `/projects`，确认：

- 桌面宽度下两张卡片并排显示，窄屏下纵向显示。
- 页面不再出现“个人博客”。
- 两张卡片均只有 GitHub 按钮，没有“演示”按钮。
- 两个 GitHub 按钮分别指向计划中的仓库地址。

- [x] **Step 5: 提交实现**

```bash
git add src/data/projects.json tests/projects-data.test.ts
git commit -m "feat: update portfolio projects"
```
