import { apiFetch } from './http'

const BASE = '/api/v1'

export interface DocFile {
  id: string
  name: string
  size: number
  chunks: number
  status: 'ready' | 'processing' | 'error'
  uploaded_at: string
  visibility?: 'private' | 'department' | 'departments' | 'workspace' | 'roles' | 'users' | 'public'
  department_id?: string | null
  allowed_departments?: string[]
  owner_id?: string | null
  allowed_roles?: string[]
  allowed_users?: string[]
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
  const resp = await apiFetch(`${BASE}/documents`)
  if (!resp.ok) throw new Error(`获取文件列表失败: ${resp.status}`)
  const body: DocListResponse = await resp.json()
  if (!body.success) throw new Error(body.error || '获取失败')
  return body.data.files
}

export async function uploadDocument(
  file: File,
  access: { visibility?: string; departmentIds?: string[]; allowedRoles?: string[]; allowedUsers?: string[] } = {},
): Promise<DocUploadResponse['data']> {
  const form = new FormData()
  form.append('file', file)
  form.append('visibility', access.visibility || 'private')
  form.append('department_ids', (access.departmentIds || []).join(','))
  form.append('allowed_roles', (access.allowedRoles || []).join(','))
  form.append('allowed_users', (access.allowedUsers || []).join(','))
  const resp = await apiFetch(`${BASE}/documents/upload`, {
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
  const resp = await apiFetch(`${BASE}/documents/${fileId}`, { method: 'DELETE' })
  if (!resp.ok) throw new Error(`删除失败: ${resp.status}`)
}

export async function updateDocumentAccess(
  fileId: string,
  access: { visibility: string; departmentId?: string | null; allowedDepartmentIds?: string[]; allowedRoles?: string[]; allowedUsers?: string[] },
): Promise<void> {
  const resp = await apiFetch(`${BASE}/documents/${fileId}/access`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      visibility: access.visibility,
      department_id: access.departmentId || null,
      allowed_departments: access.allowedDepartmentIds || [],
      allowed_roles: access.allowedRoles || [],
      allowed_users: access.allowedUsers || [],
    }),
  })
  if (!resp.ok) throw new Error(`更新文档权限失败: ${resp.status}`)
}
