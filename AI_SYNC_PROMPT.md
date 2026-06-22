# 学山博客 · AI 平台同步提示词

将此内容发送给 Cursor / Codex / GitHub Copilot / 其他 AI 编码工具：

---

<SYNC_PROMPT>

## 项目背景

这是 icemouce 的个人博客项目，已部署在 Cloudflare Pages，域名 https://blog.icemouce.cc。GitHub 仓库：https://github.com/icemouce111/blog。

## 技术栈（重要，不要改）

- React 19 + TypeScript 6 + Vite 8
- Tailwind CSS 4 + shadcn/ui v4（基于 @base-ui/react，不是旧版 radix-ui）
- React Router v7
- Zustand 5（主题状态）
- react-markdown + remark-gfm
- 自写 frontmatter 解析器（不要引入 gray-matter，它依赖 Node.js Buffer，浏览器不支持）
- Cloudflare Pages 部署

## shadcn/ui v4 关键用法（和旧版不同）

```tsx
// ❌ 旧版 asChild（不存在了）
<Button asChild><Link to="/blog">文字</Link></Button>

// ✅ 新版 render 属性
<Button variant="ghost" render={<Link to="/blog" />}>文字</Button>
<SheetTrigger render={<Button variant="ghost" size="icon" />}>
```

## 文件结构

```
src/
├── components/
│   ├── ui/          # shadcn/ui 组件（不要手动改，用 npx shadcn@latest add）
│   ├── layout/      # Navbar, Footer, Layout, PageContainer, constants
│   └── blog/        # GiscusComments
├── pages/           # 页面组件
│   ├── HomePage.tsx
│   ├── BlogPage.tsx, BlogPostPage.tsx
│   ├── AiDailyPage.tsx, AiDailyPostPage.tsx  ← AI日报
│   ├── ProjectsPage.tsx
│   ├── ResourcesPage.tsx
│   └── AboutPage.tsx
├── lib/
│   ├── posts.ts     # 博客文章数据加载
│   ├── ai-daily.ts  # AI日报数据加载
│   └── utils.ts     # cn() 工具函数
├── store/theme.ts   # Zustand 主题
├── hooks/useTheme.ts
├── data/            # JSON 数据文件
│   ├── projects.json
│   ├── resources.json
│   └── friends.json
├── content/
│   ├── blog/        # 博客 .md 文件
│   └── ai-daily/    # AI日报 .md 文件
├── App.tsx          # 路由配置
└── index.css        # Tailwind + 全局样式
```

## Markdown 文件格式

博客文章（`src/content/blog/`）和 AI 日报（`src/content/ai-daily/`）使用相同的 frontmatter 格式：

```yaml
---
title: 文章标题
date: 2026-06-22
description: 一句话摘要
tags:
  - 标签1
  - 标签2
---
正文内容...
```

## ⚠️ Git 操作规则（极其重要）

**每次编辑代码前，必须先执行：**
```bash
git pull origin main
```

**编辑完成后立即执行：**
```bash
git add . && git commit -m "描述改动" && git push
```

**绝对禁止：**
- 不要 git push -f（强制推送）
- 不要修改 tsconfig 或 vite.config 除非明确知道在做什么
- 不要引入 gray-matter 或其他 Node.js 专属库
- 不要改 shadcn/ui 组件目录（src/components/ui/）
- 修改任何文件前先 git pull，避免冲突

## 当前已知问题

- AI 日报目录（src/content/ai-daily/）刚创建，还没有日报文件
- BlogPostPage 的 TOC 已移到左侧
- 不要改暗色模式相关代码（工作正常）

</SYNC_PROMPT>
