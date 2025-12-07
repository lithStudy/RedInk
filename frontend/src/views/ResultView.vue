<template>
  <div class="result-page">
    <div class="result-content">
      <div class="page-header-card">
        <div class="header-info">
          <h1 class="page-title">创作完成</h1>
          <p class="page-subtitle">恭喜！你的小红书图文已生成完毕，共 {{ images.length }} 张</p>
        </div>
        <div class="header-actions">
          <button class="btn btn-secondary btn-sm" @click="startOver">
            再来一篇
          </button>
          <button class="btn btn-primary btn-sm" @click="downloadAll">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
              <polyline points="7 10 12 15 17 10"></polyline>
              <line x1="12" y1="15" x2="12" y2="3"></line>
            </svg>
            一键下载
          </button>
        </div>
      </div>

      <div class="images-grid">
        <div v-for="image in images" :key="image.index" class="image-card group">
          <!-- Image Area -->
          <div 
            v-if="image.url" 
            style="position: relative; aspect-ratio: 3/4; overflow: hidden; cursor: pointer;" 
            @click="viewImage(image.url)"
          >
            <img
              :src="image.url"
              :alt="`第 ${image.index + 1} 页`"
              style="width: 100%; height: 100%; object-fit: cover; transition: transform 0.3s;"
            />
            <!-- Regenerating Overlay -->
            <div v-if="regeneratingIndex === image.index" style="position: absolute; inset: 0; background: rgba(255,255,255,0.8); display: flex; flex-direction: column; align-items: center; justify-content: center; z-index: 10;">
               <div class="spinner" style="width: 24px; height: 24px; border-width: 2px; border-color: var(--primary); border-top-color: transparent;"></div>
               <span style="font-size: 12px; color: var(--primary); margin-top: 8px; font-weight: 600;">重绘中...</span>
            </div>
            
            <!-- Hover Overlay -->
            <div v-else style="position: absolute; inset: 0; background: rgba(0,0,0,0.3); opacity: 0; transition: opacity 0.2s; display: flex; align-items: center; justify-content: center; color: white; font-weight: 600;" class="hover-overlay">
              预览大图
            </div>
          </div>
          
          <!-- Action Bar -->
          <div style="padding: 12px; border-top: 1px solid #f0f0f0; display: flex; justify-content: space-between; align-items: center;">
            <span style="font-size: 12px; color: var(--text-sub);">Page {{ image.index + 1 }}</span>
            <div style="display: flex; gap: 8px;">
              <button 
                style="border: none; background: none; color: var(--text-sub); cursor: pointer; display: flex; align-items: center;"
                title="重新生成此图"
                @click="handleRegenerate(image)"
                :disabled="regeneratingIndex === image.index"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M23 4v6h-6"></path><path d="M1 20v-6h6"></path><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path></svg>
              </button>
              <button 
                style="border: none; background: none; color: var(--primary); cursor: pointer; font-size: 12px;"
                @click="downloadOne(image)"
              >
                下载
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 主容器 - 使用flex布局 */
.result-page {
  width: 100%;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.result-content {
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
  flex-wrap: wrap;
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

/* 确保图片预览区域正确填充 */
.image-card > div:first-child {
  flex: 1;
  display: flex;
  flex-direction: column;
  position: relative;
  aspect-ratio: 3/4;
  overflow: hidden;
  cursor: pointer;
}

.image-card:hover .hover-overlay {
  opacity: 1;
}

.image-card:hover img {
  transform: scale(1.05);
}

.hover-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.3);
  opacity: 0;
  transition: opacity 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-weight: 600;
  font-size: 14px;
  z-index: 1;
}

.image-card img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.3s;
}

/* 响应式设计 */
@media (max-width: 1024px) {
  .image-card {
    flex: 0 0 calc(33.333% - 11px);
  }
}

@media (max-width: 768px) {
  .result-content {
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
    flex: 1;
    min-width: 0;
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
  .result-content {
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

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { regenerateImage, getHistory, type Page } from '../api'

const router = useRouter()
const route = useRoute()
const regeneratingIndex = ref<number | null>(null)

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

const viewImage = (url: string) => {
  const baseUrl = url.split('?')[0]
  window.open(baseUrl + '?thumbnail=false', '_blank')
}

const startOver = () => {
  router.push('/')
}

const downloadOne = (image: any) => {
  if (image.url) {
    const link = document.createElement('a')
    const baseUrl = image.url.split('?')[0]
    link.href = baseUrl + '?thumbnail=false'
    link.download = `rednote_page_${image.index + 1}.png`
    link.click()
  }
}

const downloadAll = () => {
  if (recordId.value) {
    const link = document.createElement('a')
    link.href = `/api/history/${recordId.value}/download`
    link.click()
  } else {
    images.value.forEach((image, index) => {
      if (image.url) {
        setTimeout(() => {
          const link = document.createElement('a')
          const baseUrl = image.url.split('?')[0]
          link.href = baseUrl + '?thumbnail=false'
          link.download = `rednote_page_${image.index + 1}.png`
          link.click()
        }, index * 300)
      }
    })
  }
}

const handleRegenerate = async (image: any) => {
  if (!recordId.value || regeneratingIndex.value !== null) return

  regeneratingIndex.value = image.index
  try {
    // Find the page content from outline
    const pageContent = outline.value.pages.find(p => p.index === image.index)
    if (!pageContent) {
       alert('无法找到对应页面的内容')
       return
    }

    // 构建上下文信息
    const context = {
      fullOutline: outline.value.raw || '',
      userTopic: topic.value || ''
    }

    const result = await regenerateImage(recordId.value, pageContent, true, context)
    if (result.success && result.image_url) {
       const newUrl = result.image_url
       const img = images.value.find(img => img.index === image.index)
       if (img) {
         img.url = `${newUrl}?t=${Date.now()}`
         img.status = 'done'
       }
       // 重新加载数据以确保同步
       if (recordId.value) {
         await loadData(recordId.value)
       }
    } else {
       alert('重绘失败: ' + (result.error || '未知错误'))
    }
  } catch (e: any) {
    alert('重绘失败: ' + e.message)
  } finally {
    regeneratingIndex.value = null
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
    await loadData(recordIdParam)
  } else {
    router.push('/')
  }
})
</script>
