import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import OutlineView from '../views/OutlineView.vue'
import GenerateView from '../views/GenerateView.vue'
import ResultView from '../views/ResultView.vue'
import HistoryView from '../views/HistoryView.vue'
import SettingsView from '../views/SettingsView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView
    },
    {
      path: '/outline',
      name: 'outline',
      component: OutlineView
      // 支持 query 参数: ?recordId=xxx 或 ?taskId=xxx
    },
    {
      path: '/generate',
      name: 'generate',
      component: GenerateView
      // 支持 query 参数: ?recordId=xxx
    },
    {
      path: '/result',
      name: 'result',
      component: ResultView
      // 支持 query 参数: ?recordId=xxx
    },
    {
      path: '/history',
      name: 'history',
      component: HistoryView
    },
    {
      path: '/history/:id',
      name: 'history-detail',
      component: HistoryView
    },
    {
      path: '/settings',
      name: 'settings',
      component: SettingsView
    }
  ]
})

export default router
