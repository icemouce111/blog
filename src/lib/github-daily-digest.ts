import type { GithubDailyHighlight, GithubDailyRecord, GithubDailyRepo } from './github-daily'

export interface GithubDigestPick {
  repo: string
  title?: string
  value: string
  how?: string
}

type GithubDigestRecord = Pick<GithubDailyRecord, 'mode' | 'highlights' | 'repos'>

function hasCompleteHighlights(highlights: GithubDailyHighlight[]) {
  return highlights.length > 0 && highlights.every((highlight) => (
    Boolean(highlight.repo && highlight.title && highlight.value && highlight.how)
  ))
}

export function hasAnalyzedGithubDigest(post: GithubDigestRecord): boolean {
  return post.mode === 'analyzed' && hasCompleteHighlights(post.highlights)
}

export function getGithubDigestLabel(post: GithubDigestRecord): string {
  return hasAnalyzedGithubDigest(post) ? '开源精选' : '热门项目'
}

function toHighlightPick(highlight: GithubDailyHighlight): GithubDigestPick {
  return {
    repo: highlight.repo,
    title: highlight.title,
    value: highlight.value,
    how: highlight.how,
  }
}

function toFallbackPick(repo: GithubDailyRepo): GithubDigestPick {
  return {
    repo: repo.fullName,
    value: repo.what || repo.description || '项目暂未提供介绍。',
  }
}

export function getGithubDigestPicks(post: GithubDigestRecord): GithubDigestPick[] {
  if (hasAnalyzedGithubDigest(post)) {
    return post.highlights.slice(0, 3).map(toHighlightPick)
  }

  return post.repos.slice(0, 3).map(toFallbackPick)
}
