import { apiFetch, getAuthToken } from './http'

const BASE = '/api/v1'

export type ResearchMode = 'auto' | 'parallel' | 'multihop'
export type ResearchTaskStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'

export interface ResearchResult {
  report: string
  sources: Array<{
    chunk_id: string
    score: number
    combined_score?: number
    metadata: Record<string, unknown>
    content: string
  }>
}

export interface ResearchTaskData {
  task_id: string
  query?: string
  status?: ResearchTaskStatus
  result?: ResearchResult | null
  error?: string | null
}

export interface TaskResponse {
  success: boolean
  data: ResearchTaskData
  error: string | null
}

export async function submitResearch(
  query: string,
  enableWebSearch: boolean = false,
  researchMode: ResearchMode = 'auto',
  maxHops: number = 3,
): Promise<string> {
  const resp = await apiFetch(`${BASE}/research`, {
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

export async function fetchResearchTask(taskId: string): Promise<ResearchTaskData> {
  const resp = await apiFetch(`${BASE}/research/${taskId}`)
  if (!resp.ok) {
    throw new Error(`获取研究任务失败: ${resp.status} ${resp.statusText}`)
  }
  const body: TaskResponse = await resp.json()
  if (!body.data?.task_id) {
    throw new Error(body.error || '获取研究任务失败：响应数据无效')
  }
  return body.data
}

export async function fetchResult(taskId: string): Promise<ResearchResult | null> {
  const task = await fetchResearchTask(taskId)
  return task.result ?? null
}

export async function cancelResearch(taskId: string): Promise<void> {
  await apiFetch(`${BASE}/research/${taskId}/cancel`, { method: 'POST' })
}

export function researchStreamUrl(taskId: string): string {
  const token = getAuthToken()
  return token
    ? `${BASE}/research/${taskId}/stream?access_token=${encodeURIComponent(token)}`
    : `${BASE}/research/${taskId}/stream`
}
