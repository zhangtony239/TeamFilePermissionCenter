<template>
  <el-card>
    <template #header>
      <div style="display:flex;align-items:center;justify-content:space-between">
        <div style="font-weight:600">审计日志</div>
        <div style="display:flex;gap:8px;align-items:center">
          <el-input v-model="filters.project" placeholder="project=项目ID（可选）" style="width:220px" />
          <el-input v-model="filters.action" placeholder="action=动作（可选）" style="width:220px" />
          <el-button type="primary" @click="load">查询</el-button>
          <el-button @click="reset">重置</el-button>
        </div>
      </div>
    </template>

    <el-table :data="logs" height="720">
      <el-table-column prop="created_at" label="时间" width="190" />
      <el-table-column label="操作者" width="180">
        <template #default="scope">
          <span>{{ scope.row.actor?.display_name || scope.row.actor?.username || '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="action" label="动作" width="160" />
      <el-table-column label="项目" width="180">
        <template #default="scope">
          <span v-if="scope.row.project">{{ scope.row.project_code || scope.row.project }} {{ scope.row.project_name || '' }}</span>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column prop="path" label="路径" min-width="240" />
      <el-table-column prop="result" label="结果" width="90" />
      <el-table-column prop="ip" label="IP" width="140" />
    </el-table>
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '../lib/api'

type AuditLog = {
  id: number
  created_at: string
  actor?: {
    id: number
    username: string
    display_name: string
    email: string
  } | null
  action: string
  project: number | null
  project_code?: string
  project_name?: string
  path: string
  result: string
  reason?: string
  ip: string
}

const logs = ref<AuditLog[]>([])
const filters = reactive({
  project: '',
  action: ''
})

function buildParams() {
  const params: Record<string, string> = {}
  if (filters.project.trim()) params.project = filters.project.trim()
  if (filters.action.trim()) params.action = filters.action.trim()
  return params
}

async function load() {
  try {
    const resp = await api.get('/audit/', { params: buildParams() })
    logs.value = resp.data
  } catch {
    ElMessage.error('加载审计日志失败')
  }
}

function reset() {
  filters.project = ''
  filters.action = ''
  load()
}

onMounted(load)
</script>
