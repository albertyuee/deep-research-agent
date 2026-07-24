<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <div>
        <h1 class="text-xl font-bold text-gray-800">⚙️ 管理后台</h1>
        <p class="text-sm text-gray-400">管理用户、部门和系统角色权限</p>
      </div>
      <n-tag type="success">管理员</n-tag>
    </div>

    <n-alert v-if="error" type="error" :bordered="false" class="mb-4">{{ error }}</n-alert>

    <n-tabs type="line" animated>
      <n-tab-pane name="users" tab="用户管理">
        <div class="flex justify-between items-center mb-4">
          <span class="text-sm text-gray-500">共 {{ users.length }} 个用户</span>
          <n-button type="primary" @click="openCreateUser">
            <template #icon><n-icon><person-add-outline /></n-icon></template>
            新增用户
          </n-button>
        </div>
        <n-spin :show="loading">
          <div v-if="users.length" class="grid grid-cols-1 lg:grid-cols-2 gap-3">
            <n-card v-for="item in users" :key="item.id" size="small" :bordered="false" class="border border-gray-100">
              <div class="flex items-start justify-between gap-3">
                <div class="min-w-0">
                  <div class="font-semibold text-gray-800 truncate">{{ item.display_name }}</div>
                  <div class="text-xs text-gray-400 truncate">{{ item.email }}</div>
                  <div class="flex gap-2 mt-2">
                    <n-tag size="small" :type="roleType(item.role)">{{ roleLabel(item.role) }}</n-tag>
                    <n-tag size="small" :type="item.active ? 'success' : 'default'">{{ item.active ? '启用' : '已禁用' }}</n-tag>
                    <n-tag v-if="departmentName(item.department_id)" size="small" type="info">{{ departmentName(item.department_id) }}</n-tag>
                  </div>
                </div>
                <div class="flex gap-1 shrink-0">
                  <n-button text size="small" @click="openEditUser(item)">编辑</n-button>
                  <n-popconfirm @positive-click="removeUser(item)">
                    <template #trigger><n-button text size="small" type="error">删除</n-button></template>
                    确定删除「{{ item.display_name }}」？
                  </n-popconfirm>
                </div>
              </div>
            </n-card>
          </div>
          <n-empty v-else description="暂无用户" />
        </n-spin>
      </n-tab-pane>

      <n-tab-pane name="departments" tab="部门管理">
        <div class="flex justify-between items-center mb-4">
          <span class="text-sm text-gray-500">共 {{ departments.length }} 个部门</span>
          <n-button type="primary" @click="showDepartmentModal = true">新增部门</n-button>
        </div>
        <div v-if="departments.length" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          <n-card v-for="department in departments" :key="department.id" size="small" :bordered="false" class="border border-gray-100">
            <div class="font-semibold text-gray-800">{{ department.name }}</div>
            <div class="text-xs text-gray-400 mt-1">ID: {{ department.id }}</div>
            <div class="text-xs text-gray-500 mt-2">{{ users.filter(user => user.department_id === department.id).length }} 名成员</div>
          </n-card>
        </div>
        <n-empty v-else description="暂无部门" />
      </n-tab-pane>

      <n-tab-pane name="documents" tab="文档权限">
        <div class="flex justify-between items-center mb-4">
          <span class="text-sm text-gray-500">显示 {{ filteredDocuments.length }} / {{ documents.length }} 份文档</span>
          <div class="flex items-center gap-2">
            <n-input v-model:value="documentSearchQuery" clearable placeholder="搜索文档名称或 ID" style="width: 220px">
              <template #prefix><n-icon><search-outline /></n-icon></template>
            </n-input>
            <n-button text type="primary" @click="loadDocuments">刷新</n-button>
          </div>
        </div>
        <n-spin :show="documentsLoading">
          <div v-if="filteredDocuments.length" class="grid grid-cols-1 lg:grid-cols-2 gap-3">
            <n-card v-for="document in filteredDocuments" :key="document.id" size="small" :bordered="false" class="border border-gray-100">
              <div class="flex items-start justify-between gap-3">
                <div class="min-w-0">
                  <div class="font-semibold text-gray-800 truncate">{{ document.name }}</div>
                  <div class="text-xs text-gray-400 mt-1">{{ document.chunks }} chunks</div>
                  <div class="flex gap-2 mt-2 flex-wrap">
                    <n-tag size="small" type="info">{{ visibilityLabel(document.visibility) }}</n-tag>
                    <n-tag v-if="document.department_id" size="small" type="success">{{ departmentName(document.department_id) || '本部门' }}</n-tag>
                    <n-tag v-for="departmentId in (document.allowed_departments || [])" :key="departmentId" size="small" type="success">{{ departmentName(departmentId) || '指定部门' }}</n-tag>
                    <n-tag v-for="role in (document.allowed_roles || [])" :key="role" size="small">{{ roleLabel(role as AuthUser['role']) }}</n-tag>
                  </div>
                </div>
                <n-button size="small" type="primary" secondary @click="openDocumentAccess(document)">修改权限</n-button>
              </div>
            </n-card>
          </div>
          <n-empty v-else :description="documentSearchQuery ? '没有匹配的文档' : '暂无文档'" />
        </n-spin>
      </n-tab-pane>

      <n-tab-pane name="permissions" tab="角色权限">
        <n-alert type="info" :bordered="false" class="mb-4">
          权限由后端统一校验。管理员可以管理全部资源，研究者默认可以上传和检索，访客只能检索被授权资料。
        </n-alert>
        <n-table :bordered="false" :single-line="false">
          <thead><tr><th>权限</th><th>管理员</th><th>研究者</th><th>访客</th></tr></thead>
          <tbody>
            <tr v-for="permission in permissionRows" :key="permission.key">
              <td>{{ permission.label }}</td><td>✓</td><td>{{ permission.researcher ? '✓' : '—' }}</td><td>{{ permission.guest ? '✓' : '—' }}</td>
            </tr>
          </tbody>
        </n-table>
      </n-tab-pane>
    </n-tabs>

    <n-modal v-model:show="showUserModal" preset="card" :title="editingUser ? '编辑用户' : '新增用户'" style="width: 480px">
      <n-form label-placement="left" label-width="90">
        <n-form-item label="姓名"><n-input v-model:value="userForm.display_name" placeholder="用户姓名" /></n-form-item>
        <n-form-item v-if="!editingUser" label="邮箱"><n-input v-model:value="userForm.email" placeholder="name@example.com" /></n-form-item>
        <n-form-item v-if="!editingUser" label="初始密码"><n-input v-model:value="userForm.password" type="password" placeholder="至少 8 位" /></n-form-item>
        <n-form-item v-if="editingUser" label="重置密码"><n-input v-model:value="userForm.password" type="password" placeholder="留空则不修改" /></n-form-item>
        <n-form-item label="角色"><n-select v-model:value="userForm.role" :options="roleOptions" /></n-form-item>
        <n-form-item label="部门"><n-select v-model:value="userForm.department_id" clearable :options="departmentOptions" /></n-form-item>
        <n-form-item v-if="editingUser" label="状态"><n-switch v-model:value="userForm.active" /></n-form-item>
      </n-form>
      <template #footer><div class="flex justify-end gap-2"><n-button @click="showUserModal = false">取消</n-button><n-button type="primary" :loading="saving" @click="saveUser">保存</n-button></div></template>
    </n-modal>

    <n-modal v-model:show="showDepartmentModal" preset="card" title="新增部门" style="width: 420px">
      <n-form label-placement="left" label-width="80">
        <n-form-item label="部门名称"><n-input v-model:value="departmentNameInput" placeholder="例如：算法部" @keyup.enter="saveDepartment" /></n-form-item>
      </n-form>
      <template #footer><div class="flex justify-end gap-2"><n-button @click="showDepartmentModal = false">取消</n-button><n-button type="primary" :loading="saving" @click="saveDepartment">创建</n-button></div></template>
    </n-modal>

    <n-modal v-model:show="showDocumentModal" preset="card" title="修改文档权限" style="width: 500px">
      <div class="text-sm font-medium text-gray-700 mb-4 truncate">{{ editingDocument?.name }}</div>
      <n-form label-placement="left" label-width="100">
        <n-form-item label="访问范围"><n-select v-model:value="documentAccessForm.visibility" :options="accessOptions" /></n-form-item>
        <n-form-item v-if="documentAccessForm.visibility === 'department'" label="允许部门">
          <n-select v-model:value="documentAccessForm.department_id" clearable :options="departmentOptions" placeholder="选择部门" />
        </n-form-item>
        <n-form-item v-if="documentAccessForm.visibility === 'departments'" label="允许部门">
          <n-select v-model:value="documentAccessForm.allowed_department_ids" multiple :options="departmentOptions" placeholder="选择一个或多个部门" />
        </n-form-item>
        <n-form-item v-if="documentAccessForm.visibility === 'roles'" label="允许角色">
          <n-select v-model:value="documentAccessForm.allowed_roles" multiple :options="roleOptions" placeholder="选择角色" />
        </n-form-item>
        <n-form-item v-if="documentAccessForm.visibility === 'users'" label="允许用户">
          <n-select v-model:value="documentAccessForm.allowed_users" multiple :options="userOptions" placeholder="选择用户" />
        </n-form-item>
      </n-form>
      <template #footer><div class="flex justify-end gap-2"><n-button @click="showDocumentModal = false">取消</n-button><n-button type="primary" :loading="saving" @click="saveDocumentAccess">保存</n-button></div></template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { NIcon } from 'naive-ui'
import { PersonAddOutline, SearchOutline } from '@vicons/ionicons5'
import {
  createDepartment, createUser, deleteUser, fetchDepartments, fetchUsers, updateUser,
} from '@/api/auth'
import type { AdminUser, AuthUser, Department } from '@/api/auth'
import { fetchDocuments, updateDocumentAccess } from '@/api/documents'
import type { DocFile } from '@/api/documents'

const users = ref<AdminUser[]>([])
const departments = ref<Department[]>([])
const loading = ref(false)
const saving = ref(false)
const error = ref('')
const showUserModal = ref(false)
const showDepartmentModal = ref(false)
const showDocumentModal = ref(false)
const editingUser = ref<AdminUser | null>(null)
const editingDocument = ref<DocFile | null>(null)
const departmentNameInput = ref('')
const documents = ref<DocFile[]>([])
const documentsLoading = ref(false)
const documentSearchQuery = ref('')
const userForm = reactive({
  email: '', password: '', display_name: '', role: 'researcher' as AuthUser['role'],
  department_id: null as string | null, active: true,
})

const roleOptions = [
  { label: '管理员', value: 'admin' },
  { label: '研究者', value: 'researcher' },
  { label: '访客', value: 'guest' },
]
const departmentOptions = computed(() => departments.value.map(item => ({ label: item.name, value: item.id })))
const userOptions = computed(() => users.value.filter(item => item.active).map(item => ({ label: `${item.display_name} (${item.email})`, value: item.id })))
const accessOptions = [
  { label: '仅自己可见', value: 'private' },
  { label: '指定部门可见', value: 'department' },
  { label: '当前工作区可见', value: 'workspace' },
  { label: '多个部门可见', value: 'departments' },
  { label: '指定角色可见', value: 'roles' },
  { label: '指定用户可见', value: 'users' },
  { label: '公开', value: 'public' },
]
const documentAccessForm = reactive({
  visibility: 'private',
  department_id: null as string | null,
  allowed_department_ids: [] as string[],
  allowed_roles: [] as string[],
  allowed_users: [] as string[],
})
const filteredDocuments = computed(() => {
  const keyword = documentSearchQuery.value.trim().toLowerCase()
  if (!keyword) return documents.value
  return documents.value.filter(document => `${document.name} ${document.id}`.toLowerCase().includes(keyword))
})
const permissionRows = [
  { key: 'document:read', label: '查看和检索文档', researcher: true, guest: true },
  { key: 'document:upload', label: '上传文档', researcher: true, guest: false },
  { key: 'document:delete', label: '删除自己上传的文档', researcher: true, guest: false },
  { key: 'document:share', label: '修改文档访问权限', researcher: false, guest: false },
  { key: 'research:create', label: '创建研究任务', researcher: true, guest: true },
  { key: 'user:manage', label: '管理用户和部门', researcher: false, guest: false },
]

function roleLabel(role: AuthUser['role']) { return ({ admin: '管理员', researcher: '研究者', guest: '访客' }[role]) }
function roleType(role: AuthUser['role']) { return role === 'admin' ? 'error' : role === 'researcher' ? 'info' : 'default' }
function departmentName(id: string | null) { return departments.value.find(item => item.id === id)?.name || '' }
function visibilityLabel(visibility: DocFile['visibility']) {
  return accessOptions.find(item => item.value === visibility)?.label || '仅自己可见'
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    ;[users.value, departments.value, documents.value] = await Promise.all([fetchUsers(), fetchDepartments(), fetchDocuments()])
  } catch (e) { error.value = e instanceof Error ? e.message : '加载管理数据失败' }
  finally { loading.value = false }
}

async function loadDocuments() {
  documentsLoading.value = true
  try { documents.value = await fetchDocuments() }
  catch (e) { error.value = e instanceof Error ? e.message : '加载文档失败' }
  finally { documentsLoading.value = false }
}

function openDocumentAccess(document: DocFile) {
  editingDocument.value = document
  Object.assign(documentAccessForm, {
    visibility: document.visibility || 'private',
    department_id: document.department_id || null,
    allowed_department_ids: [...(document.allowed_departments || [])],
    allowed_roles: [...(document.allowed_roles || [])],
    allowed_users: [...(document.allowed_users || [])],
  })
  showDocumentModal.value = true
}

async function saveDocumentAccess() {
  if (!editingDocument.value) return
  if (documentAccessForm.visibility === 'department' && !documentAccessForm.department_id) {
    error.value = '请选择允许访问的部门'
    return
  }
  if (documentAccessForm.visibility === 'departments' && !documentAccessForm.allowed_department_ids.length) {
    error.value = '请选择至少一个部门'
    return
  }
  if (documentAccessForm.visibility === 'roles' && !documentAccessForm.allowed_roles.length) {
    error.value = '请选择至少一个角色'
    return
  }
  if (documentAccessForm.visibility === 'users' && !documentAccessForm.allowed_users.length) {
    error.value = '请选择至少一个用户'
    return
  }
  saving.value = true
  try {
    await updateDocumentAccess(editingDocument.value.id, {
      visibility: documentAccessForm.visibility,
      departmentId: documentAccessForm.department_id,
      allowedDepartmentIds: documentAccessForm.allowed_department_ids,
      allowedRoles: documentAccessForm.allowed_roles,
      allowedUsers: documentAccessForm.allowed_users,
    })
    editingDocument.value = {
      ...editingDocument.value,
      visibility: documentAccessForm.visibility as DocFile['visibility'],
      department_id: documentAccessForm.department_id,
      allowed_departments: [...documentAccessForm.allowed_department_ids],
      allowed_roles: [...documentAccessForm.allowed_roles],
      allowed_users: [...documentAccessForm.allowed_users],
    }
    documents.value = documents.value.map(item => item.id === editingDocument.value?.id ? editingDocument.value as DocFile : item)
    showDocumentModal.value = false
  } catch (e) { error.value = e instanceof Error ? e.message : '更新文档权限失败' }
  finally { saving.value = false }
}

function openCreateUser() {
  editingUser.value = null
  Object.assign(userForm, { email: '', password: '', display_name: '', role: 'researcher', department_id: null, active: true })
  showUserModal.value = true
}

function openEditUser(item: AdminUser) {
  editingUser.value = item
  Object.assign(userForm, { email: item.email, password: '', display_name: item.display_name, role: item.role, department_id: item.department_id, active: item.active })
  showUserModal.value = true
}

async function saveUser() {
  if (!userForm.display_name.trim() || (!editingUser.value && (!userForm.email.trim() || userForm.password.length < 8))) {
    error.value = editingUser.value ? '请填写姓名' : '请填写姓名、邮箱和至少 8 位密码'
    return
  }
  saving.value = true
  try {
    if (editingUser.value) {
      const payload: Parameters<typeof updateUser>[1] = { display_name: userForm.display_name, role: userForm.role, department_id: userForm.department_id, active: userForm.active }
      if (userForm.password) payload.password = userForm.password
      const updated = await updateUser(editingUser.value.id, payload)
      users.value = users.value.map(item => item.id === updated.id ? updated : item)
    } else {
      const created = await createUser({ email: userForm.email, password: userForm.password, display_name: userForm.display_name, role: userForm.role, department_id: userForm.department_id })
      users.value.push(created)
    }
    showUserModal.value = false
  } catch (e) { error.value = e instanceof Error ? e.message : '保存用户失败' }
  finally { saving.value = false }
}

async function removeUser(item: AdminUser) {
  try { await deleteUser(item.id); users.value = users.value.filter(user => user.id !== item.id) }
  catch (e) { error.value = e instanceof Error ? e.message : '删除用户失败' }
}

async function saveDepartment() {
  if (!departmentNameInput.value.trim()) return
  saving.value = true
  try { departments.value.push(await createDepartment(departmentNameInput.value.trim())); departmentNameInput.value = ''; showDepartmentModal.value = false }
  catch (e) { error.value = e instanceof Error ? e.message : '创建部门失败' }
  finally { saving.value = false }
}

onMounted(load)
</script>
