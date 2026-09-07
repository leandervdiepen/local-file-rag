import { describe, expect, it } from 'vitest'
import { flattenGroups, groupByFile, type PageHit } from '../../../src/renderer/domain/search-results'

function hit(overrides: Partial<PageHit> & Pick<PageHit, 'pageId' | 'fileId' | 'pageNo'>): PageHit {
  return {
    path: `/Users/someone/docs/${overrides.fileId}.pdf`,
    kind: 'pdf',
    score: 1,
    stage: 'content',
    snippet: '',
    ...overrides,
  }
}

describe('groupByFile', () => {
  it('orders groups by the rank of their best hit', () => {
    const groups = groupByFile([
      hit({ pageId: 'b:1', fileId: 'b', pageNo: 1 }),
      hit({ pageId: 'a:9', fileId: 'a', pageNo: 9 }),
      hit({ pageId: 'b:4', fileId: 'b', pageNo: 4 }),
    ])

    expect(groups.map((group) => group.fileId)).toEqual(['b', 'a'])
  })

  it('orders pages within a group by page number, not by rank', () => {
    const groups = groupByFile([
      hit({ pageId: 'a:9', fileId: 'a', pageNo: 9 }),
      hit({ pageId: 'a:2', fileId: 'a', pageNo: 2 }),
      hit({ pageId: 'a:5', fileId: 'a', pageNo: 5 }),
    ])

    expect(groups[0]?.hits.map((h) => h.pageNo)).toEqual([2, 5, 9])
  })

  it('takes the file name from the path', () => {
    const groups = groupByFile([hit({ pageId: 'a:1', fileId: 'a', pageNo: 1, path: '/Users/x/Invoice Q2.pdf' })])

    expect(groups[0]?.fileName).toBe('Invoice Q2.pdf')
  })

  it('flattens back into the order the rows are rendered in', () => {
    const groups = groupByFile([
      hit({ pageId: 'b:1', fileId: 'b', pageNo: 1 }),
      hit({ pageId: 'a:9', fileId: 'a', pageNo: 9 }),
      hit({ pageId: 'a:2', fileId: 'a', pageNo: 2 }),
    ])

    expect(flattenGroups(groups).map((h) => h.pageId)).toEqual(['b:1', 'a:2', 'a:9'])
  })

  it('has nothing to group when nothing matched', () => {
    expect(groupByFile([])).toEqual([])
  })
})
