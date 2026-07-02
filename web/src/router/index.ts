import { createRouter, createWebHistory } from 'vue-router'

import LoginPage from '../views/LoginPage.vue'
import ShellLayout from '../views/ShellLayout.vue'
import DashboardPage from '../views/DashboardPage.vue'
import ProjectsPage from '../views/ProjectsPage.vue'
import TeamPage from '../views/TeamPage.vue'
import AwardsPage from '../views/AwardsPage.vue'
import CalendarPage from '../views/CalendarPage.vue'
import TasksPage from '../views/TasksPage.vue'
import FilesPage from '../views/FilesPage.vue'
import AuditPage from '../views/AuditPage.vue'
import SettingsPage from '../views/SettingsPage.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', component: LoginPage },
    {
      path: '/',
      component: ShellLayout,
      children: [
        { path: '', component: DashboardPage },
        { path: 'projects', component: ProjectsPage },
        { path: 'team', component: TeamPage },
        { path: 'awards', component: AwardsPage },
        { path: 'calendar', component: CalendarPage },
        { path: 'tasks', component: TasksPage },
        { path: 'files', component: FilesPage },
        { path: 'audit', component: AuditPage },
        { path: 'settings', component: SettingsPage }
      ]
    }
  ]
})

router.beforeEach((to) => {
  if (to.path === '/login') return true
  const token = localStorage.getItem('tfpc_token')
  if (!token) {
    // 无 access token，连同可能失效的 refresh 一并清理
    localStorage.removeItem('tfpc_refresh')
    return '/login'
  }
  return true
})
