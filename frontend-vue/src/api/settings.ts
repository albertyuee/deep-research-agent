const BASE = '/api/v1'

export interface LLMSettings {
  provider: string
  model: string
  api_key: string
  base_url: string
  temperature: number
  max_tokens: number
}

export interface EmbeddingSettings {
  mode: string
  model: string
  api_key: string
  device: string
  dimension: number
  query_max_chars: number
  api_base_url: string
}

export interface RetrievalSettings {
  top_k: number
  retry_top_k_multiplier: number
  max_top_k: number
  max_concurrency: number
  max_retries: number
  critique_threshold: number
  rrf_k: number
  vector_backend: string
}

export interface ReasoningSettings {
  enabled: boolean
  max_sub_queries: number
  max_hops: number
  context_max_chars: number
  search_query_max_chars: number
}

export interface MilvusSettings {
  uri: string
  token: string
  host: string
  port: number
  collection_name: string
}

export interface RerankSettings {
  enabled: boolean
  provider: string
  model: string
  api_key: string
  base_url: string
  top_n: number
  candidate_multiplier: number
  timeout: number
  instruction: string
}

export interface MCPSettings {
  web_search_enabled: boolean
  tavily_api_key: string
  tavily_max_results: number
  web_search_timeout: number
}

export interface LangSmithSettings {
  tracing: boolean
  tracing_v2: boolean
  api_key: string
  project: string
  endpoint: string
}

export interface SettingsData {
  llm: LLMSettings
  embedding: EmbeddingSettings
  retrieval: RetrievalSettings
  reasoning: ReasoningSettings
  rerank: RerankSettings
  milvus: MilvusSettings
  mcp: MCPSettings
  langsmith: LangSmithSettings
}

export interface SystemInfo {
  vector_backend: string
  chunk_count: number
  version: string
}

export async function fetchSettings(): Promise<SettingsData> {
  const resp = await fetch(`${BASE}/settings`)
  if (!resp.ok) throw new Error(`获取配置失败: ${resp.status}`)
  const body = await resp.json()
  return body.data
}

export async function updateSettings(
  patch: Partial<{ llm: Partial<LLMSettings>; embedding: Partial<EmbeddingSettings>; retrieval: Partial<RetrievalSettings>; reasoning: Partial<ReasoningSettings>; rerank: Partial<RerankSettings>; milvus: Partial<MilvusSettings>; mcp: Partial<MCPSettings>; langsmith: Partial<LangSmithSettings> }>
): Promise<{ updated: string[]; need_restart: boolean }> {
  const resp = await fetch(`${BASE}/settings`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(patch),
  })
  if (!resp.ok) throw new Error(`保存失败: ${resp.status}`)
  const body = await resp.json()
  return body.data
}

export async function fetchSystemInfo(): Promise<SystemInfo> {
  const resp = await fetch(`${BASE}/settings/system-info`)
  if (!resp.ok) throw new Error(`获取系统信息失败: ${resp.status}`)
  const body = await resp.json()
  return body.data
}

export interface TestConnectionResult {
  success: boolean
  data: { message: string; preview?: string }
}

export async function testConnection(
  service: 'llm' | 'embedding' | 'milvus' | 'langsmith',
  config?: Record<string, unknown>,
): Promise<TestConnectionResult> {
  const resp = await fetch(`${BASE}/settings/test-connection`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ service, config: config || {} }),
  })
  const body = await resp.json()
  return body
}
