import assert from 'node:assert/strict'
import test from 'node:test'

import {
  getGithubDigestLabel,
  getGithubDailyStarRanking,
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
  how: '',
}

test('GitHub leaderboard ranks by daily Star growth instead of source order', () => {
  const post = {
    repos: [
      repo,
      {
        ...repo,
        rank: 2,
        fullName: 'owner/fast-growing',
        starsToday: 2138,
      },
      {
        ...repo,
        rank: 3,
        fullName: 'owner/no-daily-data',
        starsToday: null,
      },
    ],
  }

  assert.equal(getGithubDigestLabel(post), '每日新增 Star 排行')
  assert.deepEqual(
    getGithubDailyStarRanking(post).map((item) => item.fullName),
    ['owner/fast-growing', 'fmtlib/fmt', 'owner/no-daily-data'],
  )
})

test('daily Star leaderboard breaks equal-growth ties by repository name', () => {
  const post = {
    repos: [
      { ...repo, fullName: 'zeta/tool', starsToday: 100 },
      { ...repo, fullName: 'alpha/tool', starsToday: 100 },
    ],
  }

  assert.deepEqual(
    getGithubDailyStarRanking(post).map((item) => item.fullName),
    ['alpha/tool', 'zeta/tool'],
  )
})
