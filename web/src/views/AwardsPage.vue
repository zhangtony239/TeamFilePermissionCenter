<template>
  <el-card>
    <template #header>
      <div style="display:flex;align-items:center;justify-content:space-between">
        <div style="font-weight:600">奖项库</div>
        <div style="display:flex;gap:8px">
          <el-button type="primary" @click="openCreate">新增奖项</el-button>
          <el-button @click="loadAwards">刷新</el-button>
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
        @change="loadAwards"
      >
        <el-option v-for="p in projects" :key="p.id" :label="`${p.code} ${p.name}`" :value="String(p.id)" />
      </el-select>
      <el-input v-model="filters.stage" placeholder="按阶段筛选（本地匹配，可选）" style="width: 260px" />
    </div>

    <el-table :data="filteredAwards" height="720" @row-click="select">
      <el-table-column label="项目" width="220">
        <template #default="scope">
          <span>{{ scope.row.project_code || scope.row.project }} {{ scope.row.project_name || '' }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="stage" label="阶段" width="140" />
      <el-table-column prop="title" label="奖项" min-width="220" />
      <el-table-column prop="level" label="等级" width="140" />
      <el-table-column prop="awarded_at" label="获奖日期" width="120" />
      <el-table-column label="操作" width="180">
        <template #default="scope">
          <el-button size="small" @click.stop="openEdit(scope.row)">编辑</el-button>
          <el-button size="small" type="danger" @click.stop="remove(scope.row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>

  <el-dialog v-model="dialogOpen" :title="dialogMode === 'create' ? '新增奖项' : '编辑奖项'" width="560">
    <el-form label-width="90px">
      <el-form-item label="项目">
        <el-select v-model="form.project" filterable style="width: 100%">
          <el-option v-for="p in projects" :key="p.id" :label="`${p.code} ${p.name}`" :value="p.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="阶段">
        <el-input v-model="form.stage" placeholder="如：校赛/市赛/省赛/国赛 或 自定义" />
      </el-form-item>
      <el-form-item label="奖项">
        <el-input v-model="form.title" />
      </el-form-item>
      <el-form-item label="等级">
        <el-input v-model="form.level" placeholder="如：一等奖/二等奖/金奖...（可选）" />
      </el-form-item>
      <el-form-item label="日期">
        <el-date-picker v-model="form.awarded_at" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
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

type Award = {
  id: number
  project: number
  project_code?: string
  project_name?: string
  stage: string
  title: string
  level: string
  description: string
  awarded_at: string | null
  created_at: string
}

const projects = ref<Project[]>([])
const awards = ref<Award[]>([])
const selected = ref<Award | null>(null)

const filters = reactive({
  projectId: '' as string,
  stage: '' as string
})

const dialogOpen = ref(false)
const dialogMode = ref<'create' | 'edit'>('create')
const saving = ref(false)

const form = reactive({
  id: 0,
  project: 0,
  stage: '',
  title: '',
  level: '',
  description: '',
  awarded_at: '' as string | ''
})

const filteredAwards = computed(() => {
  const stage = filters.stage.trim()
  if (!stage) return awards.value
  return awards.value.filter((a) => (a.stage || '').includes(stage))
})

function select(row: Award) {
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

async function loadAwards() {
  try {
    const params: Record<string, string> = {}
    if (filters.projectId) params.project = filters.projectId
    const resp = await api.get('/awards/', { params })
    awards.value = resp.data
  } catch {
    awards.value = []
    ElMessage.error('加载奖项失败')
  }
}

function openCreate() {
  dialogMode.value = 'create'
  form.id = 0
  form.project = projects.value[0]?.id ?? 0
  form.stage = ''
  form.title = ''
  form.level = ''
  form.description = ''
  form.awarded_at = ''
  dialogOpen.value = true
}

function openEdit(row: Award) {
  dialogMode.value = 'edit'
  form.id = row.id
  form.project = row.project
  form.stage = row.stage
  form.title = row.title
  form.level = row.level
  form.description = row.description
  form.awarded_at = row.awarded_at ?? ''
  dialogOpen.value = true
}

async function save() {
  if (!form.project) {
    ElMessage.warning('请选择项目')
    return
  }
  if (!form.title.trim()) {
    ElMessage.warning('请输入奖项名称')
    return
  }
  saving.value = true
  try {
    const payload = {
      project: form.project,
      stage: form.stage,
      title: form.title,
      level: form.level,
      description: form.description,
      awarded_at: form.awarded_at || null
    }
    if (dialogMode.value === 'create') {
      await api.post('/awards/', payload)
    } else {
      await api.patch(`/awards/${form.id}/`, payload)
    }
    dialogOpen.value = false
    await loadAwards()
  } catch {
    ElMessage.error('保存失败（需要系统管理员或项目管理员权限）')
  } finally {
    saving.value = false
  }
}

async function remove(row: Award) {
  try {
    await ElMessageBox.confirm(`确认删除奖项：${row.title}？`, '确认删除', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消'
    })
    await api.delete(`/awards/${row.id}/`)
    if (selected.value?.id === row.id) selected.value = null
    await loadAwards()
  } catch {
    // cancelled or failed
  }
}

onMounted(async () => {
  await loadProjects()
  await loadAwards()
})
</script>
