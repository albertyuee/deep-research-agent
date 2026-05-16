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
  api_base_url: string
}

export interface RetrievalSettings {
  top_k: number
  max_retries: number
  critique_threshold: number
  rrf_k: number
  vector_backend: string
}

export interface SettingsData {
  llm: LLMSettings
  embedding: EmbeddingSettings
  retrieval: RetrievalSettings
}

export interface SystemInfo {
  chroma_chunks: number
  version: string
}

export async function fetchSettings(): Promise<SettingsData> {
  const resp = await fetch(`${BASE}/settings`)
  if (!resp.ok) throw new Error(`获取配置失败: ${resp.status}`)
  const body = await resp.json()
  return body.data
}

export async function updateSettings(
  patch: Partial<{ llm: Partial<LLMSettings>; embedding: Partial<EmbeddingSettings>; retrieval: Partial<RetrievalSettings> }>
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
