const BASE = '/api/v1'

export type ResearchMode = 'auto' | 'parallel' | 'multihop'

export interface TaskResponse {
  success: boolean
  data: {
    task_id: string
    query?: string
    status?: string
    result?: {
      report: string
      sources: Array<{
        chunk_id: string
        score: number
        metadata: Record<string, unknown>
        content: string
      }>
    }
    error?: string
  }
  error: string | null
}

export async function submitResearch(
  query: string,
  enableWebSearch: boolean = false,
  researchMode: ResearchMode = 'auto',
  maxHops: number = 3,
): Promise<string> {
  const resp = await fetch(`${BASE}/research`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query,
      enable_web_search: enableWebSearch,
      research_mode: researchMode,
      max_hops: maxHops,
    }),
  })
  if (!resp.ok) {
    throw new Error(`提交失败: ${resp.status} ${resp.statusText}`)
  }
  const body: TaskResponse = await resp.json()
  if (!body.success || !body.data?.task_id) {
    throw new Error(body.error || '提交失败：未获取到任务 ID')
  }
  return body.data.task_id
}

export async function fetchResult(taskId: string): Promise<TaskResponse['data']['result'] | null> {
  const resp = await fetch(`${BASE}/research/${taskId}`)
  if (!resp.ok) return null
  const body: TaskResponse = await resp.json()
  return body.data?.result ?? null
}

export async function cancelResearch(taskId: string): Promise<void> {
  await fetch(`${BASE}/research/${taskId}/cancel`, { method: 'POST' })
}
