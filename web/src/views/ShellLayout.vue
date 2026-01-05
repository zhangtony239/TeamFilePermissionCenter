<template>
  <el-container style="height: 100vh">
    <el-header height="56px" style="display:flex;align-items:center;justify-content:space-between">
      <div style="font-weight:600">TeamFilePermissionCenter</div>
      <div style="display:flex;gap:12px;align-items:center">
        <el-button size="small" @click="logout">退出登录</el-button>
      </div>
    </el-header>
    <el-container>
      <el-aside width="220px">
        <el-menu :default-active="active" router>
          <el-menu-item index="/">首页</el-menu-item>
          <el-menu-item index="/projects">项目管理</el-menu-item>
          <el-menu-item index="/team">团队管理</el-menu-item>
          <el-menu-item index="/awards">奖项库</el-menu-item>
          <el-menu-item index="/calendar">日历</el-menu-item>
          <el-menu-item index="/tasks">任务看板/甘特</el-menu-item>
          <el-menu-item index="/files">文件中心</el-menu-item>
          <el-menu-item index="/audit">审计</el-menu-item>
          <el-menu-item index="/settings">系统设置</el-menu-item>
        </el-menu>
      </el-aside>
      <el-main style="background:#f6f7fb">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const active = computed(() => route.path)

function logout() {
  localStorage.removeItem('tfpc_token')
  router.push('/login')
}
</script>
