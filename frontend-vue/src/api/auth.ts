import { apiFetch, setAuthToken } from './http'

const BASE = '/api/v1/auth'

export interface AuthUser {
  id: string
  email: string
  display_name: string
  role: 'admin' | 'researcher' | 'guest'
  department_id: string | null
  permissions: string[]
}

export interface AdminUser {
  id: string
  email: string
  display_name: string
  role: AuthUser['role']
  department_id: string | null
  active: boolean
}

export interface Department {
  id: string
  name: string
  parent_id: string | null
  created_at?: string
}

export async function login(email: string, password: string): Promise<AuthUser> {
  const resp = await apiFetch(`${BASE}/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
  const body = await resp.json().catch(() => ({}))
  if (!resp.ok) throw new Error(body.detail || '登录失败')
  if (body.data?.token) setAuthToken(body.data.token)
  return body.data.user as AuthUser
}

export async function fetchCurrentUser(): Promise<AuthUser> {
  const resp = await apiFetch(`${BASE}/me`)
  const body = await resp.json().catch(() => ({}))
  if (!resp.ok) throw new Error(body.detail || `获取用户信息失败: ${resp.status}`)
  return body.data.user as AuthUser
}

export function logout(): void {
  setAuthToken(null)
}

async function parseAdminResponse(resp: Response): Promise<any> {
  const body = await resp.json().catch(() => ({}))
  if (!resp.ok) throw new Error(body.detail || `请求失败: ${resp.status}`)
  return body.data
}

export async function fetchUsers(): Promise<AdminUser[]> {
  const data = await parseAdminResponse(await apiFetch(`${BASE}/users`))
  return data.users as AdminUser[]
}

export async function createUser(payload: {
  email: string
  password: string
  display_name: string
  role: AuthUser['role']
  department_id?: string | null
}): Promise<AdminUser> {
  const data = await parseAdminResponse(await apiFetch(`${BASE}/users`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  }))
  return data.user as AdminUser
}

export async function updateUser(userId: string, payload: {
  display_name?: string
  role?: AuthUser['role']
  department_id?: string | null
  active?: boolean
  password?: string
}): Promise<AdminUser> {
  const data = await parseAdminResponse(await apiFetch(`${BASE}/users/${userId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  }))
  return data.user as AdminUser
}

export async function deleteUser(userId: string): Promise<void> {
  await parseAdminResponse(await apiFetch(`${BASE}/users/${userId}`, { method: 'DELETE' }))
}

export async function fetchDepartments(): Promise<Department[]> {
  const data = await parseAdminResponse(await apiFetch(`${BASE}/departments`))
  return data.departments as Department[]
}

export async function createDepartment(name: string, parent_id: string | null = null): Promise<Department> {
  return await parseAdminResponse(await apiFetch(`${BASE}/departments`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, parent_id }),
  })) as Department
}
