import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'
import { createServer } from 'vite'
import type { PostMeta } from '../src/lib/posts.ts'

test('阅读入口和系列导航只链接现有文章，文章按原始日期倒序排列', async () => {
  const server = await createServer({
    configFile: false,
    server: { middlewareMode: true, ws: false, hmr: false, watch: null },
    optimizeDeps: { noDiscovery: true },
  })
  try {
    const { getPosts, getPost } = await server.ssrLoadModule('/src/lib/posts.ts')
    const posts: PostMeta[] = getPosts()
    const guides: { label: string; slugs: string[] }[] = JSON.parse(
      await readFile(new URL('../src/data/blog-guides.json', import.meta.url), 'utf8'),
    )

    for (const guide of guides) {
      assert.ok(guide.slugs.length > 0, `${guide.label} 需要有阅读入口`)
      assert.equal(new Set(guide.slugs).size, guide.slugs.length)
      for (const slug of guide.slugs) {
        assert.ok(posts.some((post) => post.slug === slug), `${slug} 必须存在于文章列表`)
        assert.equal(getPost(slug)?.slug, slug)
      }
    }

    const dates = posts.map((post) => post.dateISO)
    assert.ok(new Set(dates).size > 1, '用不同日期的文章验证排序')
    assert.deepEqual(dates, [...dates].sort().reverse())
    assert.equal(posts.at(-1)?.slug, 'hello-world')
    for (const post of posts) {
      assert.match(post.dateISO, /^\d{4}-\d{2}-\d{2}$/)
      assert.equal(getPost(post.slug)?.dateISO, post.dateISO)
    }
  } finally {
    await server.close()
  }
})
