import type { GithubDailyRecord, GithubDailyRepo } from './github-daily'

type GithubDailyRankingRecord = Pick<GithubDailyRecord, 'repos'>

/**
 * GitHub Trending supplies a daily star delta for each repository. Its source
 * order is not guaranteed to be a strict delta ranking, so rank it ourselves.
 */
export function getGithubDailyStarRanking(
  post: GithubDailyRankingRecord,
): GithubDailyRepo[] {
  return [...post.repos].sort((left, right) => {
    const leftStars = left.starsToday ?? -1
    const rightStars = right.starsToday ?? -1

    if (rightStars !== leftStars) return rightStars - leftStars
    return left.fullName.localeCompare(right.fullName)
  })
}

export function getGithubDigestLabel(_post: GithubDailyRankingRecord): string {
  return '每日新增 Star 排行'
}
