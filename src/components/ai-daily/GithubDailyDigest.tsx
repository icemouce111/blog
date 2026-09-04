import type { GithubDailyPost } from '@/lib/github-daily'
import { formatStars } from '@/lib/github-daily'
import {
  getGithubDigestLabel,
  getGithubDigestPicks,
  hasAnalyzedGithubDigest,
} from '@/lib/github-daily-digest'

interface GithubDailyDigestProps {
  post: GithubDailyPost
  variant?: 'index' | 'issue'
  id?: string
  number?: string
}

function DigestBody({ post, showBoard }: { post: GithubDailyPost; showBoard: boolean }) {
  const picks = getGithubDigestPicks(post)

  return (
    <>
      <p className="ai-github-intro">{post.intro}</p>
      <ol className="ai-github-picks">
        {picks.map((pick, index) => {
          const repo = post.repos.find((item) => item.fullName === pick.repo)
          return (
            <li key={pick.repo}>
              <span className="ai-github-rank">{String(index + 1).padStart(2, '0')}</span>
              <div>
                <p className="ai-github-repo-meta">
                  <a href={repo?.url ?? `https://github.com/${pick.repo}`} target="_blank" rel="noreferrer">
                    {pick.repo}
                  </a>
                  {repo?.language && <span>{repo.language}</span>}
                  {repo?.starsToday !== null && repo?.starsToday !== undefined && (
                    <span>今日 +{repo.starsToday}</span>
                  )}
                </p>
                {pick.title && <h3 className="ai-daily-serif">{pick.title}</h3>}
                <p>{pick.value}</p>
                {pick.how && <p className="ai-github-first-step">第一步：{pick.how}</p>}
              </div>
            </li>
          )
        })}
      </ol>

      {showBoard && (
        <details className="ai-github-board">
          <summary>展开完整榜单（{post.repos.length} 个项目）</summary>
          <ol>
            {post.repos.map((repo) => (
              <li key={repo.fullName}>
                <span>{repo.rank}</span>
                <div>
                  <a href={repo.url} target="_blank" rel="noreferrer">{repo.fullName}</a>
                  <p>{repo.what || repo.description}</p>
                </div>
                <small>★ {formatStars(repo.stars)}</small>
              </li>
            ))}
          </ol>
        </details>
      )}
    </>
  )
}

export function GithubDailyDigest({
  post,
  variant = 'index',
  id = 'github-picks',
  number = '08',
}: GithubDailyDigestProps) {
  const isAnalyzedDigest = hasAnalyzedGithubDigest(post)
  const digestLabel = getGithubDigestLabel(post)

  if (variant === 'issue') {
    return (
      <section
        className="ai-daily-content-section ai-daily-supplement ai-github-section"
        id={id}
        aria-labelledby={`${id}-heading`}
      >
        <div className="ai-daily-content-heading">
          <span>{number}</span>
          <h2 id={`${id}-heading`} className="ai-daily-serif">
            GitHub {digestLabel}
          </h2>
        </div>
        <p className="ai-daily-section-intro">
          {isAnalyzedDigest
            ? `${post.dateDisplay} · 不复述整张热榜，优先挑 Agent 工程、真实项目和教程创作能用上的工具。`
            : `${post.dateDisplay} · AI 解读暂缺，展示今日榜单前三个项目。`}
        </p>
        <DigestBody post={post} showBoard />
      </section>
    )
  }

  return (
    <section className="ai-github-digest" id={id} aria-labelledby={`${id}-heading`}>
      <header>
        <div>
          <p className="ai-daily-eyebrow">OPEN SOURCE PICKS</p>
          <h2 id={`${id}-heading`} className="ai-daily-serif">
            {isAnalyzedDigest ? '今天值得看的 3 个开源项目' : '今日热门开源项目'}
          </h2>
        </div>
        <time dateTime={post.date}>{post.date.slice(5).replace('-', '.')}</time>
      </header>
      <DigestBody post={post} showBoard={false} />
    </section>
  )
}
