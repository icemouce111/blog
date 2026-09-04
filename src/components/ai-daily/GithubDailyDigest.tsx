import type { GithubDailyPost } from '@/lib/github-daily'
import {
  getGithubDigestLabel,
  getGithubDailyStarRanking,
} from '@/lib/github-daily-digest'
import { ExternalLink } from 'lucide-react'

interface GithubDailyDigestProps {
  post: GithubDailyPost
  variant?: 'index' | 'issue'
  id?: string
  number?: string
}

function DigestBody({ post }: { post: GithubDailyPost }) {
  const ranking = getGithubDailyStarRanking(post)

  return (
    <>
      <p className="ai-github-intro">
        按 GitHub Trending 上榜项目的当日新增 Star 排序；点击项目卡即可打开 GitHub。
      </p>
      <ol className="ai-github-picks">
        {ranking.map((repo, index) => {
          return (
            <li key={repo.fullName}>
              <a
                className="ai-github-project-card"
                href={repo.url}
                target="_blank"
                rel="noreferrer"
                aria-label={`在 GitHub 打开第 ${index + 1} 名项目：${repo.fullName}`}
              >
                <span className="ai-github-rank">{String(index + 1).padStart(2, '0')}</span>
                <div>
                  <p className="ai-github-repo-meta">
                    <span className="ai-github-repo-name">{repo.fullName}</span>
                    {repo.language && <span>{repo.language}</span>}
                    {repo.starsToday !== null && repo.starsToday !== undefined && (
                      <span>今日 +{repo.starsToday}</span>
                    )}
                    <ExternalLink className="ai-github-external-icon" aria-hidden="true" />
                  </p>
                  <dl className="ai-github-scan-list">
                    <div>
                      <dt>是什么</dt>
                      <dd>{repo.what || repo.description || '项目暂未提供介绍。'}</dd>
                    </div>
                    {repo.help && (
                      <div>
                        <dt>能干嘛</dt>
                        <dd>{repo.help}</dd>
                      </div>
                    )}
                    {repo.how && (
                      <div>
                        <dt>怎么用</dt>
                        <dd>{repo.how}</dd>
                      </div>
                    )}
                  </dl>
                </div>
              </a>
            </li>
          )
        })}
      </ol>
    </>
  )
}

export function GithubDailyDigest({
  post,
  variant = 'index',
  id = 'github-picks',
  number = '08',
}: GithubDailyDigestProps) {
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
          {post.dateDisplay} · 按 GitHub Trending 上榜项目的当日新增 Star 排序。
        </p>
        <DigestBody post={post} />
      </section>
    )
  }

  return (
    <section className="ai-github-digest" id={id} aria-labelledby={`${id}-heading`}>
      <header>
        <div>
          <p className="ai-daily-eyebrow">OPEN SOURCE PICKS</p>
          <h2 id={`${id}-heading`} className="ai-daily-serif">
            GitHub 每日新增 Star 排行
          </h2>
        </div>
        <time dateTime={post.date}>{post.date.slice(5).replace('-', '.')}</time>
      </header>
      <DigestBody post={post} />
    </section>
  )
}
