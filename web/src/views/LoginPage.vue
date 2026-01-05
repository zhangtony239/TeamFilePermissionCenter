<template>
  <div style="height:100vh;display:flex;align-items:center;justify-content:center;background:#f6f7fb">
    <el-card style="width:360px">
      <template #header>
        <div style="font-weight:600">登录</div>
      </template>
      <el-form @submit.prevent>
        <el-form-item label="账号">
          <el-input v-model="username" autocomplete="username" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="password" type="password" autocomplete="current-password" />
        </el-form-item>
        <el-button type="primary" style="width:100%" :loading="loading" @click="doLogin">登录</el-button>
      </el-form>
      <div style="margin-top:12px;color:#666;font-size:12px">
        开发默认账号：admin / admin1234
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { api } from '../lib/api'

const router = useRouter()

const username = ref('admin')
const password = ref('admin1234')
const loading = ref(false)

async function doLogin() {
  loading.value = true
  try {
    const resp = await api.post('/auth/login/', { username: username.value, password: password.value })
    const token = resp.data?.access
    if (!token) throw new Error('no token')
    localStorage.setItem('tfpc_token', token)
    router.push('/projects')
  } catch {
    ElMessage.error('登录失败')
  } finally {
    loading.value = false
  }
}
</script>
