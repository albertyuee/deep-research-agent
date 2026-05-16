const BASE = '/api/v1'

export interface DocFile {
  id: string
  name: string
  size: number
  chunks: number
  status: 'ready' | 'processing' | 'error'
  uploaded_at: string
}

export interface DocListResponse {
  success: boolean
  data: { files: DocFile[] }
  error: string | null
}

export interface DocUploadResponse {
  success: boolean
  data: { file_id: string; name: string; chunks: number; status: string }
  error: string | null
}

export async function fetchDocuments(): Promise<DocFile[]> {
  const resp = await fetch(`${BASE}/documents`)
  if (!resp.ok) throw new Error(`获取文件列表失败: ${resp.status}`)
  const body: DocListResponse = await resp.json()
  if (!body.success) throw new Error(body.error || '获取失败')
  return body.data.files
}

export async function uploadDocument(file: File): Promise<DocUploadResponse['data']> {
  const form = new FormData()
  form.append('file', file)
  const resp = await fetch(`${BASE}/documents/upload`, {
    method: 'POST',
    body: form,
  })
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: resp.statusText }))
    // FastAPI 422 detail can be an array of validation errors; format it
    const msg = typeof err.detail === 'string'
      ? err.detail
      : Array.isArray(err.detail)
        ? err.detail.map((e: { msg: string }) => e.msg).join('; ')
        : `HTTP ${resp.status}`
    throw new Error(msg)
  }
  const body: DocUploadResponse = await resp.json()
  if (!body.success) throw new Error(body.error || '上传失败')
  return body.data
}

export async function deleteDocument(fileId: string): Promise<void> {
  const resp = await fetch(`${BASE}/documents/${fileId}`, { method: 'DELETE' })
  if (!resp.ok) throw new Error(`删除失败: ${resp.status}`)
}
