<template>
  <el-row :gutter="12">
    <el-col :span="14">
      <el-card>
        <template #header>
          <div style="display:flex;align-items:center;justify-content:space-between">
            <div style="font-weight:600">项目管理</div>
            <div style="display:flex;gap:8px">
              <el-button type="primary" @click="openCreate">新建项目</el-button>
              <el-button @click="load">刷新</el-button>
            </div>
          </div>
        </template>

        <el-table :data="projects" height="600" @row-click="select">
          <el-table-column prop="name" label="项目" min-width="160" />
          <el-table-column prop="code" label="编码" width="140" />
          <el-table-column prop="competition_stage" label="阶段" width="120" />
          <el-table-column prop="progress_percent" label="进度%" width="90" />
          <el-table-column prop="members_count" label="成员数" width="90" />
          <el-table-column prop="start_date" label="开始" width="110" />
          <el-table-column prop="end_date" label="结束" width="110" />
        </el-table>
      </el-card>
    </el-col>

    <el-col :span="10">
      <el-card v-if="selected" style="height: 100%">
        <template #header>
          <div style="display:flex;align-items:center;justify-content:space-between">
            <div style="font-weight:600">当前项目</div>
            <div style="display:flex;gap:8px">
              <el-button size="small" @click="toggleEdit">{{ editing ? '取消编辑' : '编辑' }}</el-button>
              <el-button size="small" type="primary" :disabled="!editing" :loading="savingEdit" @click="saveEdit">保存</el-button>
              <el-button size="small" @click="reloadSelected">刷新详情</el-button>
            </div>
          </div>
        </template>

        <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:12px">
          <div>
            <div style="font-size:18px;font-weight:600">{{ selected.name }}</div>
            <div style="color:#666;margin-top:4px">{{ selected.code }}</div>
          </div>
          <div style="font-size:28px;font-weight:700">{{ selected.progress_percent }}%</div>
        </div>

        <div style="margin-top:12px">
          <el-progress :percentage="selected.progress_percent" />
        </div>

        <el-descriptions v-if="!editing" :column="1" border style="margin-top:12px">
          <el-descriptions-item label="比赛阶段">{{ stageLabel(selected.competition_stage) }}</el-descriptions-item>
          <el-descriptions-item label="创建日期">{{ selected.created_at?.slice(0, 10) }}</el-descriptions-item>
          <el-descriptions-item label="开始日期">{{ selected.start_date || '-' }}</el-descriptions-item>
          <el-descriptions-item label="结束日期">{{ selected.end_date || '-' }}</el-descriptions-item>
          <el-descriptions-item label="总进度">{{ selected.progress_percent }}%</el-descriptions-item>
          <el-descriptions-item label="描述">{{ selected.description || '-' }}</el-descriptions-item>
        </el-descriptions>

        <el-form v-else label-width="90px" style="margin-top:12px">
          <el-form-item label="名称">
            <el-input v-model="editForm.name" />
          </el-form-item>
          <el-form-item label="描述">
            <el-input v-model="editForm.description" type="textarea" />
          </el-form-item>
          <el-form-item label="状态">
            <el-select v-model="editForm.status" style="width: 100%">
              <el-option value="ACTIVE" label="进行中" />
              <el-option value="ARCHIVED" label="归档" />
              <el-option value="ENDED" label="结束" />
            </el-select>
          </el-form-item>
          <el-form-item label="开始日期">
            <el-date-picker v-model="editForm.start_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
          </el-form-item>
          <el-form-item label="结束日期">
            <el-date-picker v-model="editForm.end_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
          </el-form-item>
          <el-form-item label="阶段">
            <el-select v-model="editForm.competition_stage" style="width: 100%">
              <el-option value="SCHOOL" label="校赛" />
              <el-option value="CITY" label="市赛" />
              <el-option value="PROVINCE" label="省赛" />
              <el-option value="NATIONAL" label="国赛" />
            </el-select>
          </el-form-item>
          <el-form-item label="总进度%">
            <el-input-number v-model="editForm.progress_percent" :min="0" :max="100" />
          </el-form-item>
        </el-form>

        <el-tabs style="margin-top:12px">
          <el-tab-pane label="团队成员">
            <el-table :data="members" size="small" height="220">
              <el-table-column prop="user.display_name" label="姓名" />
              <el-table-column prop="user.username" label="账号" />
              <el-table-column prop="role" label="角色" width="120" />
              <el-table-column prop="is_active" label="在队" width="80">
                <template #default="scope">{{ scope.row.is_active ? '是' : '否' }}</template>
              </el-table-column>
            </el-table>
          </el-tab-pane>
          <el-tab-pane label="奖项">
            <el-table :data="awards" size="small" height="220">
              <el-table-column prop="stage" label="阶段" width="90" />
              <el-table-column prop="title" label="奖项" />
              <el-table-column prop="level" label="等级" width="100" />
              <el-table-column prop="awarded_at" label="日期" width="110" />
            </el-table>
          </el-tab-pane>
          <el-tab-pane label="赛程">
            <el-table :data="events" size="small" height="220">
              <el-table-column prop="title" label="标题" min-width="160" />
              <el-table-column prop="stage" label="阶段" width="90" />
              <el-table-column label="开始" width="160">
                <template #default="scope">{{ fmtDt(scope.row.start_at) }}</template>
              </el-table-column>
              <el-table-column label="结束" width="160">
                <template #default="scope">{{ scope.row.end_at ? fmtDt(scope.row.end_at) : '-' }}</template>
              </el-table-column>
            </el-table>
          </el-tab-pane>
          <el-tab-pane label="文件">
            <div style="display:flex;align-items:center;justify-content:space-between;gap:8px;flex-wrap:wrap">
              <div style="color:#666">这里会接入你的文件树/预览/ACL/回收站。</div>
              <div style="display:flex;gap:8px">
                <el-button size="small" @click="goProjectFiles">打开文件中心</el-button>
                <el-button size="small" type="primary" plain @click="goProjectRecycleBin">打开回收站</el-button>
              </div>
            </div>
          </el-tab-pane>
          <el-tab-pane label="审计">
            <el-table :data="auditLogs" size="small" height="220">
              <el-table-column label="时间" width="160">
                <template #default="scope">{{ fmtDt(scope.row.created_at) }}</template>
              </el-table-column>
              <el-table-column label="操作者" width="140">
                <template #default="scope">
                  {{ scope.row.actor?.display_name || scope.row.actor?.username || '-' }}
                </template>
              </el-table-column>
              <el-table-column prop="action" label="动作" width="140" />
              <el-table-column prop="result" label="结果" width="80" />
              <el-table-column prop="path" label="路径" min-width="180" />
            </el-table>
          </el-tab-pane>
        </el-tabs>
      </el-card>

      <el-card v-else>
        <div style="color:#666">点击左侧任意项目，在右侧查看详情。</div>
      </el-card>
    </el-col>
  </el-row>

  <el-dialog v-model="createOpen" title="新建项目" width="520">
    <el-form label-width="90px">
      <el-form-item label="编码">
        <el-input v-model="form.code" />
      </el-form-item>
      <el-form-item label="名称">
        <el-input v-model="form.name" />
      </el-form-item>
      <el-form-item label="描述">
        <el-input v-model="form.description" type="textarea" />
      </el-form-item>
      <el-form-item label="阶段">
        <el-select v-model="form.competition_stage" style="width: 100%">
          <el-option value="SCHOOL" label="校赛" />
          <el-option value="CITY" label="市赛" />
          <el-option value="PROVINCE" label="省赛" />
          <el-option value="NATIONAL" label="国赛" />
        </el-select>
      </el-form-item>
      <el-form-item label="进度%">
        <el-input-number v-model="form.progress_percent" :min="0" :max="100" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="createOpen = false">取消</el-button>
      <el-button type="primary" :loading="creating" @click="create">创建</el-button>
    </template>
  </el-dialog>

</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { api } from '../lib/api'

type Project = {
  id: number
  code: string
  name: string
  description: string
  status: string
  start_date: string | null
  end_date: string | null
  competition_stage: 'SCHOOL' | 'CITY' | 'PROVINCE' | 'NATIONAL'
  progress_percent: number
  created_at: string
  members_count?: number
}

type Membership = {
  id: number
  role: string
  is_active: boolean
  user: { id: number; username: string; display_name: string; email: string }
}

type Award = {
  id: number
  stage: string
  title: string
  level: string
  awarded_at: string | null
}

type Event = {
  id: number
  title: string
  start_at: string
  end_at: string | null
  stage: string
}

type AuditLog = {
  id: number
  created_at: string
  actor?: { id: number; username: string; display_name: string; email: string } | null
  action: string
  path: string
  result: string
}

const projects = ref<Project[]>([])
const selected = ref<Project | null>(null)
const members = ref<Membership[]>([])
const awards = ref<Award[]>([])
const events = ref<Event[]>([])
const auditLogs = ref<AuditLog[]>([])

const router = useRouter()

const createOpen = ref(false)
const creating = ref(false)

const editing = ref(false)
const savingEdit = ref(false)
const editForm = reactive({
  name: '',
  description: '',
  status: 'ACTIVE' as Project['status'],
  start_date: '' as string | '',
  end_date: '' as string | '',
  competition_stage: 'SCHOOL' as Project['competition_stage'],
  progress_percent: 0
})
const form = reactive({
  code: '',
  name: '',
  description: '',
  competition_stage: 'SCHOOL' as Project['competition_stage'],
  progress_percent: 0
})

function stageLabel(s: Project['competition_stage']) {
  if (s === 'SCHOOL') return '校赛'
  if (s === 'CITY') return '市赛'
  if (s === 'PROVINCE') return '省赛'
  return '国赛'
}

function fmtDt(v: string) {
  if (!v) return ''
  return v.replace('T', ' ').slice(0, 19)
}

async function load() {
  const resp = await api.get('/projects/')
  projects.value = resp.data
}

async function select(row: Project) {
  selected.value = row
  await reloadSelected()
}

function goProjectFiles() {
  if (!selected.value) return
  router.push({ path: '/files', query: { project: String(selected.value.id) } })
}

function goProjectRecycleBin() {
  if (!selected.value) return
  router.push({ path: '/files', query: { project: String(selected.value.id), view: 'recycle' } })
}

async function reloadSelected() {
  if (!selected.value) return
  const projectId = selected.value.id
  const [p, m, a, e, audit] = await Promise.all([
    api.get(`/projects/${projectId}/`),
    api.get(`/projects/${projectId}/members/`),
    api.get(`/awards/?project=${projectId}`),
    api.get(`/events/?project=${projectId}`),
    api.get(`/audit/?project=${projectId}`)
  ])
  selected.value = p.data
  members.value = m.data.data ?? []
  awards.value = a.data
  events.value = e.data
  auditLogs.value = audit.data
  if (editing.value && selected.value) {
    // 保持编辑态时同步表单（避免刷新后表单与详情不一致）
    const p2 = selected.value
    editForm.name = p2.name
    editForm.description = p2.description
    editForm.status = p2.status as any
    editForm.start_date = p2.start_date || ''
    editForm.end_date = p2.end_date || ''
    editForm.competition_stage = p2.competition_stage
    editForm.progress_percent = p2.progress_percent
  }
}

function toggleEdit() {
  if (!selected.value) return
  if (editing.value) {
    editing.value = false
    return
  }
  editForm.name = selected.value.name
  editForm.description = selected.value.description
  editForm.status = selected.value.status as any
  editForm.start_date = selected.value.start_date || ''
  editForm.end_date = selected.value.end_date || ''
  editForm.competition_stage = selected.value.competition_stage
  editForm.progress_percent = selected.value.progress_percent
  editing.value = true
}

async function saveEdit() {
  if (!selected.value) return
  savingEdit.value = true
  try {
    const payload = {
      name: editForm.name,
      description: editForm.description,
      status: editForm.status,
      start_date: editForm.start_date || null,
      end_date: editForm.end_date || null,
      competition_stage: editForm.competition_stage,
      progress_percent: editForm.progress_percent
    }
    const resp = await api.patch(`/projects/${selected.value.id}/`, payload)
    selected.value = resp.data
    editing.value = false
    await load()
  } catch {
    ElMessage.error('保存失败（需要系统管理员或项目管理员权限）')
  } finally {
    savingEdit.value = false
  }
}

function openCreate() {
  form.code = ''
  form.name = ''
  form.description = ''
  form.competition_stage = 'SCHOOL'
  form.progress_percent = 0
  createOpen.value = true
}

async function create() {
  creating.value = true
  try {
    const resp = await api.post('/projects/', form)
    createOpen.value = false
    await load()
    await select(resp.data)
  } catch {
    ElMessage.error('创建失败（需要系统管理员或项目管理员权限）')
  } finally {
    creating.value = false
  }
}

onMounted(load)
</script>
