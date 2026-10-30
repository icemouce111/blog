import test from 'node:test'
import assert from 'node:assert/strict'
import {
  activeReadingSection,
  decodeReadingHash,
  getReadingSections,
} from '../src/lib/reading-navigation.ts'

test('directory keeps Chinese anchors and matches source lines for inline formatting', () => {
  assert.deepEqual(
    getReadingSections('## 开始阅读\n\n### **工具**与 [链接](https://example.com)\n'),
    [
      { id: '开始阅读', title: '开始阅读', level: 2, line: 1 },
      { id: '工具与-链接', title: '工具与 链接', level: 3, line: 3 },
    ],
  )
})
test('fenced headings and shorter nested fence markers do not enter directory', () => {
  assert.deepEqual(
    getReadingSections('````md\n## 示例\n```\n## 仍在示例\n````\n## 正文').map((s) => s.title),
    ['正文'],
  )
  assert.deepEqual(
    getReadingSections('~~~\n## 示例\n~~~\n## 正文').map((s) => s.title),
    ['正文'],
  )
})
test('duplicates and literal suffixed headings never share an id', () => {
  const sections = getReadingSections('## test\n## test\n## test-2\n## test\n## !!!')
  assert.equal(new Set(sections.map((s) => s.id)).size, 5)
  assert.equal(sections[0].id, 'test')
  assert.equal(sections[1].id, 'test-2')
})
test('directory strips closing markers but excludes h1 and indented code', () => {
  assert.deepEqual(getReadingSections('# 标题\n    ## 示例\n## 正文 ##\n'), [
    { id: '正文', title: '正文', level: 2, line: 3 },
  ])
})
test('shared links decode Chinese safely, including malformed user URLs', () => {
  assert.equal(decodeReadingHash('#%E6%AD%A3%E6%96%87'), '正文')
  assert.equal(decodeReadingHash('#creator-opportunities'), 'creator-opportunities')
  assert.equal(decodeReadingHash('#%broken'), '')
})
test('active heading remains selected through long gaps and at the start', () => {
  assert.equal(
    activeReadingSection(
      [
        { id: 'a', top: -900 },
        { id: 'b', top: 450 },
      ],
      128,
    ),
    'a',
  )
  assert.equal(
    activeReadingSection(
      [
        { id: 'a', top: -900 },
        { id: 'b', top: 127 },
      ],
      128,
    ),
    'b',
  )
  assert.equal(activeReadingSection([{ id: 'a', top: 900 }], 128), 'a')
  assert.equal(activeReadingSection([], 128), '')
})
