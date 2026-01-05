<template>
  <el-row :gutter="12">
    <el-col :span="14">
      <el-card>
        <template #header>
          <div style="display:flex;align-items:center;justify-content:space-between">
            <div style="font-weight:600">团队管理（成员库）</div>
            <div style="display:flex;gap:8px">
              <el-button type="primary" @click="openCreate">新增成员</el-button>
              <el-button @click="load">刷新</el-button>
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
        </el-table>
      </el-card>
    </el-col>

    <el-col :span="10">
      <el-card v-if="selected">
        <template #header>
          <div style="display:flex;align-items:center;justify-content:space-between">
            <div style="font-weight:600">成员详情</div>
            <el-button type="primary" size="small" @click="openEdit">编辑</el-button>
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
        <div style="color:#666">点击左侧成员，查看详情。</div>
      </el-card>
    </el-col>
  </el-row>

  <el-dialog v-model="dialogOpen" :title="dialogMode === 'create' ? '新增成员' : '编辑成员'" width="520">
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
        <el-input v-model="form.password" type="password" placeholder="为空则不修改/或创建后不可登录" />
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
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '../lib/api'

type User = {
  id: number
  username: string
  display_name: string
  email: string
  is_active: boolean
  is_staff: boolean
}

const users = ref<User[]>([])
const selected = ref<User | null>(null)

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

async function load() {
  try {
    const resp = await api.get('/users/')
    users.value = resp.data
  } catch {
    ElMessage.error('加载成员失败（需要管理员权限）')
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

function openEdit() {
  if (!selected.value) return
  dialogMode.value = 'edit'
  form.id = selected.value.id
  form.username = selected.value.username
  form.display_name = selected.value.display_name
  form.email = selected.value.email
  form.password = ''
  form.is_active = selected.value.is_active
  form.is_staff = selected.value.is_staff
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
    await load()
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

onMounted(load)
</script>
