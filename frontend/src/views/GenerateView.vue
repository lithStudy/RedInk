<template>
  <div class="generate-page">
    <div class="generate-content">
      <div class="page-header-card">
        <div class="header-info">
          <h1 class="page-title">生成结果</h1>
          <p class="page-subtitle">查看已生成的图片</p>
        </div>
        <div class="header-actions">
          <button class="btn btn-secondary btn-sm" @click="goBackToOutline">
            返回大纲
          </button>
        </div>
      </div>

      <div class="images-grid">
        <div v-for="image in images" :key="image.index" class="image-card">
          <!-- 图片展示区域 -->
          <div v-if="image.url && image.status === 'done'" class="image-preview">
            <img :src="image.url" :alt="`第 ${image.index + 1} 页`" />
            <!-- 重新生成按钮（悬停显示） -->
            <div class="image-overlay">
              <button
                class="overlay-btn"
                @click="regenerateImage(image.index)"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M23 4v6h-6"></path>
                  <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
                </svg>
                重新生成
              </button>
            </div>
          </div>

          <!-- 生成中/重试中状态 -->
          <div v-else-if="image.status === 'generating' || image.status === 'retrying'" class="image-placeholder">
            <div class="spinner"></div>
            <div class="status-text">{{ image.status === 'retrying' ? '重试中...' : '生成中...' }}</div>
          </div>

          <!-- 失败状态 -->
          <div v-else-if="image.status === 'error'" class="image-placeholder error-placeholder">
            <div class="error-icon">!</div>
            <div class="status-text">生成失败</div>
            <button
              class="retry-btn"
              @click="retrySingleImage(image.index)"
            >
              点击重试
            </button>
          </div>

          <!-- 等待中状态 -->
          <div v-else class="image-placeholder">
            <div class="status-text">等待中</div>
          </div>

          <!-- 底部信息栏 -->
          <div class="image-footer">
            <span class="page-label">Page {{ image.index + 1 }}</span>
            <span class="status-badge" :class="image.status">
              {{ getStatusText(image.status) }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { regenerateImage as apiRegenerateImage, getHistory, updateHistory, type Page } from '../api'

const router = useRouter()
const route = useRoute()

// 本地状态
const recordId = ref<string | null>(null)
const topic = ref<string>('')
const outline = ref<{
  raw: string
  pages: Page[]
  metadata?: {
    title: string
    content: string
    tags: string
  }
}>({
  raw: '',
  pages: [],
  metadata: undefined
})
const images = ref<Array<{
  page_id: number
  index: number
  url: string
  status: 'generating' | 'done' | 'error' | 'retrying'
}>>([])


const getStatusText = (status: string) => {
  const texts: Record<string, string> = {
    generating: '生成中',
    done: '已完成',
    error: '失败',
    retrying: '重试中'
  }
  return texts[status] || '等待中'
}

// 重试单张图片（异步并发执行，不阻塞）
function retrySingleImage(index: number) {
  if (!recordId.value) return

  const page = outline.value.pages.find(p => p.index === index)
  if (!page) return

  // 立即设置为重试状态
  const img = images.value.find(img => img.index === index)
  if (img) {
    img.status = 'retrying'
  }

  // 构建上下文信息
  const context = {
    fullOutline: outline.value.raw || '',
    userTopic: topic.value || ''
  }

  // 异步执行重绘，不阻塞
  apiRegenerateImage(recordId.value, page, true, context)
    .then(async result => {
      if (result.success && result.image_url) {
        if (img) {
          img.url = `${result.image_url}?t=${Date.now()}`
          img.status = 'done'
        }
        // 重新加载数据以确保同步
        if (recordId.value) {
          await loadData(recordId.value)
        }
      } else {
        if (img) {
          img.status = 'error'
        }
      }
    })
    .catch(e => {
      if (img) {
        img.status = 'error'
      }
    })
}

// 重新生成图片（成功的也可以重新生成，立即返回不等待）
function regenerateImage(index: number) {
  retrySingleImage(index)
}

// 返回大纲页
function goBackToOutline() {
  if (recordId.value) {
    router.push(`/outline?recordId=${recordId.value}`)
  } else {
    router.push('/outline')
  }
}

// 从后端加载数据
async function loadData(recordIdParam: string) {
  try {
    const res = await getHistory(recordIdParam)
    if (res.success && res.record) {
      const record = res.record
      recordId.value = record.id
      topic.value = record.topic || record.title || ''
      outline.value = {
        raw: record.outline.raw || '',
        pages: record.outline.pages || [],
        metadata: record.outline.metadata
      }
      
      // 从 record.outline.pages 中直接获取图片信息
      images.value = record.outline.pages.map((page) => {
        if (page.image?.filename) {
          const timestamp = Date.now()
          const filename = page.image.filename
          return {
            page_id: page.id!,
            index: page.index,
            url: `/api/images/${record.id}/${filename}?t=${timestamp}`,
            status: 'done' as const
          }
        }
        return {
          page_id: page.id!,
          index: page.index,
          url: '',
          status: 'error' as const
        }
      })
    }
  } catch (e) {
    console.error('❌ 加载数据失败:', e)
  }
}

onMounted(async () => {
  const recordIdParam = route.query.recordId as string
  
  if (recordIdParam) {
    console.log('🔄 从后端加载任务数据:', recordIdParam)
    await loadData(recordIdParam)
  }
  
  // 检查是否有数据
  if (outline.value.pages.length === 0) {
    router.push('/')
    return
  }
})
</script>

<style scoped>
/* 主容器 - 使用flex布局 */
.generate-page {
  width: 100%;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.generate-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-width: 1400px;
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
  align-items: flex-start;
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
  margin: 0 0 6px 0;
  letter-spacing: -0.5px;
}

.page-subtitle {
  font-size: 13px;
  color: var(--text-sub);
  margin: 0;
  line-height: 1.5;
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

.btn-secondary {
  background: white;
  color: var(--text-main);
  border: 1px solid var(--border-color);
}

.btn-secondary:hover:not(:disabled) {
  background: #f9f9f9;
  border-color: var(--border-hover);
}

/* 图片网格 - 使用flex布局 */
.images-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  width: 100%;
}

.image-card {
  flex: 0 0 calc(25% - 12px);
  min-width: 200px;
  background: white;
  border-radius: var(--radius-sm);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  transition: box-shadow 0.2s;
}

.image-card:hover {
  box-shadow: var(--shadow-md);
}

.image-preview {
  aspect-ratio: 3/4;
  overflow: hidden;
  position: relative;
  flex: 1;
}

.image-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.image-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.2s;
}

.image-preview:hover .image-overlay {
  opacity: 1;
}

.overlay-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: white;
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 12px;
  color: #333;
  transition: all 0.2s;
}

.overlay-btn:hover {
  background: var(--primary);
  color: white;
}

.overlay-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.image-placeholder {
  aspect-ratio: 3/4;
  background: #f9f9f9;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  flex: 1;
  min-height: 200px;
}

.error-placeholder {
  background: #fff5f5;
}

.error-icon {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #ff4d4f;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  font-weight: bold;
}

.status-text {
  font-size: 12px;
  color: var(--text-sub);
}

.retry-btn {
  margin-top: 8px;
  padding: 6px 14px;
  background: var(--primary);
  color: white;
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 11px;
  transition: all 0.2s;
}

.retry-btn:hover {
  opacity: 0.9;
  transform: translateY(-1px);
}

.retry-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

.image-footer {
  padding: 10px 12px;
  border-top: 1px solid #f0f0f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: white;
}

.page-label {
  font-size: 11px;
  color: var(--text-sub);
}

.status-badge {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 3px;
  font-weight: 500;
}

.status-badge.done {
  background: #E6F7ED;
  color: #52C41A;
}

.status-badge.generating,
.status-badge.retrying {
  background: #E6F4FF;
  color: #1890FF;
}

.status-badge.error {
  background: #FFF1F0;
  color: #FF4D4F;
}

.spinner {
  width: 20px;
  height: 20px;
  border: 2px solid var(--primary);
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* 响应式设计 */
@media (max-width: 1024px) {
  .image-card {
    flex: 0 0 calc(33.333% - 11px);
  }
}

@media (max-width: 768px) {
  .generate-content {
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

  .images-grid {
    gap: 12px;
  }

  .image-card {
    flex: 0 0 calc(50% - 6px);
    min-width: 0;
  }
}

@media (max-width: 480px) {
  .generate-content {
    padding: 8px;
    gap: 10px;
  }

  .page-title {
    font-size: 20px;
  }

  .image-card {
    flex: 0 0 100%;
  }
}
</style>
