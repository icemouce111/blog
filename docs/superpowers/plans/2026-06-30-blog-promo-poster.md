# 博客朋友圈宣传海报实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 生成一张包含准确博客信息和可扫描二维码的 1080 × 1440 极简朋友圈海报。

**Architecture:** 先确定性生成指向博客首页的二维码，再将博客头像与二维码作为受约束参考输入交给内置图像生成工具。最终海报遵循已确认的暖白、黑字、大留白杂志广告方向。

**Tech Stack:** Node.js QRCode CLI、内置 Image Generation、PNG

---

### Task 1: 生成二维码参考图

**Files:**
- Create: `output/imagegen/blog-qr.png`

- [ ] **Step 1: 创建输出目录**

Run: `mkdir -p output/imagegen`

Expected: `output/imagegen/` 存在。

- [ ] **Step 2: 生成高对比度二维码**

Run:

```bash
npx --yes qrcode@1.5.4 \
  --output output/imagegen/blog-qr.png \
  --width 512 \
  --margin 4 \
  --error-correction-level H \
  'https://blog.icemouce.cc'
```

Expected: 生成 512 × 512 PNG，内容指向 `https://blog.icemouce.cc`。

- [ ] **Step 3: 检查二维码文件**

Run: `file output/imagegen/blog-qr.png`

Expected: 输出包含 `PNG image data, 512 x 512`。

### Task 2: 生成极简海报

**Files:**
- Read: `public/avatar.jpg`
- Read: `output/imagegen/blog-qr.png`
- Create: 内置图像生成工具返回的 1080 × 1440 竖版 PNG

- [ ] **Step 1: 将头像和二维码作为参考输入生成成品**

使用内置图像生成工具，并传入 `public/avatar.jpg` 与 `output/imagegen/blog-qr.png`。提示词如下：

```text
Use case: ads-marketing
Asset type: vertical WeChat Moments promotional poster, 3:4 portrait
Primary request: Create a refined minimalist editorial poster for the personal technology blog icemouce.
Input images:
- Image 1 is the exact profile avatar; reproduce it as a small crisp circular portrait near the upper-left.
- Image 2 is the exact functional QR code; place it pixel-faithfully in the lower-right with an untouched white quiet zone. It must remain scannable and must not be redrawn, stylized, warped, cropped, blurred, recolored, or decorated.
Scene/backdrop: warm off-white uncoated paper with extremely subtle natural paper grain.
Style/medium: Swiss-inspired independent magazine advertisement, restrained contemporary typography, generous negative space, premium editorial art direction.
Composition/framing: 1080 × 1440 portrait. Small avatar and ICEMOUCE at top. Thin black divider. Large headline centered vertically-left. Supporting copy and three small outlined pill labels below. Bottom information rail contains the URL on the left and QR code on the right.
Color palette: warm white, near-black, muted gray; one tiny yellow accent sampled from the avatar.
Text (verbatim):
"ICEMOUCE"
"把好奇心写成答案。"
"个人博客 · AI 日报 · 开源作品集"
"持续记录技术、工具与思考。"
"AI DAILY"
"FULL STACK"
"OPEN SOURCE"
"blog.icemouce.cc"
"扫码访问"
Constraints: every quoted text string must be spelled exactly; preserve Chinese punctuation; maintain strong black-on-white contrast around the QR code; no extra copy.
Avoid: fake UI, mockup frame, phone frame, decorative QR patterns, gradients, neon, 3D objects, excessive illustration, watermark, additional logos, misspelled text.
```

- [ ] **Step 2: 视觉验收**

确认成品满足以下条件：

- 竖版 3:4 构图，暖白底、黑字、大留白。
- 头像清晰且位于左上区域。
- 所有中文、英文标签和网址与提示词逐字一致。
- 二维码位于右下角，保持正方形和完整白色静区。
- 没有额外水印、伪网址或多余文字。
