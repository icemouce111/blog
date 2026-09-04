import assert from 'node:assert/strict'
import test from 'node:test'

import {
  getGithubDigestLabel,
  getGithubDigestPicks,
  hasAnalyzedGithubDigest,
} from '../src/lib/github-daily-digest.ts'

const repo = {
  rank: 1,
  fullName: 'fmtlib/fmt',
  url: 'https://github.com/fmtlib/fmt',
  description: 'A modern formatting library',
  language: 'C++',
  stars: 24770,
  starsToday: 955,
  forks: 3001,
  topics: [],
  what: 'A modern formatting library',
  help: '',
}

test('fallback GitHub digest renders repository introductions without synthetic steps', () => {
  const post = {
    mode: 'fallback' as const,
    repos: [repo],
    highlights: [],
  }

  assert.equal(hasAnalyzedGithubDigest(post), false)
  assert.equal(getGithubDigestLabel(post), '热门项目')
  assert.deepEqual(getGithubDigestPicks(post), [{
    repo: 'fmtlib/fmt',
    value: 'A modern formatting library',
  }])
})

test('analyzed GitHub digest retains curated titles and first steps', () => {
  const post = {
    mode: 'analyzed' as const,
    repos: [repo],
    highlights: [{
      repo: 'fmtlib/fmt',
      title: '更清晰的 C++ 格式化',
      why: '成熟稳定',
      value: '让输出代码更简洁。',
      how: '从 README 的基础用法开始。',
    }],
  }

  assert.equal(hasAnalyzedGithubDigest(post), true)
  assert.equal(getGithubDigestLabel(post), '开源精选')
  assert.deepEqual(getGithubDigestPicks(post), [{
    repo: 'fmtlib/fmt',
    title: '更清晰的 C++ 格式化',
    value: '让输出代码更简洁。',
    how: '从 README 的基础用法开始。',
  }])
})
