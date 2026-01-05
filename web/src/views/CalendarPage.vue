<template>
  <el-card>
    <template #header>
      <div style="display:flex;align-items:center;justify-content:space-between">
        <div style="font-weight:600">日历 / 赛程</div>
        <div style="display:flex;gap:8px">
          <el-button type="primary" @click="openCreate">新增赛程</el-button>
          <el-button @click="loadEvents">刷新</el-button>
        </div>
      </div>
    </template>

    <div style="display:flex;gap:10px;align-items:center;margin-bottom:12px">
      <el-select
        v-model="filters.projectId"
        clearable
        filterable
        placeholder="按项目筛选（可选）"
        style="width: 320px"
        @change="loadEvents"
      >
        <el-option v-for="p in projects" :key="p.id" :label="`${p.code} ${p.name}`" :value="String(p.id)" />
      </el-select>
      <el-input v-model="filters.keyword" placeholder="标题关键字（本地过滤，可选）" style="width: 260px" />
    </div>

    <el-table :data="filteredEvents" height="720" @row-click="select">
      <el-table-column label="项目" width="220">
        <template #default="scope">
          <span>{{ scope.row.project_code || scope.row.project }} {{ scope.row.project_name || '' }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="title" label="标题" min-width="220" />
      <el-table-column prop="stage" label="阶段" width="140" />
      <el-table-column label="开始" width="180">
        <template #default="scope">{{ fmt(scope.row.start_at) }}</template>
      </el-table-column>
      <el-table-column label="结束" width="180">
        <template #default="scope">{{ scope.row.end_at ? fmt(scope.row.end_at) : '-' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="180">
        <template #default="scope">
          <el-button size="small" @click.stop="openEdit(scope.row)">编辑</el-button>
          <el-button size="small" type="danger" @click.stop="remove(scope.row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>

  <el-dialog v-model="dialogOpen" :title="dialogMode === 'create' ? '新增赛程' : '编辑赛程'" width="560">
    <el-form label-width="90px">
      <el-form-item label="项目">
        <el-select v-model="form.project" filterable style="width: 100%">
          <el-option v-for="p in projects" :key="p.id" :label="`${p.code} ${p.name}`" :value="p.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="标题">
        <el-input v-model="form.title" />
      </el-form-item>
      <el-form-item label="开始">
        <el-date-picker
          v-model="form.start_at"
          type="datetime"
          value-format="YYYY-MM-DDTHH:mm:ss"
          style="width: 100%"
        />
      </el-form-item>
      <el-form-item label="结束">
        <el-date-picker
          v-model="form.end_at"
          type="datetime"
          value-format="YYYY-MM-DDTHH:mm:ss"
          style="width: 100%"
          placeholder="可选"
        />
      </el-form-item>
      <el-form-item label="阶段">
        <el-input v-model="form.stage" placeholder="如：校赛/市赛/省赛/国赛 或 自定义" />
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

type Event = {
  id: number
  project: number
  project_code?: string
  project_name?: string
  title: string
  start_at: string
  end_at: string | null
  stage: string
  description: string
  created_at: string
}

const projects = ref<Project[]>([])
const events = ref<Event[]>([])
const selected = ref<Event | null>(null)

const filters = reactive({
  projectId: '' as string,
  keyword: '' as string
})

const dialogOpen = ref(false)
const dialogMode = ref<'create' | 'edit'>('create')
const saving = ref(false)

const form = reactive({
  id: 0,
  project: 0,
  title: '',
  start_at: '',
  end_at: '' as string | '',
  stage: '',
  description: ''
})

const filteredEvents = computed(() => {
  const kw = filters.keyword.trim()
  if (!kw) return events.value
  return events.value.filter((e) => (e.title || '').includes(kw))
})

function fmt(v: string) {
  if (!v) return ''
  // 兼容后端返回的 ISO 或含毫秒格式
  return v.replace('T', ' ').slice(0, 19)
}

function select(row: Event) {
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

async function loadEvents() {
  try {
    const params: Record<string, string> = {}
    if (filters.projectId) params.project = filters.projectId
    const resp = await api.get('/events/', { params })
    events.value = resp.data
  } catch {
    events.value = []
    ElMessage.error('加载赛程失败')
  }
}

function openCreate() {
  dialogMode.value = 'create'
  form.id = 0
  form.project = Number(filters.projectId) || projects.value[0]?.id || 0
  form.title = ''
  form.start_at = ''
  form.end_at = ''
  form.stage = ''
  form.description = ''
  dialogOpen.value = true
}

function openEdit(row: Event) {
  dialogMode.value = 'edit'
  form.id = row.id
  form.project = row.project
  form.title = row.title
  form.start_at = row.start_at
  form.end_at = row.end_at ?? ''
  form.stage = row.stage
  form.description = row.description
  dialogOpen.value = true
}

async function save() {
  if (!form.project) {
    ElMessage.warning('请选择项目')
    return
  }
  if (!form.title.trim()) {
    ElMessage.warning('请输入标题')
    return
  }
  if (!form.start_at) {
    ElMessage.warning('请选择开始时间')
    return
  }
  saving.value = true
  try {
    const payload = {
      project: form.project,
      title: form.title,
      start_at: form.start_at,
      end_at: form.end_at || null,
      stage: form.stage,
      description: form.description
    }
    if (dialogMode.value === 'create') {
      await api.post('/events/', payload)
    } else {
      await api.patch(`/events/${form.id}/`, payload)
    }
    dialogOpen.value = false
    await loadEvents()
  } catch {
    ElMessage.error('保存失败（需要系统管理员或项目管理员权限）')
  } finally {
    saving.value = false
  }
}

async function remove(row: Event) {
  try {
    await ElMessageBox.confirm(`确认删除赛程：${row.title}？`, '确认删除', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消'
    })
    await api.delete(`/events/${row.id}/`)
    if (selected.value?.id === row.id) selected.value = null
    await loadEvents()
  } catch {
    // cancelled or failed
  }
}

onMounted(async () => {
  await loadProjects()
  await loadEvents()
})
</script>
