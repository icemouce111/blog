export interface ReadingSection {
  id: string
  title: string
  level?: number
  number?: string
  line?: number
}

export function decodeReadingHash(hash: string): string {
  try {
    return decodeURIComponent(hash.replace(/^#/, ''))
  } catch {
    return ''
  }
}

function headingText(text: string) {
  return text
    .replace(/!?\[([^\]]*)\]\([^)]*\)/g, '$1')
    .replace(/<[^>]*>/g, '')
    .replace(/[*_`~]/g, '')
    .replace(/\s+#+\s*$/, '')
    .trim()
}

// Both the rendered heading and its directory entry use the same source line.
// Fenced examples must never become headings; duplicate labels get stable suffixes.
export function getReadingSections(markdown: string): ReadingSection[] {
  const used = new Set<string>()
  const sections: ReadingSection[] = []
  let fence: { marker: string; length: number } | undefined
  markdown.split('\n').forEach((line, index) => {
    const marker = line.match(/^ {0,3}(`{3,}|~{3,})/)
    if (marker) {
      if (!fence) fence = { marker: marker[1][0], length: marker[1].length }
      else if (
        marker[1][0] === fence.marker &&
        marker[1].length >= fence.length &&
        /^ {0,3}(`+|~+)\s*$/.test(line)
      )
        fence = undefined
      return
    }
    if (fence) return
    const match = line.match(/^ {0,3}(#{2,3})\s+(.+?)\s*$/)
    if (!match) return
    const title = headingText(match[2])
    const base =
      title
        .toLowerCase()
        .replace(/[^\w\u4e00-\u9fff]+/g, '-')
        .replace(/^-|-$/g, '') || 'section'
    let id = base
    let suffix = 1
    while (used.has(id)) id = `${base}-${++suffix}`
    used.add(id)
    sections.push({ id, title, level: match[1].length, line: index + 1 })
  })
  return sections
}

export function activeReadingSection(sections: { id: string; top: number }[], offset: number) {
  return sections.findLast((section) => section.top <= offset + 2)?.id || sections[0]?.id || ''
}
