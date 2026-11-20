import assert from 'node:assert/strict'
import test from 'node:test'

test('React DOM client loads with the installed React runtime', async () => {
  const { createRoot } = await import('react-dom/client')
  assert.equal(typeof createRoot, 'function')
})
