<template>
  <el-card>
    <template #header>
      <div style="display:flex;align-items:center;justify-content:space-between">
        <div style="font-weight:600">文件中心</div>
        <div />
      </div>
    </template>

    <!-- Step 1: 选择项目 -->
    <div v-if="!activeProjectId" style="max-width: 520px">
      <div style="font-weight:600;margin-bottom:8px">请选择项目</div>
      <el-select v-model="projectPick" filterable placeholder="选择项目后进入文件中心" style="width: 100%">
        <el-option v-for="p in projects" :key="p.id" :label="`${p.code} ${p.name}`" :value="String(p.id)" />
      </el-select>
      <div style="margin-top:12px">
        <el-button type="primary" :disabled="!projectPick" @click="enterProject">进入</el-button>
        <el-button @click="loadProjects">刷新项目</el-button>
      </div>
    </div>

    <!-- Step 2: 资源管理器布局 -->
    <el-container v-else style="height: 760px;border:1px solid var(--el-border-color);border-radius:6px;overflow:hidden">
      <!-- 左侧：项目/目录 -->
      <el-aside width="240px" style="border-right:1px solid var(--el-border-color);background:var(--el-bg-color)">
        <div style="padding:12px;border-bottom:1px solid var(--el-border-color)">
          <div style="font-weight:600;margin-bottom:8px">项目</div>
          <el-select v-model="activeProjectId" filterable style="width: 100%" @change="onProjectChange">
            <el-option v-for="p in projects" :key="p.id" :label="`${p.code} ${p.name}`" :value="String(p.id)" />
          </el-select>
        </div>

        <div style="padding:12px">
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px">
            <div style="font-weight:600">目录</div>
            <el-button size="small" @click="refreshTree">刷新</el-button>
          </div>
          <el-tree
            ref="treeRef"
            :data="tree"
            node-key="key"
            default-expand-all
            :highlight-current="true"
            @node-click="onTreeClick"
          />
        </div>
      </el-aside>

      <!-- 右侧：工具栏 + 路径 + 文件列表 + 详情 -->
      <el-container>
        <el-header height="84px" style="background:var(--el-bg-color);border-bottom:1px solid var(--el-border-color);padding:10px 12px">
          <!-- 快捷操作栏（回收站在这一栏） -->
          <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
            <el-input
              v-model="searchText"
              placeholder="搜索文件/内容"
              style="width: 200px"
              clearable
              @keyup.enter="doSearch"
              @clear="doSearch"
            >
              <template #append>
                <el-button @click="doSearch">搜</el-button>
              </template>
            </el-input>
            <el-upload :show-file-list="false" :disabled="viewMode !== 'files'" :http-request="doUpload">
              <el-button :disabled="viewMode !== 'files'">上传</el-button>
            </el-upload>
            <el-button :disabled="viewMode !== 'files'" @click="createFolder">新建文件夹</el-button>
            <el-button :disabled="viewMode !== 'files' || !canToolbarDownload" @click="downloadSelectedOne">下载</el-button>
            <el-button type="danger" :disabled="viewMode !== 'files' || selectedKeys.length === 0" @click="deleteSelected">删除</el-button>
            <el-switch v-model="includePersonal" active-text="显示个人区" inactive-text="隐藏个人区" @change="onTogglePersonal" />
            <el-button
              type="primary"
              plain
              @click="toggleRecycle"
            >
              {{ viewMode === 'recycle' ? '返回文件' : '回收站' }}
            </el-button>
          </div>

          <!-- 当前路径 -->
          <div style="margin-top:10px">
            <el-breadcrumb separator="/">
              <el-breadcrumb-item v-for="(seg, idx) in breadcrumb" :key="idx">
                <el-link v-if="seg.clickable" :underline="false" type="primary" @click="seg.onClick">{{ seg.label }}</el-link>
                <span v-else>{{ seg.label }}</span>
              </el-breadcrumb-item>
            </el-breadcrumb>
          </div>
        </el-header>

        <el-main style="background:var(--el-fill-color-lighter);padding:12px">
          <el-row :gutter="12" style="height: 100%">
            <!-- 文件列表 -->
            <el-col :span="16" style="height: 100%">
              <el-card style="height: 100%">
                <template #header>
                  <div style="display:flex;align-items:center;justify-content:space-between">
                    <div style="font-weight:600">{{ viewMode === 'recycle' ? '回收站' : '文件列表' }}</div>
                    <div style="color:var(--el-text-color-placeholder)">{{ viewMode === 'recycle' ? '该项目回收站' : '当前文件夹' }}</div>
                  </div>
                </template>

                <el-table
                  ref="tableRef"
                  :data="rows"
                  height="620"
                  @selection-change="onSelection"
                  @row-click="onRowClick"
                >
                  <el-table-column type="selection" width="44" />
                  <el-table-column prop="name" label="名称" min-width="240" />
                  <el-table-column v-if="viewMode === 'recycle'" prop="original_path" label="原路径" width="180" />
                  <el-table-column prop="type" label="类型" width="90" />
                  <el-table-column prop="modified" label="修改时间" width="170" />
                  <el-table-column prop="size" label="大小" width="90" />
                  <el-table-column label="操作" width="200">
                    <template #default="scope">
                      <template v-if="viewMode !== 'recycle'">
                        <el-button size="small" :disabled="scope.row.type === '文件夹'" @click.stop="previewOne(scope.row)">预览</el-button>
                        <el-button size="small" :disabled="scope.row.type === '文件夹'" @click.stop="downloadOne(scope.row)">下载</el-button>
                        <el-button size="small" type="danger" @click.stop="deleteOne(scope.row)">删除</el-button>
                      </template>
                      <template v-else>
                        <el-button size="small" type="primary" @click.stop="restoreOne(scope.row)">恢复</el-button>
                        <el-button size="small" type="danger" @click.stop="purgeOne(scope.row)">彻底删除</el-button>
                      </template>
                    </template>
                  </el-table-column>
                </el-table>
              </el-card>
            </el-col>

            <!-- 右侧详情 -->
            <el-col :span="8" style="height: 100%">
              <el-card style="height: 100%">
                <template #header>
                  <div style="display:flex;align-items:center;justify-content:space-between">
                    <div style="font-weight:600">详细信息</div>
                    <el-button size="small" @click="clearFocus">清除</el-button>
                  </div>
                </template>

                <div v-if="focused">
                  <el-descriptions :column="1" border>
                    <el-descriptions-item label="名称">{{ focused.name }}</el-descriptions-item>
                    <el-descriptions-item label="类型">{{ focused.type }}</el-descriptions-item>
                    <el-descriptions-item label="个人区">{{ focused.is_personal ? '是' : '否' }}</el-descriptions-item>
                    <el-descriptions-item label="大小">{{ focused.size }}</el-descriptions-item>
                    <el-descriptions-item label="修改时间">{{ focused.modified }}</el-descriptions-item>
                    <el-descriptions-item label="路径">{{ breadcrumbText }}</el-descriptions-item>
                  </el-descriptions>

                  <div style="margin-top:12px;display:flex;gap:8px;flex-wrap:wrap">
                    <template v-if="viewMode !== 'recycle'">
                      <el-button :disabled="!canRenameMove" @click="renameFocused">重命名</el-button>
                      <el-button :disabled="!canRenameMove" @click="moveFocused">移动</el-button>
                      <el-button :disabled="focused.type === '文件夹'" @click="openVersions(focused)">历史版本</el-button>
                      <el-switch
                        v-model="focusedPersonalSwitch"
                        active-text="设为个人区"
                        inactive-text="取消个人区"
                        @change="toggleFocusedPersonal"
                      />
                      <el-button :disabled="focused.type === '文件夹'" @click="previewOne(focused)">预览</el-button>
                      <el-button :disabled="focused.type === '文件夹'" @click="downloadOne(focused)">下载</el-button>
                      <el-button type="danger" @click="deleteOne(focused)">删除</el-button>
                    </template>
                    <template v-else>
                      <el-button type="primary" @click="restoreOne(focused)">恢复</el-button>
                      <el-button type="danger" @click="purgeOne(focused)">彻底删除</el-button>
                    </template>
                  </div>
                </div>
                <div v-else style="color:var(--el-text-color-placeholder)">点击左侧文件查看详细信息。</div>
              </el-card>
            </el-col>
          </el-row>
        </el-main>
      </el-container>
    </el-container>
  </el-card>

  <el-dialog v-model="versionsOpen" title="历史版本" width="640px">
    <el-table :data="versionsList" height="400">
      <el-table-column prop="version_number" label="版本号" width="80" />
      <el-table-column prop="size_bytes" label="大小" width="100">
        <template #default="scope">{{ fmtBytes(scope.row.size_bytes) }}</template>
      </el-table-column>
      <el-table-column prop="created_at" label="上传时间" width="180">
        <template #default="scope">{{ fmtTime(scope.row.created_at) }}</template>
      </el-table-column>
      <el-table-column prop="created_by" label="上传人">
        <template #default="scope">{{ scope.row.created_by?.display_name || scope.row.created_by?.username || '-' }}</template>
      </el-table-column>
    </el-table>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, h, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, ElTree } from 'element-plus'
import { api } from '../lib/api'

type Project = { id: number; code: string; name: string }

type TreeNode = { key: string; label: string; children?: TreeNode[] }

type Row = {
  key: string
  id: number
  name: string
  type: '文件夹' | '文件'
  modified: string
  size: string
  parent: number | null
  is_dir: boolean
  deleted_at?: string | null
  is_personal: boolean
  owner_user: number | null
  original_path?: string
}

type DirNode = { id: number; name: string; parent: number | null }

type UploadRequestOptions = {
  file: File
  onSuccess?: (response: any) => void
  onError?: (error: any) => void
}

const route = useRoute()
const router = useRouter()

const projects = ref<Project[]>([])
const projectPick = ref('')
const activeProjectId = ref('')

const viewMode = ref<'files' | 'recycle'>('files')
const searchText = ref('')

const includePersonal = ref(false)

const treeRef = ref<any>(null)
const tableRef = ref<any>(null)

const tree = ref<TreeNode[]>([])
const dirMap = ref<Record<string, DirNode>>({})

const currentFolderKey = ref('root')
const focused = ref<Row | null>(null)
const selectedKeys = ref<string[]>([])
const selectedRows = ref<Row[]>([])

const listRows = ref<Row[]>([])
const versionsOpen = ref(false)
const versionsList = ref<any[]>([])

const breadcrumb = computed(() => {
  const projectSeg = projects.value.find((p) => String(p.id) === activeProjectId.value)
  const projectLabel = projectSeg ? `${projectSeg.code} ${projectSeg.name}` : (activeProjectId.value || '-')

  const segs: Array<{ label: string; clickable: boolean; onClick?: () => void }> = [
    { label: '项目', clickable: false },
    { label: projectLabel, clickable: false }
  ]

  if (viewMode.value === 'recycle') {
    segs.push({
      label: '回收站',
      clickable: false
    })
    return segs
  }

  segs.push({ label: '根目录', clickable: currentFolderKey.value !== 'root', onClick: () => setFolder('root') })

  // 多级面包屑：根据 dirMap 追溯 parent
  if (currentFolderKey.value !== 'root') {
    const chain: DirNode[] = []
    let cursor = dirMap.value[currentFolderKey.value]
    while (cursor) {
      chain.unshift(cursor)
      if (cursor.parent == null) break
      cursor = dirMap.value[String(cursor.parent)]
    }
    chain.forEach((n, idx) => {
      const isLast = idx === chain.length - 1
      segs.push({
        label: n.name,
        clickable: !isLast,
        onClick: () => setFolder(String(n.id))
      })
    })
  }
  return segs
})

const breadcrumbText = computed(() => breadcrumb.value.map((s) => s.label).join(' / '))

const rows = computed<Row[]>(() => listRows.value)

const canToolbarDownload = computed(() => {
  if (selectedRows.value.length !== 1) return false
  return selectedRows.value[0].type !== '文件夹'
})

const canRenameMove = computed(() => {
  return viewMode.value === 'files' && !!focused.value
})

async function loadProjects() {
  try {
    const resp = await api.get('/projects/')
    projects.value = resp.data
  } catch {
    projects.value = []
  }
}

function syncRoute() {
  if (!activeProjectId.value) return
  const query: Record<string, string> = {
    project: activeProjectId.value,
    view: viewMode.value
  }
  if (viewMode.value === 'files') query.folder = currentFolderKey.value
  if (includePersonal.value) query.include_personal = '1'
  if (searchText.value) query.q = searchText.value
  router.replace({ path: '/files', query })
}

function onTogglePersonal() {
  syncRoute()
  focused.value = null
  selectedKeys.value = []
  void loadTree()
  void loadList()
}

async function setFolder(folderKey: string) {
  currentFolderKey.value = folderKey
  focused.value = null
  selectedKeys.value = []
  if (treeRef.value && typeof treeRef.value.setCurrentKey === 'function') {
    treeRef.value.setCurrentKey(folderKey)
  }
  syncRoute()
  await loadList()
}

function enterProject() {
  if (!projectPick.value) return
  activeProjectId.value = projectPick.value
  currentFolderKey.value = 'root'
  syncRoute()
}

function onProjectChange() {
  currentFolderKey.value = 'root'
  searchText.value = ''
  syncRoute()
  focused.value = null
  selectedKeys.value = []
  if (treeRef.value && typeof treeRef.value.setCurrentKey === 'function') {
    treeRef.value.setCurrentKey('root')
  }
}

function refreshTree() {
  void loadTree()
}

function onTreeClick(node: TreeNode) {
  void setFolder(node.key)
}

function toggleRecycle() {
  viewMode.value = viewMode.value === 'recycle' ? 'files' : 'recycle'
  searchText.value = ''
  syncRoute()
  focused.value = null
  selectedKeys.value = []
  void loadList()
}

function onSelection(rows: Row[]) {
  selectedRows.value = rows
  selectedKeys.value = rows.map((r) => r.key)
}

function onRowClick(row: Row) {
  if (viewMode.value !== 'files') {
    focused.value = row
    return
  }
  if (row.type === '文件夹') {
    void setFolder(row.key)
    return
  }
  focused.value = row
}

function clearFocus() {
  focused.value = null
}

async function createFolder() {
  if (!activeProjectId.value) return
  if (viewMode.value !== 'files') return
  try {
    const { value } = await ElMessageBox.prompt('请输入文件夹名称', '新建文件夹', {
      confirmButtonText: '创建',
      cancelButtonText: '取消',
      inputPlaceholder: '例如：assets',
      inputValidator: (v: string) => {
        const s = (v || '').trim()
        if (!s) return '请输入名称'
        if (s.length > 255) return '名称过长'
        if (/[\\/]/.test(s)) return '名称不能包含 / 或 \\ '
        return true
      }
    })

    const name = (value || '').trim()
    const parent = currentFolderKey.value === 'root' ? null : Number(currentFolderKey.value)
    await api.post('/files/folders/', {
      project: Number(activeProjectId.value),
      parent,
      name
    })
    ElMessage.success('已创建')
    await loadTree()
    await loadList()
  } catch (e: any) {
    if (e?.name === 'CanceledError' || e === 'cancel' || e === 'cancelled') return
    ElMessage.error(e?.response?.data?.detail || '创建失败（需要项目管理员或系统管理员权限）')
  }
}

async function renameFocused() {
  if (!focused.value) return
  if (viewMode.value !== 'files') return
  try {
    const cur = focused.value
    const { value } = await ElMessageBox.prompt('请输入新名称', '重命名', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      inputValue: cur.name,
      inputValidator: (v: string) => {
        const s = (v || '').trim()
        if (!s) return '请输入名称'
        if (s.length > 255) return '名称过长'
        if (/[\\/]/.test(s)) return '名称不能包含 / 或 \\ '
        return true
      }
    })

    const name = (value || '').trim()
    await api.post(`/files/${cur.id}/rename/`, { name })
    ElMessage.success('已重命名')
    focused.value = { ...cur, name }
    await loadTree()
    await loadList()
  } catch (e: any) {
    if (e?.name === 'CanceledError' || e === 'cancel' || e === 'cancelled') return
    ElMessage.error(e?.response?.data?.detail || '重命名失败（需要项目管理员或系统管理员权限）')
  }
}

async function moveFocused() {
  if (!focused.value) return
  if (viewMode.value !== 'files') return
  try {
    const cur = focused.value
    if (!tree.value.length) {
      await loadTree()
    }

    let pickedKey = 'root'
    await ElMessageBox({
      title: '选择目标文件夹',
      message: h(
        'div',
        { style: 'max-height: 360px; overflow: auto; padding: 4px 0' },
        h(ElTree, {
          data: tree.value,
          nodeKey: 'key',
          defaultExpandAll: true,
          highlightCurrent: true,
          currentNodeKey: currentFolderKey.value || 'root',
          onNodeClick: (node: any) => {
            pickedKey = String(node?.key || 'root')
          }
        })
      ),
      showCancelButton: true,
      confirmButtonText: '移动到此处',
      cancelButtonText: '取消',
      closeOnClickModal: false
    })

    const parent = pickedKey === 'root' ? null : Number(pickedKey)

    await api.post(`/files/${cur.id}/move/`, { parent })
    ElMessage.success('已移动')

    // 移动后当前列表可能不再包含该条目，直接清理焦点/选择
    focused.value = null
    selectedKeys.value = []
    if (tableRef.value && typeof tableRef.value.clearSelection === 'function') {
      tableRef.value.clearSelection()
    }
    await loadTree()
    await loadList()
  } catch (e: any) {
    if (e?.name === 'CanceledError' || e === 'cancel' || e === 'cancelled') return
    ElMessage.error(e?.response?.data?.detail || '移动失败（需要项目管理员或系统管理员权限）')
  }
}

async function doUpload(opts: UploadRequestOptions) {
  if (!activeProjectId.value) return
  if (viewMode.value !== 'files') return
  try {
    const fd = new FormData()
    fd.append('project', activeProjectId.value)
    if (currentFolderKey.value !== 'root') fd.append('parent', currentFolderKey.value)
    fd.append('file', opts.file)

    // 如果是覆盖更新（选中了文件且只选中了一个）
    // 但这里是通用上传按钮，通常是新增。
    // 若要支持覆盖更新，需要在详情面板提供“上传新版本”按钮，或者检测同名。
    // 目前后端 upload 接口是新建，若同名会报错。
    // 我们在详情面板加一个“更新内容”按钮比较好。
    // 这里保持原样：新增文件。

    await api.post('/files/upload/', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
    ElMessage.success('上传成功')
    opts.onSuccess?.({ ok: true })
    await loadTree()
    await loadList()
  } catch (e: any) {
    opts.onError?.(e)
    ElMessage.error(e?.response?.data?.detail || '上传失败（需要项目管理员或系统管理员权限）')
  }
}

async function openVersions(row: Row) {
  if (!row?.id) return
  try {
    const resp = await api.get(`/files/${row.id}/versions/`)
    versionsList.value = resp.data
    versionsOpen.value = true
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '获取版本失败')
  }
}

async function doSearch() {
  if (!activeProjectId.value) return
  if (!searchText.value.trim()) {
    // 清空搜索，回到当前目录
    await loadList()
    return
  }
  
  // 搜索模式下，不依赖 currentFolderKey，而是全项目搜索
  // 但为了保持 UI 状态，我们不改变 currentFolderKey，只是列表展示搜索结果
  // 并且面包屑可能需要提示“搜索结果”
  
  try {
    const resp = await api.get('/files/search/', {
      params: {
        project: activeProjectId.value,
        q: searchText.value,
        include_personal: includePersonal.value ? '1' : '0'
      }
    })
    const items = resp.data as any[]
    listRows.value = items.map((x) => ({
      key: String(x.id),
      id: x.id,
      name: x.name,
      type: x.is_dir ? '文件夹' : '文件',
      modified: fmtTime(x.updated_at),
      size: x.is_dir ? '-' : fmtBytes(x.size_bytes || 0),
      parent: x.parent ?? null,
      is_dir: !!x.is_dir,
      deleted_at: x.deleted_at,
      is_personal: !!x.is_personal,
      owner_user: x.owner_user ?? null
    }))
    syncRoute()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '搜索失败')
  }
}

async function downloadOne(row: Row) {
  if (!row?.id) return
  if (row.type === '文件夹') return
  try {
    const resp = await api.get(`/files/${row.id}/download/`)
    const url = resp.data?.url
    if (!url) {
      ElMessage.error('下载链接为空')
      return
    }
    window.open(url, '_blank')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '下载失败')
  }
}

async function previewOne(row: Row) {
  if (!row?.id) return
  if (row.type === '文件夹') return
  try {
    const resp = await api.get(`/files/${row.id}/preview/`)
    const url = resp.data?.url
    if (!url) {
      ElMessage.error('预览链接为空')
      return
    }
    window.open(url, '_blank')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '预览失败')
  }
}

function downloadSelectedOne() {
  if (!canToolbarDownload.value) return
  void downloadOne(selectedRows.value[0])
}

async function deleteSelected() {
  const ids = selectedKeys.value.map((k) => Number(k)).filter((n) => Number.isFinite(n))
  if (!activeProjectId.value || viewMode.value !== 'files' || ids.length === 0) return
  try {
    await ElMessageBox.confirm(`确定删除选中的 ${ids.length} 项吗？`, '删除', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await Promise.all(ids.map((id) => api.post(`/files/${id}/delete/`)))
    ElMessage.success('已移入回收站')
    selectedKeys.value = []
    focused.value = null
    if (tableRef.value && typeof tableRef.value.clearSelection === 'function') {
      tableRef.value.clearSelection()
    }
    await loadTree()
    await loadList()
  } catch (e: any) {
    if (e?.name === 'CanceledError' || e === 'cancel' || e === 'cancelled') return
    ElMessage.error(e?.response?.data?.detail || '删除失败（需要项目管理员或系统管理员权限）')
  }
}

async function deleteOne(row: Row) {
  if (!row?.id) return
  try {
    await ElMessageBox.confirm(`确定删除“${row.name}”吗？`, '删除', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await api.post(`/files/${row.id}/delete/`)
    ElMessage.success('已移入回收站')
    focused.value = null
    if (tableRef.value && typeof tableRef.value.clearSelection === 'function') {
      tableRef.value.clearSelection()
    }
    await loadTree()
    await loadList()
  } catch (e: any) {
    if (e?.name === 'CanceledError' || e === 'cancel' || e === 'cancelled') return
    ElMessage.error(e?.response?.data?.detail || '删除失败（需要项目管理员或系统管理员权限）')
  }
}

async function restoreOne(row: Row) {
  if (!row?.id) return
  try {
    await api.post(`/files/${row.id}/restore/`)
    ElMessage.success('已恢复')
    focused.value = null
    if (tableRef.value && typeof tableRef.value.clearSelection === 'function') {
      tableRef.value.clearSelection()
    }
    await loadTree()
    await loadList()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '恢复失败（需要项目管理员或系统管理员权限）')
  }
}

async function purgeOne(row: Row) {
  if (!row?.id) return
  try {
    await ElMessageBox.confirm(`确定彻底删除“${row.name}”吗？该操作不可恢复。`, '彻底删除', {
      confirmButtonText: '彻底删除',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await api.delete(`/files/${row.id}/purge/`)
    ElMessage.success('已彻底删除')
    focused.value = null
    if (tableRef.value && typeof tableRef.value.clearSelection === 'function') {
      tableRef.value.clearSelection()
    }
    await loadTree()
    await loadList()
  } catch (e: any) {
    if (e?.name === 'CanceledError' || e === 'cancel' || e === 'cancelled') return
    ElMessage.error(e?.response?.data?.detail || '彻底删除失败（需要项目管理员或系统管理员权限）')
  }
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

function buildTreeNodes(dirs: DirNode[]): { tree: TreeNode[]; map: Record<string, DirNode> } {
  const map: Record<string, DirNode> = {}
  dirs.forEach((d) => {
    map[String(d.id)] = d
  })

  const childrenMap: Record<string, TreeNode[]> = {}
  dirs.forEach((d) => {
    const parentKey = d.parent == null ? 'root' : String(d.parent)
    if (!childrenMap[parentKey]) childrenMap[parentKey] = []
    childrenMap[parentKey].push({ key: String(d.id), label: d.name })
  })

  const attach = (node: TreeNode) => {
    const kids = childrenMap[node.key]
    if (kids && kids.length) {
      node.children = kids.sort((a, b) => a.label.localeCompare(b.label))
      node.children.forEach(attach)
    }
  }

  const root: TreeNode = { key: 'root', label: '根目录' }
  attach(root)
  return { tree: [root], map }
}

async function loadTree() {
  if (!activeProjectId.value) return
  const resp = await api.get('/files/tree/', {
    params: { project: activeProjectId.value, include_personal: includePersonal.value ? '1' : '0' }
  })
  const dirs: DirNode[] = resp.data
  const built = buildTreeNodes(dirs)
  tree.value = built.tree
  dirMap.value = built.map
  if (treeRef.value && typeof treeRef.value.setCurrentKey === 'function') {
    treeRef.value.setCurrentKey(currentFolderKey.value)
  }
}

async function loadList() {
  if (!activeProjectId.value) {
    listRows.value = []
    return
  }

  if (viewMode.value === 'recycle') {
    const resp = await api.get('/files/recycle/', {
      params: { project: activeProjectId.value, include_personal: includePersonal.value ? '1' : '0' }
    })
    const items = resp.data as any[]
    listRows.value = items.map((x) => ({
      key: String(x.id),
      id: x.id,
      name: x.name,
      type: x.is_dir ? '文件夹' : '文件',
      modified: fmtTime(x.deleted_at || x.updated_at),
      size: x.is_dir ? '-' : fmtBytes(x.size_bytes || 0),
      parent: x.parent ?? null,
      is_dir: !!x.is_dir,
      deleted_at: x.deleted_at,
      is_personal: !!x.is_personal,
      owner_user: x.owner_user ?? null,
      original_path: x.original_path || ''
    }))
    return
  }

  if (searchText.value.trim()) {
    await doSearch()
    return
  }

  const folder = currentFolderKey.value || 'root'
  const resp = await api.get('/files/', {
    params: {
      project: activeProjectId.value,
      folder,
      include_personal: includePersonal.value ? '1' : '0'
    }
  })
  const items = resp.data as any[]
  listRows.value = items.map((x) => ({
    key: String(x.id),
    id: x.id,
    name: x.name,
    type: x.is_dir ? '文件夹' : '文件',
    modified: fmtTime(x.updated_at),
    size: x.is_dir ? '-' : fmtBytes(x.size_bytes || 0),
    parent: x.parent ?? null,
    is_dir: !!x.is_dir,
    deleted_at: x.deleted_at,
    is_personal: !!x.is_personal,
    owner_user: x.owner_user ?? null
  }))
}

const focusedPersonalSwitch = computed({
  get: () => !!focused.value?.is_personal,
  set: (v: boolean) => {
    if (focused.value) focused.value.is_personal = v
  }
})

async function toggleFocusedPersonal() {
  if (!focused.value) return
  if (viewMode.value !== 'files') return
  try {
    const id = focused.value.id
    const is_personal = !!focused.value.is_personal
    const resp = await api.post(`/files/${id}/personalize/`, { is_personal })
    const data = resp.data?.data
    if (data && focused.value) {
      focused.value.is_personal = !!data.is_personal
      focused.value.owner_user = data.owner_user ?? null
    }
    ElMessage.success('已更新')
    await loadTree()
    await loadList()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '设置失败')
    // 回滚 UI 开关
    if (focused.value) focused.value.is_personal = !focused.value.is_personal
  }
}

onMounted(async () => {
  await loadProjects()
  const qp = typeof route.query.project === 'string' ? route.query.project : ''
  const qv = typeof route.query.view === 'string' ? route.query.view : ''
  const qf = typeof route.query.folder === 'string' ? route.query.folder : ''
  const qip = typeof route.query.include_personal === 'string' ? route.query.include_personal : ''
  if (qp) {
    activeProjectId.value = qp
    projectPick.value = qp
  }
  if (qv === 'recycle') viewMode.value = 'recycle'
  if (qf) currentFolderKey.value = qf
  if (qip === '1') includePersonal.value = true
  if (typeof route.query.q === 'string') searchText.value = route.query.q

  if (activeProjectId.value) {
    await loadTree()
    await loadList()
  }
})
</script>
