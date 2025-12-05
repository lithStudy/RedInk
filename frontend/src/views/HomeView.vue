<template>
  <div class="container home-container">
    <!-- 图片网格轮播背景 -->
    <ShowcaseBackground />

    <!-- Hero Area -->
    <div class="hero-section">
      <div class="hero-content">
        <div class="brand-pill">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 6px;"><path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/></svg>
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
    <div v-if="tone" class="tone-section" style="max-width: 1100px; margin: 0 auto 40px auto;">
      <div class="card tone-card">
        <div class="tone-header">
          <h3 class="tone-title">内容基调</h3>
          <button 
            class="btn btn-primary btn-generate" 
            @click="handleGenerateOutline"
            :disabled="loading || !tone.trim()"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 6px;">
              <path d="M20.24 12.24a6 6 0 0 0-8.49-8.49L5 10.5V19h8.5z"></path>
              <line x1="16" y1="8" x2="2" y2="22"></line>
              <line x1="17.5" y1="15" x2="9" y2="15"></line>
            </svg>
            {{ loading ? '生成中...' : '生成大纲' }}
          </button>
        </div>
        <div class="tone-content">
          <textarea
            v-model="tone"
            class="tone-textarea"
            placeholder="编辑内容基调..."
            rows="15"
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

    <!-- 错误提示 -->
    <div v-if="error" class="error-toast">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
      {{ error }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useGeneratorStore } from '../stores/generator'
import { generateOutline, generateTone, createHistory } from '../api'

// 引入组件
import ShowcaseBackground from '../components/home/ShowcaseBackground.vue'
import ComposerInput from '../components/home/ComposerInput.vue'

const router = useRouter()
const store = useGeneratorStore()

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
      store.setTopic(topic.value.trim())
      store.setOutline(outlineResult.outline || '', outlineResult.pages, outlineResult.metadata)

      // 保存 recordId
      if (toneRecordId.value) {
        store.recordId = toneRecordId.value
        console.log('已保存 recordId:', toneRecordId.value)
      }
      
      // 初始化图片状态（为新大纲创建空的图片槽位）
      store.images = outlineResult.pages.map((page) => ({
        index: page.index,
        url: '',
        status: 'error' as const,
        retryable: true
      }))

      // 重置进度状态
      store.progress = {
        current: 0,
        total: outlineResult.pages.length,
        status: 'idle'
      }

      // 保存用户上传的图片到 store
      if (imageFiles.length > 0) {
        store.userImages = imageFiles
      } else {
        store.userImages = []
      }

      // 保存 record_id（从大纲生成结果或基调生成结果中获取）
      if (outlineResult.record_id) {
        store.recordId = outlineResult.record_id
        console.log('已保存 recordId:', store.recordId)
      } else if (toneRecordId.value) {
        store.recordId = toneRecordId.value
        console.log('已保存 recordId (from tone):', store.recordId)
      }

      // 清理 ComposerInput 的预览
      composerRef.value?.clearPreviews()
      uploadedImageFiles.value = []
      tone.value = ''
      toneRecordId.value = null

      // 跳转时携带 recordId 参数
      if (store.recordId) {
        router.push(`/outline?recordId=${store.recordId}`)
      } else {
        // 没有 recordId，使用 draft 模式（OutlineView 会创建）
        router.push('/outline')
      }
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
.home-container {
  max-width: 1100px;
  padding-top: 10px;
  position: relative;
  z-index: 1;
}

/* Hero Section */
.hero-section {
  text-align: center;
  margin-bottom: 40px;
  padding: 50px 60px;
  animation: fadeIn 0.6s ease-out;
  background: rgba(255, 255, 255, 0.95);
  border-radius: 24px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.06);
  backdrop-filter: blur(10px);
}

.hero-content {
  margin-bottom: 36px;
}

.brand-pill {
  display: inline-block;
  padding: 6px 16px;
  background: rgba(255, 36, 66, 0.08);
  color: var(--primary);
  border-radius: 100px;
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 20px;
  letter-spacing: 0.5px;
}

.platform-slogan {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-main);
  margin-bottom: 24px;
  line-height: 1.6;
  letter-spacing: 0.5px;
}

.page-subtitle {
  font-size: 16px;
  color: var(--text-sub);
  margin-top: 12px;
}

/* Page Footer */
.page-footer {
  text-align: center;
  padding: 24px 0 16px;
  margin-top: 20px;
}

.footer-copyright {
  font-size: 15px;
  color: #333;
  font-weight: 500;
  margin-bottom: 6px;
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
  font-size: 13px;
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
  bottom: 32px;
  left: 50%;
  transform: translateX(-50%);
  background: #FF4D4F;
  color: white;
  padding: 12px 24px;
  border-radius: 50px;
  box-shadow: 0 8px 24px rgba(255, 77, 79, 0.3);
  display: flex;
  align-items: center;
  gap: 8px;
  z-index: 1000;
  animation: slideUp 0.3s ease-out;
}

/* Animations */
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes slideUp {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

/* 基调展示区域 */
.tone-section {
  animation: fadeIn 0.6s ease-out;
}

.tone-card {
  background: white;
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.06);
  overflow: hidden;
}

.tone-header {
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: linear-gradient(135deg, rgba(255, 36, 66, 0.05) 0%, rgba(255, 36, 66, 0.02) 100%);
}

.tone-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: var(--text-main);
}

.tone-content {
  padding: 24px;
}

.tone-textarea {
  width: 100%;
  min-height: 300px;
  padding: 16px;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  font-size: 13px;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue', sans-serif;
  line-height: 1.8;
  resize: vertical;
  color: var(--text-main);
  background: var(--bg-secondary);
}

.tone-textarea:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 0 3px rgba(255, 36, 66, 0.1);
}

.btn-generate {
  padding: 10px 20px;
  font-size: 14px;
  display: flex;
  align-items: center;
  border-radius: 8px;
  border: none;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary {
  background: var(--primary);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #e62e3d;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(255, 36, 66, 0.3);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}
</style>
