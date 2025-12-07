<template>
  <div class="home-page">
    <!-- 图片网格轮播背景 -->
    <ShowcaseBackground />

    <!-- 主内容区域 -->
    <div class="home-content">
      <!-- Hero Area -->
      <div class="hero-section">
        <div class="hero-content">
          <div class="brand-pill">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/>
            </svg>
            AI 驱动的红墨创作助手
          </div>
          <div class="platform-slogan">
            让传播不再需要门槛，让创作从未如此简单
          </div>
          <h1 class="page-title">灵感一触即发</h1>
          <p class="page-subtitle">输入你的创意主题，让 AI 帮你生成爆款标题、正文和封面图</p>
        </div>

        <!-- 主题输入组合框 -->
        <ComposerInput
          ref="composerRef"
          v-model="topic"
          :loading="generatingTone"
          @generate="handleGenerate"
          @imagesChange="handleImagesChange"
        />
      </div>

      <!-- 基调展示区域 -->
      <div v-if="tone" class="tone-section">
        <div class="section-card tone-card">
          <div class="card-header">
            <h3 class="card-title">内容基调</h3>
            <button 
              class="btn btn-primary btn-sm" 
              @click="handleGenerateOutline"
              :disabled="loading || !tone.trim()"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M20.24 12.24a6 6 0 0 0-8.49-8.49L5 10.5V19h8.5z"></path>
                <line x1="16" y1="8" x2="2" y2="22"></line>
                <line x1="17.5" y1="15" x2="9" y2="15"></line>
              </svg>
              {{ loading ? '生成中...' : '生成大纲' }}
            </button>
          </div>
          <div class="card-body">
            <textarea
              v-model="tone"
              class="tone-textarea"
              placeholder="编辑内容基调..."
              rows="12"
            ></textarea>
          </div>
        </div>
      </div>

      <!-- 版权信息 -->
      <div class="page-footer">
        <div class="footer-copyright">
          © 2025 <a href="https://github.com/HisMax/RedInk" target="_blank" rel="noopener noreferrer">RedInk</a> by 默子 (Histone)
        </div>
        <div class="footer-license">
          Licensed under <a href="https://creativecommons.org/licenses/by-nc-sa/4.0/" target="_blank" rel="noopener noreferrer">CC BY-NC-SA 4.0</a>
        </div>
      </div>
    </div>

    <!-- 错误提示 -->
    <div v-if="error" class="error-toast">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10"></circle>
        <line x1="12" y1="8" x2="12" y2="12"></line>
        <line x1="12" y1="16" x2="12.01" y2="16"></line>
      </svg>
      {{ error }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { generateOutline, generateTone, createHistory, type Page, type OutlineMetadata } from '../api'

// 引入组件
import ShowcaseBackground from '../components/home/ShowcaseBackground.vue'
import ComposerInput from '../components/home/ComposerInput.vue'

const router = useRouter()

// 状态
const topic = ref('')
const loading = ref(false)
const error = ref('')
const composerRef = ref<InstanceType<typeof ComposerInput> | null>(null)

// 上传的图片文件
const uploadedImageFiles = ref<File[]>([])

// 基调相关状态
const generatingTone = ref(false)
const tone = ref<string>('')
const toneRecordId = ref<string | null>(null)  // 保存基调生成时的 record_id

/**
 * 处理图片变化
 */
function handleImagesChange(images: File[]) {
  uploadedImageFiles.value = images
}

/**
 * 生成基调
 */
async function handleGenerate() {
  if (!topic.value.trim()) return

  generatingTone.value = true
  error.value = ''

  try {
    // 生成基调
    const toneResult = await generateTone(topic.value.trim())

    if (!toneResult.success || !toneResult.tone) {
      error.value = toneResult.error || '生成基调失败'
      return
    }

    // 保存基调内容和 record_id
    tone.value = toneResult.tone
    toneRecordId.value = toneResult.record_id || null
    console.log('✅ 基调生成成功，record_id:', toneRecordId.value)
  } catch (err: any) {
    error.value = err.message || '网络错误，请重试'
  } finally {
    generatingTone.value = false
  }
}

/**
 * 根据基调生成大纲
 */
async function handleGenerateOutline() {
  if (!tone.value.trim()) {
    error.value = '基调内容不能为空'
    return
  }

  if (!toneRecordId.value) {
    error.value = '记录ID不存在，无法生成大纲'
    return
  }

  loading.value = true
  error.value = ''

  try {
    const imageFiles = uploadedImageFiles.value
    const outlineResult = await generateOutline(
      topic.value.trim(),
      imageFiles.length > 0 ? imageFiles : undefined,
      tone.value,
      toneRecordId.value  // 使用基调生成时的 record_id
    )

    if (outlineResult.success && outlineResult.pages) {
      console.log('✅ 大纲生成成功，结果:', outlineResult)
      console.log('📱 元数据:', outlineResult.metadata)

      // 获取 record_id（从大纲生成结果或基调生成结果中获取）
      const recordId = outlineResult.record_id || toneRecordId.value
      
      if (!recordId) {
        error.value = '生成失败：未获取到记录ID'
        return
      }

      // 创建或更新历史记录
      try {
        await createHistory(topic.value.trim(), {
          raw: outlineResult.outline || '',
          pages: outlineResult.pages,
          metadata: outlineResult.metadata
        }, recordId)
        console.log('✅ 历史记录已保存')
      } catch (e) {
        console.error('保存历史记录失败:', e)
      }

      // 清理 ComposerInput 的预览
      composerRef.value?.clearPreviews()
      uploadedImageFiles.value = []
      tone.value = ''
      toneRecordId.value = null

      // 跳转时携带 recordId 参数
      router.push(`/outline?recordId=${recordId}`)
    } else {
      error.value = outlineResult.error || '生成大纲失败'
    }
  } catch (err: any) {
    error.value = err.message || '网络错误，请重试'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
/* 主容器 - 使用flex布局 */
.home-page {
  width: 100%;
  min-height: 100vh;
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
}

.home-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
  max-width: 1100px;
  margin: 0 auto;
  width: 100%;
  padding: 16px;
}

/* Hero Section */
.hero-section {
  text-align: center;
  padding: 32px 24px;
  animation: fadeIn 0.6s ease-out;
  background: rgba(255, 255, 255, 0.95);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  backdrop-filter: blur(10px);
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.hero-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.brand-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 6px 16px;
  background: rgba(255, 36, 66, 0.08);
  color: var(--primary);
  border-radius: 100px;
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.5px;
  align-self: center;
}

.platform-slogan {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-main);
  line-height: 1.6;
  letter-spacing: 0.5px;
}

.page-title {
  font-size: 32px;
  font-weight: 800;
  color: var(--text-main);
  margin: 0;
  letter-spacing: -1px;
}

.page-subtitle {
  font-size: 15px;
  color: var(--text-sub);
  margin: 0;
  line-height: 1.6;
}

/* 通用卡片样式 */
.section-card {
  background: white;
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
  transition: box-shadow 0.2s;
}

.section-card:hover {
  box-shadow: var(--shadow-md);
}

.card-header {
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-color);
  background: linear-gradient(135deg, rgba(255, 36, 66, 0.03) 0%, rgba(255, 36, 66, 0.01) 100%);
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.card-title {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: var(--text-main);
  flex: 1;
}

.card-body {
  padding: 16px;
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

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

/* 基调展示区域 */
.tone-section {
  animation: fadeIn 0.6s ease-out;
}

.tone-textarea {
  width: 100%;
  min-height: 200px;
  padding: 12px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  font-size: 13px;
  font-family: inherit;
  line-height: 1.7;
  resize: vertical;
  color: var(--text-main);
  background: var(--bg-body);
}

.tone-textarea:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 0 3px rgba(255, 36, 66, 0.1);
}

/* Page Footer */
.page-footer {
  text-align: center;
  padding: 20px 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.footer-copyright {
  font-size: 14px;
  color: #333;
  font-weight: 500;
}

.footer-copyright a {
  color: var(--primary);
  text-decoration: none;
  font-weight: 600;
}

.footer-copyright a:hover {
  text-decoration: underline;
}

.footer-license {
  font-size: 12px;
  color: #999;
}

.footer-license a {
  color: #666;
  text-decoration: none;
}

.footer-license a:hover {
  color: var(--primary);
}

/* Error Toast */
.error-toast {
  position: fixed;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  background: #FF4D4F;
  color: white;
  padding: 12px 20px;
  border-radius: 50px;
  box-shadow: 0 8px 24px rgba(255, 77, 79, 0.3);
  display: flex;
  align-items: center;
  gap: 8px;
  z-index: 1000;
  animation: slideUp 0.3s ease-out;
  max-width: 90%;
}

/* Animations */
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes slideUp {
  from { opacity: 0; transform: translate(-50%, 20px); }
  to { opacity: 1; transform: translate(-50%, 0); }
}

/* 响应式设计 */
@media (max-width: 768px) {
  .home-content {
    padding: 12px;
    gap: 16px;
  }

  .hero-section {
    padding: 24px 16px;
    gap: 20px;
  }

  .platform-slogan {
    font-size: 16px;
  }

  .page-title {
    font-size: 24px;
  }

  .page-subtitle {
    font-size: 14px;
  }

  .card-header {
    padding: 10px 12px;
    flex-wrap: wrap;
  }

  .card-body {
    padding: 12px;
  }

  .tone-textarea {
    min-height: 150px;
    font-size: 12px;
  }

  .error-toast {
    bottom: 16px;
    padding: 10px 16px;
    font-size: 13px;
  }
}

@media (max-width: 480px) {
  .home-content {
    padding: 8px;
    gap: 12px;
  }

  .hero-section {
    padding: 20px 12px;
    gap: 16px;
  }

  .page-title {
    font-size: 20px;
  }

  .brand-pill {
    font-size: 12px;
    padding: 5px 12px;
  }
}
</style>
