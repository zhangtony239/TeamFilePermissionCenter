<template>
  <el-card>
    <template #header>
      <div style="display:flex;align-items:center;justify-content:space-between">
        <div style="font-weight:600">任务</div>
        <div style="display:flex;gap:8px">
          <el-button type="primary" @click="openCreate">新增任务</el-button>
          <el-button @click="loadTasks">刷新</el-button>
        </div>
      </div>
    </template>

    <div style="display:flex;gap:10px;align-items:center;margin-bottom:12px;flex-wrap:wrap">
      <el-select
        v-model="filters.projectId"
        clearable
        filterable
        placeholder="按项目筛选（可选）"
        style="width: 320px"
        @change="loadTasks"
      >
        <el-option v-for="p in projects" :key="p.id" :label="`${p.code} ${p.name}`" :value="String(p.id)" />
      </el-select>

      <el-select v-model="filters.status" clearable placeholder="按状态筛选（本地）" style="width: 180px">
        <el-option value="TODO" label="未开始" />
        <el-option value="DOING" label="进行中" />
        <el-option value="DONE" label="已完成" />
      </el-select>

      <el-input v-model="filters.keyword" placeholder="标题关键字（本地过滤，可选）" style="width: 260px" />
    </div>

    <el-table :data="filteredTasks" height="720" @row-click="select">
      <el-table-column label="项目" width="220">
        <template #default="scope">
          <span>{{ scope.row.project_code || scope.row.project }} {{ scope.row.project_name || '' }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="title" label="任务" min-width="240" />
      <el-table-column label="状态" width="120">
        <template #default="scope">{{ statusLabel(scope.row.status) }}</template>
      </el-table-column>
      <el-table-column prop="progress_percent" label="进度%" width="90" />
      <el-table-column prop="start_date" label="开始" width="110" />
      <el-table-column prop="end_date" label="结束" width="110" />
      <el-table-column prop="sort_order" label="排序" width="90" />
      <el-table-column label="操作" width="180">
        <template #default="scope">
          <el-button size="small" @click.stop="openEdit(scope.row)">编辑</el-button>
          <el-button size="small" type="danger" @click.stop="remove(scope.row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>

  <el-dialog v-model="dialogOpen" :title="dialogMode === 'create' ? '新增任务' : '编辑任务'" width="560">
    <el-form label-width="90px">
      <el-form-item label="项目">
        <el-select v-model="form.project" filterable style="width: 100%">
          <el-option v-for="p in projects" :key="p.id" :label="`${p.code} ${p.name}`" :value="p.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="任务">
        <el-input v-model="form.title" />
      </el-form-item>
      <el-form-item label="状态">
        <el-select v-model="form.status" style="width: 100%">
          <el-option value="TODO" label="未开始" />
          <el-option value="DOING" label="进行中" />
          <el-option value="DONE" label="已完成" />
        </el-select>
      </el-form-item>
      <el-form-item label="进度%">
        <el-input-number v-model="form.progress_percent" :min="0" :max="100" />
      </el-form-item>
      <el-form-item label="开始日期">
        <el-date-picker v-model="form.start_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
      </el-form-item>
      <el-form-item label="结束日期">
        <el-date-picker v-model="form.end_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
      </el-form-item>
      <el-form-item label="排序">
        <el-input-number v-model="form.sort_order" />
      </el-form-item>
      <el-form-item label="描述">
        <el-input v-model="form.description" type="textarea" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dialogOpen = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="save">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '../lib/api'

type Project = {
  id: number
  code: string
  name: string
}

type Task = {
  id: number
  project: number
  project_code?: string
  project_name?: string
  title: string
  status: 'TODO' | 'DOING' | 'DONE'
  start_date: string | null
  end_date: string | null
  progress_percent: number
  description: string
  sort_order: number
  created_at: string
}

const projects = ref<Project[]>([])
const tasks = ref<Task[]>([])
const selected = ref<Task | null>(null)

const filters = reactive({
  projectId: '' as string,
  status: '' as '' | Task['status'],
  keyword: '' as string
})

const dialogOpen = ref(false)
const dialogMode = ref<'create' | 'edit'>('create')
const saving = ref(false)

const form = reactive({
  id: 0,
  project: 0,
  title: '',
  status: 'TODO' as Task['status'],
  start_date: '' as string | '',
  end_date: '' as string | '',
  progress_percent: 0,
  description: '',
  sort_order: 0
})

const filteredTasks = computed(() => {
  let list = tasks.value
  if (filters.status) list = list.filter((t) => t.status === filters.status)
  const kw = filters.keyword.trim()
  if (kw) list = list.filter((t) => (t.title || '').includes(kw))
  return list
})

function statusLabel(s: Task['status']) {
  if (s === 'TODO') return '未开始'
  if (s === 'DOING') return '进行中'
  return '已完成'
}

function select(row: Task) {
  selected.value = row
}

async function loadProjects() {
  try {
    const resp = await api.get('/projects/')
    projects.value = resp.data
  } catch {
    projects.value = []
  }
}

async function loadTasks() {
  try {
    const params: Record<string, string> = {}
    if (filters.projectId) params.project = filters.projectId
    const resp = await api.get('/tasks/', { params })
    tasks.value = resp.data
  } catch {
    tasks.value = []
    ElMessage.error('加载任务失败')
  }
}

function openCreate() {
  dialogMode.value = 'create'
  form.id = 0
  form.project = Number(filters.projectId) || projects.value[0]?.id || 0
  form.title = ''
  form.status = 'TODO'
  form.start_date = ''
  form.end_date = ''
  form.progress_percent = 0
  form.description = ''
  form.sort_order = 0
  dialogOpen.value = true
}

function openEdit(row: Task) {
  dialogMode.value = 'edit'
  form.id = row.id
  form.project = row.project
  form.title = row.title
  form.status = row.status
  form.start_date = row.start_date ?? ''
  form.end_date = row.end_date ?? ''
  form.progress_percent = row.progress_percent
  form.description = row.description
  form.sort_order = row.sort_order
  dialogOpen.value = true
}

async function save() {
  if (!form.project) {
    ElMessage.warning('请选择项目')
    return
  }
  if (!form.title.trim()) {
    ElMessage.warning('请输入任务标题')
    return
  }
  saving.value = true
  try {
    const payload = {
      project: form.project,
      title: form.title,
      status: form.status,
      start_date: form.start_date || null,
      end_date: form.end_date || null,
      progress_percent: form.progress_percent,
      description: form.description,
      sort_order: form.sort_order
    }
    if (dialogMode.value === 'create') {
      await api.post('/tasks/', payload)
    } else {
      await api.patch(`/tasks/${form.id}/`, payload)
    }
    dialogOpen.value = false
    await loadTasks()
  } catch {
    ElMessage.error('保存失败（需要系统管理员或项目管理员权限）')
  } finally {
    saving.value = false
  }
}

async function remove(row: Task) {
  try {
    await ElMessageBox.confirm(`确认删除任务：${row.title}？`, '确认删除', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消'
    })
    await api.delete(`/tasks/${row.id}/`)
    if (selected.value?.id === row.id) selected.value = null
    await loadTasks()
  } catch {
    // cancelled or failed
  }
}

onMounted(async () => {
  await loadProjects()
  await loadTasks()
})
</script>
