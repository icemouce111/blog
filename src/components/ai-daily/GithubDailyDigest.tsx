import type { GithubDailyPost } from '@/lib/github-daily'
import { formatStars } from '@/lib/github-daily'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet'
import {
  getGithubDigestLabel,
  getGithubDigestPicks,
  hasAnalyzedGithubDigest,
} from '@/lib/github-daily-digest'
import { ExternalLink, Info, Star } from 'lucide-react'

interface GithubDailyDigestProps {
  post: GithubDailyPost
  variant?: 'index' | 'issue'
  id?: string
  number?: string
}

function GithubRepoQuickView({
  post,
  repo,
  value,
  how,
}: {
  post: GithubDailyPost
  repo: GithubDailyPost['repos'][number]
  value: string
  how?: string
}) {
  const isAnalyzedDigest = hasAnalyzedGithubDigest(post)
  const introduction = repo.what || repo.description || value

  return (
    <Sheet>
      <SheetTrigger className="ai-github-quick-view">
        <Info aria-hidden="true" /> 项目速览
      </SheetTrigger>
      <SheetContent className="ai-github-sheet" side="right">
        <SheetHeader className="ai-github-sheet-header">
          <p className="ai-github-sheet-kicker">GITHUB PROJECT</p>
          <SheetTitle>{repo.fullName}</SheetTitle>
          <SheetDescription>
            {repo.language || '未标注语言'} · 今日 +{repo.starsToday ?? '—'}
          </SheetDescription>
        </SheetHeader>

        <div className="ai-github-sheet-body">
          <section>
            <h3>项目介绍</h3>
            <p>{introduction}</p>
          </section>

          {repo.help && (
            <section>
              <h3>适合谁</h3>
              <p>{repo.help}</p>
            </section>
          )}

          {isAnalyzedDigest && how && (
            <section>
              <h3>建议从这里开始</h3>
              <p>{how}</p>
            </section>
          )}

          {!isAnalyzedDigest && (
            <section className="ai-github-sheet-source-note">
              <h3>资料状态</h3>
              <p>本期 AI 解读暂缺，项目介绍来自 GitHub 仓库原始说明。</p>
            </section>
          )}

          <dl className="ai-github-sheet-stats">
            <div>
              <dt><Star aria-hidden="true" /> Stars</dt>
              <dd>{formatStars(repo.stars)}</dd>
            </div>
            <div>
              <dt>Forks</dt>
              <dd>{formatStars(repo.forks)}</dd>
            </div>
          </dl>
        </div>

        <div className="ai-github-sheet-footer">
          <a href={repo.url} target="_blank" rel="noreferrer">
            在 GitHub 查看项目 <ExternalLink aria-hidden="true" />
          </a>
        </div>
      </SheetContent>
    </Sheet>
  )
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
                <p className="ai-github-pick-intro">{pick.value}</p>
                {pick.how && <p className="ai-github-first-step">第一步：{pick.how}</p>}
                {repo && (
                  <GithubRepoQuickView
                    post={post}
                    repo={repo}
                    value={pick.value}
                    how={pick.how}
                  />
                )}
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
