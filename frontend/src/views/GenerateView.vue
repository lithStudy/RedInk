<template>
  <div class="container">
    <div class="page-header">
      <div>
        <h1 class="page-title">生成结果</h1>
        <p class="page-subtitle">
          查看已生成的图片
        </p>
      </div>
      <div style="display: flex; gap: 10px;">
        <button class="btn" @click="goBackToOutline" style="border:1px solid var(--border-color)">
          返回大纲
        </button>
      </div>
    </div>

    <div class="card">

      <div class="grid-cols-4" style="margin-top: 40px;">
        <div v-for="image in store.images" :key="image.index" class="image-card">
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
import { onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useGeneratorStore } from '../stores/generator'
import { regenerateImage as apiRegenerateImage, getHistory } from '../api'

const router = useRouter()
const route = useRoute()
const store = useGeneratorStore()


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
  if (!store.taskId) return

  const page = store.outline.pages.find(p => p.index === index)
  if (!page) return

  // 立即设置为重试状态
  store.setImageRetrying(index)

  // 构建上下文信息
  const context = {
    fullOutline: store.outline.raw || '',
    userTopic: store.topic || ''
  }

  // 异步执行重绘，不阻塞
  apiRegenerateImage(store.taskId, page, true, context)
    .then(result => {
      if (result.success && result.image_url) {
        store.updateImage(index, result.image_url)
      } else {
        store.updateProgress(index, 'error', undefined, result.error)
      }
    })
    .catch(e => {
      store.updateProgress(index, 'error', undefined, String(e))
    })
}

// 重新生成图片（成功的也可以重新生成，立即返回不等待）
function regenerateImage(index: number) {
  retrySingleImage(index)
}

// 返回大纲页
function goBackToOutline() {
  if (store.recordId) {
    router.push(`/outline?recordId=${store.recordId}`)
  } else {
    router.push('/outline')
  }
}


onMounted(async () => {
  const recordId = route.query.recordId as string
  
  // 如果有 recordId，从后端加载数据
  if (recordId && (!store.recordId || store.recordId !== recordId)) {
    console.log('🔄 从后端加载任务数据:', recordId)
    
    // 尝试从缓存快速恢复
    store.loadFromCache(recordId)
    
    // 从后端加载最新数据
    try {
      const res = await getHistory(recordId)
      if (res.success && res.record) {
        const record = res.record
        store.recordId = record.id
        store.taskId = record.id  // task_id 就是 record_id
        store.setTopic(record.title)
        store.setOutline(record.outline.raw, record.outline.pages, record.outline.metadata)
        
        // 从 record.outline.pages 中直接获取图片信息
        store.images = record.outline.pages.map((page) => {
          if (page.image?.filename) {
            const timestamp = Date.now()
            const filename = page.image.filename
            return {
              index: page.index,
              url: `/api/images/${record.id}/${filename}?t=${timestamp}`,
              status: 'done' as const,
              retryable: true
            }
          }
          return {
            index: page.index,
            url: '',
            status: 'error' as const,
            retryable: true
          }
        })
        
        store.saveToStorage()
      }
    } catch (e) {
      console.error('❌ 加载数据失败:', e)
    }
  }
  
  // 检查是否有数据
  if (store.outline.pages.length === 0) {
    router.push('/')
    return
  }
})
</script>

<style scoped>
.image-preview {
  aspect-ratio: 3/4;
  overflow: hidden;
  position: relative;
  flex: 1; /* 填充卡片剩余空间 */
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
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
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
  flex: 1; /* 填充卡片剩余空间 */
  min-height: 240px; /* 确保有最小高度 */
}

.error-placeholder {
  background: #fff5f5;
}

.error-icon {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #ff4d4f;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  font-weight: bold;
}

.status-text {
  font-size: 13px;
  color: var(--text-sub);
}

.retry-btn {
  margin-top: 8px;
  padding: 6px 16px;
  background: var(--primary);
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
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
  padding: 12px;
  border-top: 1px solid #f0f0f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.page-label {
  font-size: 12px;
  color: var(--text-sub);
}

.status-badge {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 4px;
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
  width: 24px;
  height: 24px;
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

.btn-danger {
  background: #ff4d4f;
  color: white;
  border: none;
}

.btn-danger:hover {
  background: #ff7875;
}

.btn-danger:disabled {
  background: #ffccc7;
  cursor: not-allowed;
}
</style>
