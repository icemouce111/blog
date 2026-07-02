# AI Daily Reliable Scheduling Design

## Goal

Publish one validated AI Daily report every day without depending on Codex
Desktop being open. When the MacBook is available, include sources that require
its browser login state. When it is unavailable, still publish from portable
official and public sources.

## Constraints

- The only local machine is a MacBook M4, normally opened for work around 10:00
  Asia/Shanghai.
- The MacBook must not be kept awake overnight or required to run with its lid
  closed.
- The existing command remains `python3 scripts/generate-ai-daily.py`.
- Cloudflare Pages continues to deploy from GitHub `main`.
- Human review does not block publication.
- Secrets, browser profiles, locks, temporary worktrees, and logs remain outside
  the repository.
- No Cloudflare R2 exchange layer or additional always-on hardware is required.

## Architecture

The system uses two independent schedulers with one idempotent publisher:

1. A macOS LaunchAgent starts the existing command at 10:10
   Asia/Shanghai. It can use `scripts/.env`, `bb-browser`, local MCP services,
   and authenticated browser profiles.
2. GitHub Actions starts the same command at 10:37. If the local run already
   published the report, this run only verifies the remote SHA, RSS, and page.
   If the local run did not publish, GitHub generates and publishes from
   portable sources.
3. GitHub Actions starts a second recovery run at 11:17. It is idempotent and
   closes over transient scheduler, API, network, or deployment failures.

The existing publisher remains the only Git mutation path. Every invocation
fetches `origin/main`, generates in a detached temporary worktree, stages only
the allowed report/RSS/trend artifacts, pushes non-force `HEAD:main`, retries
one non-fast-forward, and verifies the deployed result.

## Local Scheduling

The repository will contain a LaunchAgent template and installation commands.
The installed plist will live in `~/Library/LaunchAgents`, with:

- an explicit repository working directory;
- an explicit PATH containing Python, Git, Homebrew, and `bb-browser`;
- `StartCalendarInterval` for 10:10 local time;
- `RunAtLoad` through a small due-check wrapper, so logging in after 10:10 can
  start a missed local run when today's remote report is absent;
- stdout and stderr under `~/Library/Logs/ai-daily/`;
- no `KeepAlive`, forced wake, or sleep prevention.

The due-check wrapper exits successfully when it is before 10:00 or the remote
report already exists. Local source failures remain fail-soft and visible in
the run log.

## GitHub Actions Scheduling

The workflow will exist on the default branch and provide:

- scheduled runs at 10:37 and 11:17 with timezone `Asia/Shanghai`;
- `workflow_dispatch` inputs for an optional date and force flag;
- `permissions: contents: write`;
- a single concurrency group with `cancel-in-progress: false`;
- Python dependency installation from `scripts/requirements.txt`;
- Git identity setup for the generated commit;
- repository secrets for `DEEPSEEK_API_KEY` or `OPENAI_API_KEY`, plus optional
  `X_BEARER_TOKEN`;
- a bounded job timeout;
- a final job summary containing source health, publication state, commit SHA,
  RSS state, and page state.

The public repository's standard GitHub-hosted runner does not add an Actions
compute charge under the current GitHub billing model.

## Source Availability Policy

Sources are divided by runtime capability:

- Portable sources such as Hacker News, GitHub, V2EX, HuggingFace, Product
  Hunt, OpenAI, Anthropic, and supported public APIs are available to both
  local and cloud runs.
- Local-only sources such as browser-authenticated Xiaohongshu, Zhihu, and
  browser fallbacks are attempted by the MacBook run.
- X uses its official bearer token in either environment when configured, with
  the local browser fallback available only on the MacBook.

Missing local-only sources never block the cloud fallback. The guaranteed
service level is one core report per day, not successful collection from every
source every day.

## LLM Configuration

The hard-coded model selection becomes environment-configurable:

- `AI_DAILY_LLM_MODEL` selects the primary model.
- `deepseek-v4-flash` becomes the DeepSeek default.
- The existing OpenAI fallback remains available when its key is configured.
- Logs record model name and token usage without printing secrets.

This removes dependence on the `deepseek-chat` alias scheduled for deprecation
on 2026-07-24.

## Failure Handling

- MacBook asleep or offline: the 10:37 cloud run publishes.
- First cloud run delayed or transiently failed: the 11:17 run retries.
- Two runs overlap: GitHub concurrency serializes cloud jobs; Git
  non-fast-forward recovery resolves cross-machine overlap.
- Report already exists: rerun verifies the remote and live state.
- LLM unavailable: the existing evidence-only fallback applies.
- Optional sources unavailable: report logs degraded/skipped status and
  continues.
- Push succeeds but deployment is late: the publisher polls RSS and returns
  nonzero if its deployment deadline is exceeded.

## Security

- Local secrets stay in `scripts/.env`.
- Cloud secrets stay in GitHub Actions Secrets.
- The workflow receives only `contents: write`.
- No browser cookies or local MCP credentials are uploaded.
- Logs must not print environment values or authorization headers.
- Generated artifacts remain restricted to the existing allowlist.

## Cost

- New hardware: RMB 0.
- GitHub Actions compute: RMB 0 for the current public repository and standard
  runner.
- Cloudflare storage: none required.
- Additional MacBook power: normal working-hours use only.
- LLM/API charges: usage-based and unchanged except for scheduled cloud
  fallback calls. DeepSeek is expected to remain a few RMB per month at the
  current report volume; OpenAI fallback costs more and is used only when
  configured.

## Rollout

1. Make LLM model configuration reliable before the alias deprecation date.
2. Add and test the GitHub Actions workflow with manual dispatch.
3. Perform one cloud-only publication test.
4. Add and install the LaunchAgent and due-check wrapper.
5. Exercise local-first, cloud-first, overlap, missed-local, and rerun cases.
6. Observe two natural publishing days.
7. Disable the Codex Automation only after both days satisfy acceptance.
8. Update the operational SOP with installation, recovery, and manual backfill
   commands.

## Acceptance Criteria

- With the MacBook off, a dated report reaches remote `main`, RSS, and the live
  page by the end of the recovery window.
- With the MacBook ready by 10:10, the local run attempts authenticated sources
  and normally publishes before the first cloud fallback.
- Repeated or overlapping invocations produce one effective daily report and
  no force push.
- Any failed publication returns nonzero and remains visible in Actions or
  local logs.
- Manual dispatch supports a historical date and force replacement.
- No secret, browser state, lock, or runtime log is committed.
- Existing Python and TypeScript tests and the production build continue to
  pass.

The operational target is normal publication before 10:30 and recovery
publication before 11:30, rather than an exact 10:00 timestamp.
