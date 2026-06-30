import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

interface Project {
  name: string
  description: string
  tags: string[]
  github?: string
  demo?: string
}

test('作品集只展示 browser-smart Skill 和接触网缺陷复核 Demo', async () => {
  const projectsUrl = new URL('../src/data/projects.json', import.meta.url)
  const projects = JSON.parse(await readFile(projectsUrl, 'utf8')) as Project[]

  assert.deepEqual(
    projects.map(({ name, github, demo }) => ({ name, github, demo })),
    [
      {
        name: 'browser-smart',
        github: 'https://github.com/icemouce111/browser-smart',
        demo: undefined,
      },
      {
        name: '接触网缺陷复核 Demo',
        github: 'https://github.com/icemouce111/catenary-defect-review-demo',
        demo: undefined,
      },
    ],
  )

  for (const project of projects) {
    assert.ok(project.description.length > 0)
    assert.ok(project.tags.length > 0)
  }
})
