<template>
  <div class="history-page">
    <!-- 主内容区域 -->
    <div class="history-content">
      <!-- Header Area -->
      <div class="page-header-card">
        <div class="header-info">
          <h1 class="page-title">我的创作</h1>
        </div>
        <div class="header-actions">
          <button class="btn btn-primary btn-sm" @click="router.push('/')">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <line x1="12" y1="5" x2="12" y2="19"></line>
              <line x1="5" y1="12" x2="19" y2="12"></line>
            </svg>
            新建图文
          </button>
        </div>
      </div>

      <!-- Stats Overview -->
      <StatsOverview v-if="stats" :stats="stats" />

      <!-- Toolbar: Tabs & Search -->
      <div class="toolbar-card">
        <div class="tabs-container">
          <div
            class="tab-item"
            :class="{ active: currentTab === 'all' }"
            @click="switchTab('all')"
          >
            全部
          </div>
          <div
            class="tab-item"
            :class="{ active: currentTab === 'completed' }"
            @click="switchTab('completed')"
          >
            已完成
          </div>
          <div
            class="tab-item"
            :class="{ active: currentTab === 'draft' }"
            @click="switchTab('draft')"
          >
            草稿箱
          </div>
        </div>

        <div class="search-mini">
          <svg class="icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8"></circle>
            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
          </svg>
          <input
            v-model="searchKeyword"
            type="text"
            placeholder="搜索标题..."
            @keyup.enter="handleSearch"
          />
        </div>
      </div>

      <!-- Content Area -->
      <div v-if="loading" class="loading-state">
        <div class="spinner"></div>
      </div>

      <div v-else-if="records.length === 0" class="empty-state-large">
        <div class="empty-img">
          <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path>
            <polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline>
            <line x1="12" y1="22.08" x2="12" y2="12"></line>
          </svg>
        </div>
        <h3>暂无相关记录</h3>
        <p class="empty-tips">去创建一个新的作品吧</p>
      </div>

      <div v-else class="gallery-grid">
        <GalleryCard
          v-for="record in records"
          :key="record.id"
          :record="record"
          @preview="viewImages"
          @edit="loadRecord"
          @delete="confirmDelete"
        />
      </div>

      <!-- Pagination -->
      <div v-if="totalPages > 1" class="pagination-wrapper">
        <button class="page-btn" :disabled="currentPage === 1" @click="changePage(currentPage - 1)">上一页</button>
        <span class="page-indicator">{{ currentPage }} / {{ totalPages }}</span>
        <button class="page-btn" :disabled="currentPage === totalPages" @click="changePage(currentPage + 1)">下一页</button>
      </div>
    </div>

    <!-- Image Viewer Modal -->
    <ImageGalleryModal
      v-if="viewingRecord"
      :visible="!!viewingRecord"
      :record="viewingRecord"
      :regeneratingImages="regeneratingImages"
      @close="closeGallery"
      @showOutline="showOutlineModal = true"
      @regenerate="regenerateHistoryImage"
      @downloadAll="downloadAllImages"
      @download="downloadImage"
    />

    <!-- 大纲查看模态框 -->
    <OutlineModal
      v-if="showOutlineModal && viewingRecord"
      :visible="showOutlineModal"
      :pages="viewingRecord.outline.pages"
      @close="showOutlineModal = false"
    />

  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  getHistoryList,
  getHistoryStats,
  searchHistory,
  deleteHistory,
  getHistory,
  type HistoryRecord,
  regenerateImage as apiRegenerateImage
} from '../api'

// 引入组件
import StatsOverview from '../components/history/StatsOverview.vue'
import GalleryCard from '../components/history/GalleryCard.vue'
import ImageGalleryModal from '../components/history/ImageGalleryModal.vue'
import OutlineModal from '../components/history/OutlineModal.vue'

const router = useRouter()
const route = useRoute()

// 数据状态
const records = ref<HistoryRecord[]>([])
const loading = ref(false)
const stats = ref<any>(null)
const currentTab = ref('all')
const searchKeyword = ref('')
const currentPage = ref(1)
const totalPages = ref(1)

// 查看器状态
const viewingRecord = ref<any>(null)
const regeneratingImages = ref<Set<number>>(new Set())
const showOutlineModal = ref(false)

/**
 * 加载历史记录列表
 */
async function loadData() {
  loading.value = true
  try {
    let statusFilter = currentTab.value === 'all' ? undefined : currentTab.value
    const res = await getHistoryList(currentPage.value, 12, statusFilter)
    if (res.success) {
      records.value = res.records
      totalPages.value = res.total_pages
    }
  } catch(e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

/**
 * 加载统计数据
 */
async function loadStats() {
  try {
    const res = await getHistoryStats()
    if (res.success) stats.value = res
  } catch(e) {}
}

/**
 * 切换标签页
 */
function switchTab(tab: string) {
  currentTab.value = tab
  currentPage.value = 1
  loadData()
}

/**
 * 搜索历史记录
 */
async function handleSearch() {
  if (!searchKeyword.value.trim()) {
    loadData()
    return
  }
  loading.value = true
  try {
    const res = await searchHistory(searchKeyword.value)
    if (res.success) {
      records.value = res.records
      totalPages.value = 1
    }
  } catch(e) {} finally {
    loading.value = false
  }
}

/**
 * 加载记录并跳转到编辑页
 * 改为直接跳转，由 OutlineView 根据 URL 参数加载数据
 */
async function loadRecord(id: string) {
  console.log('📝 点击编辑按钮，recordId:', id)
  try {
    // 直接跳转到 outline 页，携带 recordId 参数
    // OutlineView 会根据 recordId 从后端加载完整数据
    await router.push(`/outline?recordId=${id}`)
    console.log('✅ 已跳转到编辑页')
  } catch (err) {
    console.error('❌ 跳转失败:', err)
    alert('跳转失败，请稍后重试')
  }
}

/**
 * 查看图片
 */
async function viewImages(id: string) {
  const res = await getHistory(id)
  if (res.success) viewingRecord.value = res.record
}

/**
 * 关闭图片查看器
 */
function closeGallery() {
  viewingRecord.value = null
  showOutlineModal.value = false
}

/**
 * 确认删除
 */
async function confirmDelete(record: any) {
  if(confirm('确定删除吗？')) {
    await deleteHistory(record.id)
    loadData()
    loadStats()
  }
}

/**
 * 切换页码
 */
function changePage(p: number) {
  currentPage.value = p
  loadData()
}

/**
 * 重新生成历史记录中的图片
 */
async function regenerateHistoryImage(index: number) {
  if (!viewingRecord.value || !viewingRecord.value.id) {
    alert('无法重新生成：缺少记录信息')
    return
  }

  const page = viewingRecord.value.outline.pages[index]
  if (!page) return

  regeneratingImages.value.add(index)

  try {
    const context = {
      fullOutline: viewingRecord.value.outline.raw || '',
      userTopic: viewingRecord.value.title || ''
    }

    const result = await apiRegenerateImage(
      viewingRecord.value.id,
      page,
      true,
      context
    )

    if (result.success && result.image_url) {
      const filename = result.image_url.split('/').pop()
      
      // 刷新图片 - 重新获取完整的 record 数据
      const res = await getHistory(viewingRecord.value.id)
      if (res.success) {
        viewingRecord.value = res.record
      } else {
        // 如果重新获取失败，手动更新当前页面的图片信息
        if (viewingRecord.value.outline.pages[index]) {
          viewingRecord.value.outline.pages[index].image = {
            id: 0, // 临时值，实际应该从后端获取
            filename: filename || '',
            thumbnail_filename: `thumb_${filename || ''}`
          }
        }
      }

      regeneratingImages.value.delete(index)
    } else {
      regeneratingImages.value.delete(index)
      alert('重新生成失败: ' + (result.error || '未知错误'))
    }
  } catch (e) {
    regeneratingImages.value.delete(index)
    alert('重新生成失败: ' + String(e))
  }
}

/**
 * 下载单张图片
 */
function downloadImage(filename: string, index: number) {
  if (!viewingRecord.value) return
  const link = document.createElement('a')
  link.href = `/api/images/${viewingRecord.value.id}/${filename}?thumbnail=false`
  link.download = `page_${index + 1}.png`
  link.click()
}

/**
 * 打包下载所有图片
 */
function downloadAllImages() {
  if (!viewingRecord.value) return
  const link = document.createElement('a')
  link.href = `/api/history/${viewingRecord.value.id}/download`
  link.click()
}

onMounted(async () => {
  await loadData()
  await loadStats()

  // 检查路由参数，如果有 ID 则自动打开图片查看器
  if (route.params.id) {
    await viewImages(route.params.id as string)
  }
})
</script>

<style scoped>
/* 主容器 - 使用flex布局 */
.history-page {
  width: 100%;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.history-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-width: 1200px;
  margin: 0 auto;
  width: 100%;
  padding: 16px;
}

/* 页面头部卡片 */
.page-header-card {
  background: white;
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  padding: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

.header-info {
  flex: 1;
  min-width: 0;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-main);
  margin: 0;
  letter-spacing: -0.5px;
}

.header-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

/* 按钮样式 */
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 8px 14px;
  border: none;
  border-radius: var(--radius-sm);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}

.btn-sm {
  padding: 6px 12px;
  font-size: 12px;
}

.btn-primary {
  background: var(--primary);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: var(--primary-hover);
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(255, 36, 66, 0.3);
}

/* Toolbar */
.toolbar-card {
  background: white;
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.tabs-container {
  display: flex;
  gap: 8px;
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 12px;
}

.tab-item {
  padding: 8px 16px;
  border-radius: var(--radius-sm);
  font-size: 13px;
  font-weight: 500;
  color: var(--text-sub);
  cursor: pointer;
  transition: all 0.2s;
  user-select: none;
}

.tab-item:hover {
  background: #f9f9f9;
  color: var(--text-main);
}

.tab-item.active {
  background: var(--primary-light);
  color: var(--primary);
  font-weight: 600;
}

.search-mini {
  position: relative;
  width: 100%;
}

.search-mini input {
  width: 100%;
  padding: 8px 12px 8px 36px;
  border-radius: 100px;
  border: 1px solid var(--border-color);
  font-size: 14px;
  background: white;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.search-mini input:focus {
  border-color: var(--primary);
  outline: none;
  box-shadow: 0 0 0 3px var(--primary-light);
}

.search-mini .icon {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: #ccc;
}

/* Gallery Grid - 使用grid布局，一行显示多张卡片 */
.gallery-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
  width: 100%;
}

/* Pagination */
.pagination-wrapper {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
  margin-top: 16px;
  padding: 16px;
  background: white;
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
}

.page-btn {
  padding: 8px 16px;
  border: 1px solid var(--border-color);
  background: white;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
}

.page-btn:hover:not(:disabled) {
  background: #f9f9f9;
  border-color: var(--border-hover);
}

.page-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.page-indicator {
  font-size: 13px;
  color: var(--text-sub);
  font-weight: 500;
}

/* Empty State */
.empty-state-large {
  text-align: center;
  padding: 60px 20px;
  color: var(--text-sub);
  background: white;
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
}

.empty-img {
  font-size: 64px;
  opacity: 0.5;
  margin-bottom: 16px;
}

.empty-state-large h3 {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-main);
  margin: 0 0 8px 0;
}

.empty-state-large .empty-tips {
  margin: 0;
  color: var(--text-placeholder);
  font-size: 14px;
}

/* Loading State */
.loading-state {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 60px 20px;
  background: white;
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
}

.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--border-color);
  border-top-color: var(--primary);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* 响应式设计 */
@media (max-width: 768px) {
  .history-content {
    padding: 12px;
    gap: 12px;
  }

  .page-header-card {
    flex-direction: column;
    align-items: stretch;
    padding: 12px;
  }

  .header-actions {
    width: 100%;
  }

  .btn {
    width: 100%;
    justify-content: center;
  }

  .toolbar-card {
    padding: 12px;
  }

  .tabs-container {
    flex-wrap: wrap;
    gap: 6px;
  }

  .tab-item {
    flex: 1;
    min-width: 0;
    text-align: center;
    padding: 6px 12px;
    font-size: 12px;
  }

  .gallery-grid {
    grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
    gap: 10px;
  }

  .pagination-wrapper {
    flex-direction: column;
    gap: 12px;
    padding: 12px;
  }

  .page-btn {
    width: 100%;
  }
}

@media (max-width: 480px) {
  .history-content {
    padding: 8px;
    gap: 10px;
  }

  .page-title {
    font-size: 20px;
  }

  .gallery-grid {
    grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
    gap: 8px;
  }

  .empty-state-large {
    padding: 40px 16px;
  }

  .empty-img {
    font-size: 48px;
  }
}
</style>
