import assert from 'node:assert/strict'
import { createRequire } from 'node:module'
import test from 'node:test'

const require = createRequire(import.meta.url)

test('React DOM client loads with the installed React runtime', () => {
  const { createRoot } = require('react-dom/client')
  assert.equal(typeof createRoot, 'function')
})
