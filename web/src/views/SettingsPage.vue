<template>
  <el-tabs v-model="activeTab">
    <el-tab-pane label="我的账号" name="me">
      <el-card>
        <template #header>
          <div style="display:flex;align-items:center;justify-content:space-between">
            <div style="font-weight:600">当前账号</div>
            <div style="display:flex;gap:8px">
              <el-button @click="loadMe">刷新</el-button>
              <el-button type="danger" @click="logout">退出登录</el-button>
            </div>
          </div>
        </template>

        <el-descriptions v-if="me" :column="1" border>
          <el-descriptions-item label="姓名">{{ me.display_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="账号">{{ me.username }}</el-descriptions-item>
          <el-descriptions-item label="邮箱">{{ me.email || '-' }}</el-descriptions-item>
          <el-descriptions-item label="启用">{{ me.is_active ? '是' : '否' }}</el-descriptions-item>
          <el-descriptions-item label="管理员">{{ me.is_staff ? '是' : '否' }}</el-descriptions-item>
        </el-descriptions>
        <div v-else style="color:#666">正在加载账号信息…</div>
      </el-card>
    </el-tab-pane>

    <el-tab-pane label="用户管理" name="users">
      <el-row :gutter="12">
        <el-col :span="14">
          <el-card>
            <template #header>
              <div style="display:flex;align-items:center;justify-content:space-between">
                <div style="font-weight:600">用户列表（管理员）</div>
                <div style="display:flex;gap:8px">
                  <el-button type="primary" @click="openCreate">新增用户</el-button>
                  <el-button @click="loadUsers">刷新</el-button>
                </div>
              </div>
            </template>

            <el-table :data="users" height="650" @row-click="select">
              <el-table-column prop="display_name" label="姓名" width="140" />
              <el-table-column prop="username" label="账号" width="160" />
              <el-table-column prop="email" label="邮箱" min-width="200" />
              <el-table-column prop="is_active" label="启用" width="90">
                <template #default="scope">{{ scope.row.is_active ? '是' : '否' }}</template>
              </el-table-column>
              <el-table-column prop="is_staff" label="管理员" width="100">
                <template #default="scope">{{ scope.row.is_staff ? '是' : '否' }}</template>
              </el-table-column>
              <el-table-column label="操作" width="160">
                <template #default="scope">
                  <el-button size="small" @click.stop="openEdit(scope.row)">编辑</el-button>
                  <el-button size="small" type="danger" @click.stop="remove(scope.row)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </el-col>

        <el-col :span="10">
          <el-card v-if="selected">
            <template #header>
              <div style="display:flex;align-items:center;justify-content:space-between">
                <div style="font-weight:600">用户详情</div>
                <el-button type="primary" size="small" @click="openEdit(selected)">编辑</el-button>
              </div>
            </template>

            <el-descriptions :column="1" border>
              <el-descriptions-item label="姓名">{{ selected.display_name || '-' }}</el-descriptions-item>
              <el-descriptions-item label="账号">{{ selected.username }}</el-descriptions-item>
              <el-descriptions-item label="邮箱">{{ selected.email || '-' }}</el-descriptions-item>
              <el-descriptions-item label="启用">{{ selected.is_active ? '是' : '否' }}</el-descriptions-item>
              <el-descriptions-item label="管理员">{{ selected.is_staff ? '是' : '否' }}</el-descriptions-item>
            </el-descriptions>
          </el-card>
          <el-card v-else>
            <div style="color:#666">仅管理员可管理用户；点击左侧查看详情。</div>
          </el-card>
        </el-col>
      </el-row>
    </el-tab-pane>

    <el-tab-pane label="系统备份" name="backups">
      <el-card>
        <template #header>
          <div style="display:flex;align-items:center;justify-content:space-between">
            <div style="font-weight:600">备份管理（管理员）</div>
            <div style="display:flex;gap:8px">
              <el-button type="primary" @click="createBackup">立即备份</el-button>
              <el-button @click="loadBackups">刷新</el-button>
            </div>
          </div>
        </template>
        
        <el-table :data="backups" style="width: 100%">
          <el-table-column prop="name" label="文件名" />
          <el-table-column prop="size" label="大小" width="120">
            <template #default="scope">{{ fmtBytes(scope.row.size) }}</template>
          </el-table-column>
          <el-table-column prop="created_at" label="创建时间" width="180">
            <template #default="scope">{{ fmtTime(scope.row.created_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="120">
            <template #default="scope">
              <el-button size="small" type="warning" @click="restoreBackup(scope.row)">恢复</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </el-tab-pane>
  </el-tabs>

  <el-dialog v-model="dialogOpen" :title="dialogMode === 'create' ? '新增用户' : '编辑用户'" width="520">
    <el-form label-width="90px">
      <el-form-item label="账号">
        <el-input v-model="form.username" :disabled="dialogMode === 'edit'" />
      </el-form-item>
      <el-form-item label="姓名">
        <el-input v-model="form.display_name" />
      </el-form-item>
      <el-form-item label="邮箱">
        <el-input v-model="form.email" />
      </el-form-item>
      <el-form-item label="密码">
        <el-input v-model="form.password" type="password" placeholder="为空则不修改" />
      </el-form-item>
      <el-form-item label="启用">
        <el-switch v-model="form.is_active" />
      </el-form-item>
      <el-form-item label="管理员">
        <el-switch v-model="form.is_staff" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dialogOpen = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="save">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '../lib/api'

type Me = {
  id: number
  username: string
  display_name: string
  email: string
  is_active: boolean
  is_staff: boolean
}

type User = {
  id: number
  username: string
  display_name: string
  email: string
  is_active: boolean
  is_staff: boolean
}

const router = useRouter()
const activeTab = ref<'me' | 'users' | 'backups'>('me')

const me = ref<Me | null>(null)

const users = ref<User[]>([])
const selected = ref<User | null>(null)
const backups = ref<any[]>([])

const dialogOpen = ref(false)
const dialogMode = ref<'create' | 'edit'>('create')
const saving = ref(false)

const form = reactive({
  id: 0,
  username: '',
  display_name: '',
  email: '',
  password: '',
  is_active: true,
  is_staff: false
})

async function loadMe() {
  try {
    const resp = await api.get('/auth/me/')
    me.value = resp.data?.data ?? null
  } catch {
    me.value = null
  }
}

async function loadUsers() {
  try {
    const resp = await api.get('/users/')
    users.value = resp.data
  } catch {
    users.value = []
    ElMessage.error('加载用户失败（需要管理员权限）')
  }
}

function select(row: User) {
  selected.value = row
}

function openCreate() {
  dialogMode.value = 'create'
  form.id = 0
  form.username = ''
  form.display_name = ''
  form.email = ''
  form.password = ''
  form.is_active = true
  form.is_staff = false
  dialogOpen.value = true
}

function openEdit(row: User) {
  dialogMode.value = 'edit'
  form.id = row.id
  form.username = row.username
  form.display_name = row.display_name
  form.email = row.email
  form.password = ''
  form.is_active = row.is_active
  form.is_staff = row.is_staff
  dialogOpen.value = true
}

async function save() {
  saving.value = true
  try {
    const payload: any = {
      username: form.username,
      display_name: form.display_name,
      email: form.email,
      is_active: form.is_active,
      is_staff: form.is_staff
    }
    if (form.password) payload.password = form.password

    if (dialogMode.value === 'create') {
      await api.post('/users/', payload)
    } else {
      await api.patch(`/users/${form.id}/`, payload)
    }

    dialogOpen.value = false
    await loadUsers()
    if (dialogMode.value === 'edit' && selected.value) {
      const updated = users.value.find((u) => u.id === selected.value?.id)
      if (updated) selected.value = updated
    }
  } catch {
    ElMessage.error('保存失败（需要管理员权限）')
  } finally {
    saving.value = false
  }
}

async function remove(row: User) {
  try {
    await ElMessageBox.confirm(`确认删除用户：${row.username}？`, '确认删除', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消'
    })
    await api.delete(`/users/${row.id}/`)
    if (selected.value?.id === row.id) selected.value = null
    await loadUsers()
  } catch {
    // cancelled or failed
  }
}

function logout() {
  localStorage.removeItem('tfpc_token')
  router.push('/login')
}

function fmtBytes(n: number) {
  if (!n || n <= 0) return '-'
  const units = ['B', 'KB', 'MB', 'GB']
  let v = n
  let idx = 0
  while (v >= 1024 && idx < units.length - 1) {
    v /= 1024
    idx += 1
  }
  const s = idx === 0 ? String(Math.round(v)) : v.toFixed(v >= 10 ? 1 : 2)
  return `${s} ${units[idx]}`
}

function fmtTime(v: string) {
  if (!v) return ''
  return v.replace('T', ' ').slice(0, 19)
}

async function loadBackups() {
  try {
    const resp = await api.get('/backups/')
    backups.value = resp.data
  } catch {
    backups.value = []
  }
}

async function createBackup() {
  try {
    await api.post('/backups/create/')
    ElMessage.success('备份已创建')
    await loadBackups()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '备份失败')
  }
}

async function restoreBackup(row: any) {
  try {
    await ElMessageBox.confirm(`确定从备份 ${row.name} 恢复吗？这将覆盖当前数据！`, '恢复备份', {
      confirmButtonText: '恢复',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await api.post('/backups/restore/', { filename: row.name })
    ElMessage.success('恢复成功')
  } catch (e: any) {
    if (e?.name === 'CanceledError' || e === 'cancel' || e === 'cancelled') return
    ElMessage.error(e?.response?.data?.detail || '恢复失败')
  }
}

watch(
  () => activeTab.value,
  (v) => {
    if (v === 'users') loadUsers()
    if (v === 'backups') loadBackups()
  }
)

onMounted(() => {
  loadMe()
})
</script>
