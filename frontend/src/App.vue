<template>
  <div id="app">
    <!-- 收起/展开按钮（小屏模式下固定在左上角） -->
    <button 
      class="sidebar-toggle" 
      :class="{ 'mobile-toggle': isMobile }"
      @click="toggleSidebar" 
      :title="isCollapsed ? '展开菜单' : '收起菜单'"
    >
      <svg v-if="isCollapsed" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="9 18 15 12 9 6"></polyline>
      </svg>
      <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="15 18 9 12 15 6"></polyline>
      </svg>
    </button>

    <!-- 侧边栏 Sidebar -->
    <aside class="layout-sidebar" :class="{ collapsed: isCollapsed }">
      <div class="logo-area">
        <img src="/logo.png" alt="红墨" class="logo-icon" />
        <span class="logo-text" v-show="!isCollapsed">红墨</span>
      </div>
      
      <!-- 桌面端收起/展开按钮 -->
      <button 
        v-if="!isMobile"
        class="sidebar-toggle desktop-toggle" 
        @click="toggleSidebar" 
        :title="isCollapsed ? '展开菜单' : '收起菜单'"
      >
        <svg v-if="isCollapsed" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="9 18 15 12 9 6"></polyline>
        </svg>
        <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="15 18 9 12 15 6"></polyline>
        </svg>
      </button>
      
      <nav class="nav-menu">
        <RouterLink to="/" class="nav-item" active-class="active" :title="isCollapsed ? '创作中心' : ''">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="3" width="7" height="7"></rect>
            <rect x="14" y="3" width="7" height="7"></rect>
            <rect x="14" y="14" width="7" height="7"></rect>
            <rect x="3" y="14" width="7" height="7"></rect>
          </svg>
          <span v-show="!isCollapsed">创作中心</span>
        </RouterLink>
        <RouterLink to="/history" class="nav-item" active-class="active" :title="isCollapsed ? '历史记录' : ''">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
            <polyline points="14 2 14 8 20 8"></polyline>
            <line x1="16" y1="13" x2="8" y2="13"></line>
            <line x1="16" y1="17" x2="8" y2="17"></line>
            <polyline points="10 9 9 9 8 9"></polyline>
          </svg>
          <span v-show="!isCollapsed">历史记录</span>
        </RouterLink>
        <RouterLink to="/settings" class="nav-item" active-class="active" :title="isCollapsed ? '系统设置' : ''">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="3"></circle>
            <path d="M12 1v6m0 6v6m-6-6h6m6 0h-6"></path>
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
          </svg>
          <span v-show="!isCollapsed">系统设置</span>
        </RouterLink>
      </nav>
      
      <div class="sidebar-footer" v-show="!isCollapsed">
        <div class="user-info">
          <img src="/logo.png" alt="默子" class="user-avatar" />
          <div>
            <div class="user-name">默子</div>
            <div class="user-id">mozi</div>
          </div>
        </div>
      </div>
    </aside>

    <!-- 遮罩层（小屏模式下，侧边栏展开时显示） -->
    <div v-if="!isCollapsed && isMobile" class="sidebar-overlay" @click="toggleSidebar"></div>

    <!-- 主内容区 -->
    <main class="layout-main" :class="{ 'sidebar-collapsed': isCollapsed }">
      <RouterView v-slot="{ Component, route }">
        <component :is="Component" />

        <!-- 全局页脚版权信息（首页除外） -->
        <footer v-if="route.path !== '/'" class="global-footer">
          <div class="footer-content">
            <div class="footer-text">
              © 2025 <a href="https://github.com/HisMax/RedInk" target="_blank" rel="noopener noreferrer">RedInk</a> by 默子 (Histone)
            </div>
            <div class="footer-license">
              Licensed under <a href="https://creativecommons.org/licenses/by-nc-sa/4.0/" target="_blank" rel="noopener noreferrer">CC BY-NC-SA 4.0</a>
            </div>
          </div>
        </footer>
      </RouterView>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { RouterView, RouterLink } from 'vue-router'

const isCollapsed = ref(false)
const isMobile = ref(false)

// 检测屏幕尺寸
function checkMobile() {
  isMobile.value = window.innerWidth < 768
  // 小屏模式下自动收起
  if (isMobile.value) {
    isCollapsed.value = true
  }
}

// 切换侧边栏
function toggleSidebar() {
  isCollapsed.value = !isCollapsed.value
}

// 监听窗口大小变化
let resizeTimer: ReturnType<typeof setTimeout> | null = null
function handleResize() {
  if (resizeTimer) {
    clearTimeout(resizeTimer)
  }
  resizeTimer = setTimeout(() => {
    checkMobile()
  }, 100)
}

onMounted(() => {
  checkMobile()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  if (resizeTimer) {
    clearTimeout(resizeTimer)
  }
})
</script>
