import assert from 'node:assert/strict'
import test from 'node:test'
import { classifyOpportunity, groupOpportunities, pendingReason, type CreatorOpportunity } from '../src/lib/creator-opportunity-policy.ts'

const profile = { followersBelow: 1000, weeklyHours: 10, verificationMaxAgeDays: 7 }
function item(changes: Partial<CreatorOpportunity> = {}): CreatorOpportunity {
  return {
    id: 'sample', title: 'AI商品短片', organizer: '官方主办', type: '创作赛', url: 'https://official.example/activity',
    rewardTypes: ['cash_prize'], reward: '评优现金奖励，非保底', requirements: '原创视频与活动要求',
    deadline: '2026-11-15', deadlineKind: 'dated', deadlineText: '11月15日截止', fitStage: 'now', fit: '适合积累样片',
    minFollowers: null, priority: 1, verification: 'official', verifiedAt: '2026-10-30', checkedAt: null, ...changes,
  }
}

test('separates confirmed, uncertain, later and expired opportunities', () => {
  const result = groupOpportunities([
    item(), item({ id: 'needs-review', verification: 'pending' }),
    item({ id: 'thousand-followers', minFollowers: 1000 }),
    item({ id: 'expired', deadline: '2026-10-29' }),
    item({ id: 'conflict', deadline: null, deadlineKind: 'conflicting' }),
  ], '2026-10-30', profile)
  assert.deepEqual(result.recommended.map((entry) => entry.id), ['sample'])
  assert.deepEqual(result.later.map((entry) => entry.id), ['thousand-followers'])
  assert.equal(result.pending.length, 2)
})

test('stale, future or malformed evidence never appears as verified', () => {
  for (const verifiedAt of ['2026-10-21', '2026-10-31', '2026-02-30', null]) {
    assert.equal(classifyOpportunity(item({ verifiedAt }), '2026-10-30', profile), 'pending')
  }
  assert.equal(classifyOpportunity(item(), '2026-10-30', profile), 'recommended')
  assert.match(pendingReason(item({ verifiedAt: '2026-10-21' }), '2026-10-30', profile), /超过有效期/)
})

test('unknown deadline and missing requirements are not treated as rolling programs', () => {
  assert.equal(classifyOpportunity(item({ deadline: null, deadlineKind: 'unknown' }), '2026-10-30', profile), 'pending')
  assert.equal(classifyOpportunity(item({ deadline: null, deadlineKind: 'rolling' }), '2026-10-30', profile), 'recommended')
  assert.equal(classifyOpportunity(item({ requirements: '' }), '2026-10-30', profile), 'pending')
})
