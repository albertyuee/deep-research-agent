const BASE = '/api/v1'

export interface QuickSearchResponse {
  success: boolean
  data: {
    query: string
    summary: string
    sources: Array<{
      chunk_id: string
      content: string
      score: number
      metadata: Record<string, unknown>
    }>
    elapsed_ms: number
  }
  error: string | null
}

export async function quickSearch(query: string, topK: number = 5): Promise<QuickSearchResponse['data']> {
  const resp = await fetch(`${BASE}/quick-search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, top_k: topK }),
  })
  if (!resp.ok) {
    throw new Error(`搜索失败: ${resp.status} ${resp.statusText}`)
  }
  const body: QuickSearchResponse = await resp.json()
  if (!body.success) {
    throw new Error(body.error || '搜索失败')
  }
  return body.data
}
