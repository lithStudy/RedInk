<template>
  <div class="container" style="max-width: 100%;">
    <!-- 浮动错误提示 -->
    <div v-if="error" class="generation-toolbar">
      <div class="toolbar-error">
        {{ error }}
      </div>
    </div>

    <!-- 基调展示区域 -->
    <div v-if="tone" class="tone-section" style="max-width: 1200px; margin: 0 auto 30px auto;">
      <div class="card tone-card">
        <div class="tone-header">
          <h3 class="tone-title">内容基调</h3>
          <button 
            class="btn btn-primary btn-generate" 
            @click="regenerateOutline"
            :disabled="isRegeneratingOutline || !toneHasChanged"
            :title="!toneHasChanged ? '请先修改基调内容' : ''"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 6px;">
              <path d="M20.24 12.24a6 6 0 0 0-8.49-8.49L5 10.5V19h8.5z"></path>
              <line x1="16" y1="8" x2="2" y2="22"></line>
              <line x1="17.5" y1="15" x2="9" y2="15"></line>
            </svg>
            {{ isRegeneratingOutline ? '生成中...' : '生成大纲' }}
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

    <!-- 确认对话框 -->
    <div v-if="showConfirmDialog" class="confirm-dialog-overlay" @click.self="showConfirmDialog = false">
      <div class="confirm-dialog">
        <div class="confirm-dialog-header">
          <h3>确认重新生成大纲</h3>
        </div>
        <div class="confirm-dialog-content">
          <p>检测到您已经生成过图片，重新生成大纲将会：</p>
          <ul>
            <li>清空所有已生成的图片</li>
            <li>根据新的基调重新生成大纲</li>
            <li>需要重新生成所有图片</li>
          </ul>
          <p style="margin-top: 16px; color: #ff4d4f; font-weight: 500;">确定要继续吗？</p>
        </div>
        <div class="confirm-dialog-footer">
          <button class="btn btn-secondary" @click="showConfirmDialog = false">
            取消
          </button>
          <button class="btn btn-primary" @click="doRegenerateOutline">
            确定生成
          </button>
        </div>
      </div>
    </div>

    <!-- 小红书内容编辑区域 -->
    <div v-if="store.outline.metadata || localMetadata" 
         class="metadata-section" 
         style="max-width: 1200px; margin: 0 auto 30px auto;">
      <div class="card metadata-card">
        <div class="metadata-header">
          <h3 class="metadata-title">📱 小红书内容</h3>
          <button 
            class="btn-collapse" 
            @click="metadataCollapsed = !metadataCollapsed"
            :title="metadataCollapsed ? '展开' : '收起'"
          >
            <svg v-if="metadataCollapsed" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="6 9 12 15 18 9"></polyline>
            </svg>
            <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="18 15 12 9 6 15"></polyline>
            </svg>
          </button>
        </div>
        <div v-if="!metadataCollapsed" class="metadata-content">
          <!-- 标题 -->
          <div class="metadata-item">
            <label class="metadata-label">
              标题
              <span class="char-count" :class="{ 'over-limit': titleCharCount > 20 }">
                {{ titleCharCount }}/20
              </span>
            </label>
            <input 
              v-model="localMetadata.title"
              class="metadata-input title-input"
              placeholder="输入小红书标题（20字以内）..."
              maxlength="30"
              @input="onMetadataChange"
            />
          </div>
          
          <!-- 正文 -->
          <div class="metadata-item">
            <label class="metadata-label">
              正文
              <span class="char-count" :class="{ 'under-limit': contentCharCount < 100, 'over-limit': contentCharCount > 300 }">
                {{ contentCharCount }}/100-300
              </span>
            </label>
            <textarea
              v-model="localMetadata.content"
              class="metadata-textarea content-textarea"
              placeholder="输入小红书正文内容（100-300字）..."
              rows="8"
              @input="onMetadataChange"
            ></textarea>
          </div>
          
          <!-- 标签 -->
          <div class="metadata-item">
            <label class="metadata-label">
              标签
              <span class="char-count">{{ tagCount }}个</span>
            </label>
            <textarea
              v-model="localMetadata.tags"
              class="metadata-textarea tags-textarea"
              placeholder="输入标签，用空格分隔（例如：#手冲咖啡 #咖啡教程 #居家咖啡）..."
              rows="3"
              @input="onMetadataChange"
            ></textarea>
            <div v-if="localMetadata.tags" class="tags-preview">
              <span v-for="(tag, idx) in localMetadata.tags.split(/\s+/).filter(t => t)" 
                    :key="idx" 
                    class="tag-item">{{ tag }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="page-header" style="max-width: 1200px; margin: 0 auto 30px auto;">
      <div>
        <h1 class="page-title">编辑大纲</h1>
        <p class="page-subtitle">
          调整页面顺序，修改文案，打造完美内容
          <span v-if="saveStatus === 'saving'" class="save-status saving">保存中...</span>
          <span v-else-if="saveStatus === 'saved'" class="save-status saved">已保存</span>
        </p>
        <!-- 参考图模式选择 -->
        <div class="reference-mode-selector">
          <label class="reference-mode-label">参考图模式：</label>
          <div class="reference-mode-options">
            <label class="reference-mode-option">
              <input 
                type="radio" 
                v-model="referenceMode" 
                value="custom"
                :disabled="store.userImages.length === 0"
              />
              <span>使用自定义参考图</span>
              <span v-if="store.userImages.length === 0" class="option-hint">（需上传参考图）</span>
            </label>
            <label class="reference-mode-option">
              <input 
                type="radio" 
                v-model="referenceMode" 
                value="cover"
              />
              <span>使用封面参考</span>
            </label>
            <label class="reference-mode-option">
              <input 
                type="radio" 
                v-model="referenceMode" 
                value="previous"
              />
              <span>使用上一张参考</span>
            </label>
          </div>
        </div>
      </div>
      <div style="display: flex; gap: 12px;">
        <button class="btn btn-secondary" @click="goBack" style="background: white; border: 1px solid var(--border-color);">
          上一步
        </button>
        <!-- 生成中显示停止按钮 -->
        <button
          v-if="isGenerating"
          class="btn btn-danger"
          @click="stopGeneration"
          :disabled="isStopping"
        >
          {{ isStopping ? '停止中...' : '停止生成' }}
        </button>
        <!-- 暂停时显示继续按钮 -->
        <button
          v-if="isPaused"
          class="btn btn-primary"
          @click="continueGeneration"
          :disabled="isContinuing"
        >
          {{ isContinuing ? '继续中...' : '继续生成' }}
        </button>
        <!-- 失败时显示补全按钮 -->
        <button
          v-if="hasFailedImages && !isGenerating && !isPaused"
          class="btn btn-primary"
          @click="retryAllFailed"
          :disabled="isRetrying"
        >
          {{ isRetrying ? '补全中...' : '一键补全失败图片' }}
        </button>
        <!-- 一键下载按钮（有已生成的图片时显示） -->
        <button
          v-if="hasGeneratedImages && !isGenerating"
          class="btn btn-secondary"
          @click="downloadAll"
          style="background: white; border: 1px solid var(--border-color);"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 6px;">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
            <polyline points="7 10 12 15 17 10"></polyline>
            <line x1="12" y1="15" x2="12" y2="3"></line>
          </svg>
          一键下载
        </button>
        <!-- 默认显示开始生成按钮 -->
        <button 
          v-if="!isGenerating && !isPaused && !hasFailedImages" 
          class="btn btn-primary" 
          @click="startGeneration"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 6px;"><path d="M20.24 12.24a6 6 0 0 0-8.49-8.49L5 10.5V19h8.5z"></path><line x1="16" y1="8" x2="2" y2="22"></line><line x1="17.5" y1="15" x2="9" y2="15"></line></svg>
          {{ hasGeneratedImages ? '查看生成结果' : '开始生成图片' }}
        </button>
      </div>
    </div>

    <!-- 生成进度（标题下方，卡片上方） -->
    <div v-if="store.progress.total > 0" class="progress-section" style="max-width: 1200px; margin: 0 auto 30px auto;">
      <div class="card progress-card">
        <div class="progress-info">
          <span class="progress-label">生成进度</span>
          <span class="progress-percent">{{ Math.round(progressPercent) }}%</span>
        </div>
        <div class="progress-container">
          <div class="progress-bar" :style="{ width: progressPercent + '%' }" />
        </div>
        <div class="progress-status">
          <span v-if="isGenerating">正在生成第 {{ store.progress.current + 1 }} / {{ store.progress.total }} 页</span>
          <span v-else-if="isPaused">已暂停，{{ store.getPendingPages().length }} 张图片待生成</span>
          <span v-else-if="hasFailedImages">{{ failedCount }} 张图片生成失败</span>
          <span v-else>全部 {{ store.progress.total }} 张图片生成完成</span>
        </div>
      </div>
    </div>

    <div class="outline-grid">
      <div 
        v-for="(page, idx) in store.outline.pages" 
        :key="page.index"
        class="flip-card-wrapper"
        :draggable="true"
        @dragstart="onDragStart($event, idx)"
        @dragover.prevent="onDragOver($event, idx)"
        @drop="onDrop($event, idx)"
        :class="{ 'dragging-over': dragOverIndex === idx }"
      >
        <div 
          class="flip-card"
          :class="{ 'flipped': flippedCards.has(page.index) }"
        >
          <!-- 文字面 -->
          <div class="flip-card-face flip-card-front">
            <div class="card outline-card">
              <!-- 拖拽手柄 (改为右上角或更加隐蔽) -->
              <div class="card-top-bar">
                <div class="page-info">
                   <span class="page-number">P{{ idx + 1 }}</span>
                   <span class="page-type" :class="page.type">{{ getPageTypeName(page.type) }}</span>
                </div>
                
                <div class="card-controls">
                  <div class="drag-handle" title="拖拽排序">
                     <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#999" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="9" cy="12" r="1"></circle><circle cx="9" cy="5" r="1"></circle><circle cx="9" cy="19" r="1"></circle><circle cx="15" cy="12" r="1"></circle><circle cx="15" cy="5" r="1"></circle><circle cx="15" cy="19" r="1"></circle></svg>
                  </div>
                  <button class="icon-btn" @click.stop="deletePage(idx)" title="删除此页">
                     <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                  </button>
                </div>
              </div>

              <textarea
                v-model="page.content"
                class="textarea-paper"
                placeholder="在此输入文案..."
                @input="store.updatePage(page.index, page.content)"
              />
              
              <div class="word-count">{{ page.content.length }} 字</div>
            </div>
          </div>

          <!-- 图片面 -->
          <div class="flip-card-face flip-card-back">
            <div class="card outline-card image-card">
              <!-- 顶部栏 -->
              <div class="card-top-bar">
                <div class="page-info">
                   <span class="page-number">P{{ idx + 1 }}</span>
                   <span class="page-type" :class="page.type">{{ getPageTypeName(page.type) }}</span>
                </div>
                
                <div class="card-controls">
                  <div class="drag-handle" title="拖拽排序">
                     <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#999" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="9" cy="12" r="1"></circle><circle cx="9" cy="5" r="1"></circle><circle cx="9" cy="19" r="1"></circle><circle cx="15" cy="12" r="1"></circle><circle cx="15" cy="5" r="1"></circle><circle cx="15" cy="19" r="1"></circle></svg>
                  </div>
                  <button class="icon-btn" @click.stop="deletePage(idx)" title="删除此页">
                     <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                  </button>
                </div>
              </div>

              <!-- 图片内容 -->
              <div class="page-image-container-full">
                <!-- 已生成的图片 -->
                <div v-if="getImageForPage(page.index)?.status === 'done' && getImageForPage(page.index)?.url" class="page-image-preview-full">
                  <img :src="getImageForPage(page.index)?.url" :alt="`第 ${page.index + 1} 页`" />
                  <!-- 重新生成按钮（悬浮显示） -->
                  <div class="image-regenerate-overlay">
                    <div class="overlay-buttons">
                      <button
                        class="overlay-action-btn"
                        @click.stop="viewLargeImage(page.index)"
                        title="查看大图"
                      >
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                          <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                          <circle cx="12" cy="12" r="3"></circle>
                        </svg>
                        <span>查看大图</span>
                      </button>
                      <button
                        class="overlay-action-btn"
                        @click.stop="downloadOne(page.index, idx + 1)"
                        title="下载此图"
                      >
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                          <polyline points="7 10 12 15 17 10"></polyline>
                          <line x1="12" y1="15" x2="12" y2="3"></line>
                        </svg>
                        <span>下载</span>
                      </button>
                      <button
                        class="overlay-action-btn"
                        @click.stop="regeneratePageImage(page.index)"
                        :disabled="regeneratingImages.has(page.index)"
                        title="重新生成图片"
                      >
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                          <path d="M23 4v6h-6"></path>
                          <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
                        </svg>
                        <span>{{ regeneratingImages.has(page.index) ? '生成中...' : '重新生成' }}</span>
                      </button>
                    </div>
                  </div>
                </div>
                <!-- 生成中/重试中状态 -->
                <div v-else-if="getImageForPage(page.index)?.status === 'generating' || getImageForPage(page.index)?.status === 'retrying'" class="page-image-placeholder-full">
                  <div class="spinner-small"></div>
                  <div class="status-text-small">
                    {{ getImageForPage(page.index)?.status === 'retrying' ? '重试中...' : '生成中...' }}
                  </div>
                </div>
                <!-- 生成失败状态（有错误信息） -->
                <div v-else-if="getImageForPage(page.index)?.status === 'error' && getImageForPage(page.index)?.error" class="page-image-placeholder-full error-placeholder-small">
                  <div class="error-icon-small">!</div>
                  <div class="status-text-small">生成失败</div>
                  <button
                    class="generate-image-btn"
                    @click.stop="generatePageImage(page.index)"
                    :disabled="generatingImages.has(page.index)"
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <path d="M23 4v6h-6"></path>
                      <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
                    </svg>
                    <span>{{ generatingImages.has(page.index) ? '生成中...' : '重新生成' }}</span>
                  </button>
                </div>
                <!-- 还没有生成图片（没有图片数据） -->
                <div v-else class="page-image-placeholder-full">
                  <div class="generate-image-prompt">
                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="opacity: 0.3;">
                      <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                      <circle cx="8.5" cy="8.5" r="1.5"></circle>
                      <path d="M21 15l-5-5L5 21"></path>
                    </svg>
                    <div class="status-text-small" style="margin: 12px 0;">还未生成图片</div>
                    <button
                      class="generate-image-btn"
                      @click.stop="generatePageImage(page.index)"
                      :disabled="generatingImages.has(page.index) || !store.taskId"
                    >
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M23 4v6h-6"></path>
                        <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
                      </svg>
                      <span>{{ generatingImages.has(page.index) ? '生成中...' : '生成图片' }}</span>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 切换按钮 -->
        <button 
          class="flip-toggle-btn"
          @click.stop="toggleFlip(page.index)"
          :title="flippedCards.has(page.index) ? '查看文字' : '查看图片'"
        >
          <svg v-if="flippedCards.has(page.index)" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
            <path d="M14 2v6h6"></path>
            <path d="M16 13H8"></path>
            <path d="M16 17H8"></path>
            <path d="M10 9H8"></path>
          </svg>
          <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
            <circle cx="8.5" cy="8.5" r="1.5"></circle>
            <path d="M21 15l-5-5L5 21"></path>
          </svg>
        </button>
      </div>

      <!-- 添加按钮卡片 -->
      <div class="card add-card-dashed" @click="addPage('content')">
        <div class="add-content">
          <div class="add-icon">+</div>
          <span>添加页面</span>
        </div>
      </div>
    </div>
    
    <div style="height: 100px;"></div>

    <!-- 大图查看模态框 -->
    <div v-if="viewingLargeImage" class="large-image-modal" @click="closeLargeImage">
      <div class="large-image-container" @click.stop>
        <button class="close-large-image-btn" @click="closeLargeImage" title="关闭 (ESC)">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
        
        <!-- 左箭头 -->
        <button 
          v-if="hasPreviousImage" 
          class="nav-arrow-btn nav-arrow-left" 
          @click.stop="previousImage"
          title="上一张 (←)"
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="15 18 9 12 15 6"></polyline>
          </svg>
        </button>
        
        <!-- 右箭头 -->
        <button 
          v-if="hasNextImage" 
          class="nav-arrow-btn nav-arrow-right" 
          @click.stop="nextImage"
          title="下一张 (→)"
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="9 18 15 12 9 6"></polyline>
          </svg>
        </button>
        
        <!-- 图片信息 -->
        <div class="image-info">
          <span>{{ currentImageIndex + 1 }} / {{ totalImages }}</span>
        </div>
        
        <img v-if="largeImageUrl" :src="largeImageUrl" alt="大图预览" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, watch, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useGeneratorStore } from '../stores/generator'
import { updateHistory, regenerateImage as apiRegenerateImage, generateImagesPost, retryFailedImages as apiRetryFailed, createHistory, getTaskImages, stopGeneration as apiStopGeneration, continueGeneration as apiContinueGeneration, getTone, generateOutline, updateTone, getHistory, updateOutline } from '../api'

const router = useRouter()
const route = useRoute()
const store = useGeneratorStore()

const dragOverIndex = ref<number | null>(null)
const draggedIndex = ref<number | null>(null)
const saveStatus = ref<'saved' | 'saving' | 'idle'>('idle')

// 跟踪每个卡片的翻转状态
const flippedCards = ref<Set<number>>(new Set())

// 跟踪正在重新生成的图片
const regeneratingImages = ref<Set<number>>(new Set())

// 跟踪正在生成的图片（首次生成）
const generatingImages = ref<Set<number>>(new Set())

// 批量生成相关状态
const error = ref('')
const isRetrying = ref(false)
const isStopping = ref(false)
const isContinuing = ref(false)
const tone = ref<string>('')
const originalTone = ref<string>('')  // 保存原始基调，用于比较是否有修改
const isRegeneratingOutline = ref(false)
const showConfirmDialog = ref(false)  // 确认对话框
const metadataCollapsed = ref(false)  // 小红书元数据是否收起

// 本地编辑的元数据
const localMetadata = ref({
  title: '',
  content: '',
  tags: ''
})

// 字数统计
const titleCharCount = computed(() => localMetadata.value.title.length)
const contentCharCount = computed(() => localMetadata.value.content.length)
const tagCount = computed(() => localMetadata.value.tags.split(/\s+/).filter(t => t.trim()).length)

// 元数据变化时的处理
function onMetadataChange() {
  // 确保 metadata 对象存在
  if (!store.outline.metadata) {
    store.outline.metadata = {
      title: '',
      content: '',
      tags: ''
    }
  }
  // 更新到 store
  store.outline.metadata.title = localMetadata.value.title
  store.outline.metadata.content = localMetadata.value.content
  store.outline.metadata.tags = localMetadata.value.tags
  // 触发自动保存
  debouncedSave()
}

// 参考图模式：'custom' | 'cover' | 'previous'
const referenceMode = ref<'custom' | 'cover' | 'previous'>('cover')

// 计算属性
const isGenerating = computed(() => store.progress.status === 'generating')
const isPaused = computed(() => store.progress.status === 'paused')
const hasFailedImages = computed(() => store.images.some(img => img.status === 'error'))
const failedCount = computed(() => store.images.filter(img => img.status === 'error').length)

const progressPercent = computed(() => {
  if (store.progress.total === 0) return 0
  return (store.progress.current / store.progress.total) * 100
})

// 大图查看相关
const viewingLargeImage = ref(false)
const largeImageUrl = ref<string>('')
const currentImageIndex = ref<number>(0)

// 获取所有已生成图片的索引列表
const generatedImageIndices = computed(() => {
  return store.images
    .filter(img => img.status === 'done' && img.url)
    .map(img => img.index)
    .sort((a, b) => a - b)
})

// 总图片数
const totalImages = computed(() => generatedImageIndices.value.length)

// 是否有上一张
const hasPreviousImage = computed(() => {
  return currentImageIndex.value > 0
})

// 是否有下一张
const hasNextImage = computed(() => {
  return currentImageIndex.value < totalImages.value - 1
})

// 检查是否有已生成的图片
const hasGeneratedImages = computed(() => {
  return store.images.some(img => img.status === 'done' && img.url)
})

// 检查基调是否有修改
const toneHasChanged = computed(() => {
  return tone.value.trim() !== originalTone.value.trim()
})

// 获取对应页面的图片
function getImageForPage(pageIndex: number) {
  return store.images.find(img => img.index === pageIndex)
}

// 检查页面是否有已生成的图片
function hasImage(pageIndex: number): boolean {
  const image = getImageForPage(pageIndex)
  return image?.status === 'done' && !!image?.url
}

// 切换卡片翻转状态
function toggleFlip(pageIndex: number) {
  if (flippedCards.value.has(pageIndex)) {
    flippedCards.value.delete(pageIndex)
  } else {
    flippedCards.value.add(pageIndex)
  }
}

// 初始化翻转状态：有图片的默认显示图片面
function updateFlipStates() {
  store.outline.pages.forEach(page => {
    if (hasImage(page.index)) {
      flippedCards.value.add(page.index)
    } else if (!flippedCards.value.has(page.index)) {
      // 如果没有图片且用户没有手动翻转过，则显示文字面
      flippedCards.value.delete(page.index)
    }
    // 如果用户已经手动翻转过，保持当前状态
  })
}

// 监听图片变化，自动更新翻转状态（仅在图片状态变化时，不影响用户手动翻转）
watch(
  () => store.images.map(img => ({ index: img.index, status: img.status, url: img.url })),
  (newImages, oldImages) => {
    // 只在图片真正生成完成时才更新翻转状态
    if (oldImages) {
      newImages.forEach((newImg, idx) => {
        const oldImg = oldImages[idx]
        // 如果图片刚刚生成完成（从非 done 变为 done）
        if (oldImg && oldImg.status !== 'done' && newImg.status === 'done' && newImg.url) {
          flippedCards.value.add(newImg.index)
        }
      })
    }
  },
  { deep: true }
)

// 防抖保存函数
let saveTimer: ReturnType<typeof setTimeout> | null = null

async function saveToHistory() {
  if (!store.recordId) return
  
  saveStatus.value = 'saving'
  try {
    await updateHistory(store.recordId, {
      outline: {
        raw: store.outline.raw,
        pages: store.outline.pages,
        metadata: store.outline.metadata
      }
    })
    saveStatus.value = 'saved'
    // 2秒后恢复idle状态
    setTimeout(() => {
      if (saveStatus.value === 'saved') {
        saveStatus.value = 'idle'
      }
    }, 2000)
  } catch (e) {
    console.error('自动保存失败:', e)
    saveStatus.value = 'idle'
  }
}

function debouncedSave() {
  if (saveTimer) {
    clearTimeout(saveTimer)
  }
  saveTimer = setTimeout(() => {
    saveToHistory()
  }, 1000) // 1秒防抖
}

// 监听大纲变化，自动保存到后端和缓存
watch(
  () => store.outline,
  () => {
    debouncedSave()
    store.saveToStorage()  // 同时保存到缓存
  },
  { deep: true }
)

// 监听 store 中的 metadata 变化，同步到本地编辑
watch(
  () => store.outline.metadata,
  (newMetadata) => {
    console.log('📱 检测到 metadata 变化:', newMetadata)
    localMetadata.value = {
      title: newMetadata?.title || '',
      content: newMetadata?.content || '',
      tags: newMetadata?.tags || ''
    }
    console.log('✅ 已更新 localMetadata:', localMetadata.value)
  },
  { immediate: true, deep: true }
)

// 监听 recordId 变化，同步 URL
watch(
  () => store.recordId,
  (newRecordId) => {
    if (newRecordId) {
      syncURLParams()
    }
  }
)

/**
 * 从后端加载任务数据
 */
async function loadDataFromBackend(recordId: string) {
  console.log(`🔄 从后端加载任务数据: recordId=${recordId}`)
  
  try {
    const res = await getHistory(recordId)
    if (!res.success || !res.record) {
      console.error('❌ 加载历史记录失败')
      router.push('/')
      return
    }

    const record = res.record
    
    // 设置基本信息
    store.recordId = record.id
    store.taskId = record.images.task_id
    store.setTopic(record.title)

    // 如果有 task_id，优先从任务文件夹加载数据
    if (record.images.task_id) {
      try {
        const taskImagesRes = await getTaskImages(record.images.task_id)
        if (taskImagesRes.success) {
          // 优先使用任务文件夹中的大纲
          if (taskImagesRes.outline && taskImagesRes.outline.pages && taskImagesRes.outline.pages.length > 0) {
            const outline = taskImagesRes.outline
            console.log('📂 任务文件夹大纲数据:', outline)
            console.log('📱 元数据:', outline.metadata)
            store.setTopic(outline.topic || record.title)
            store.setOutline(
              outline.raw || record.outline.raw,
              outline.pages,
              outline.metadata
            )
            console.log('✅ 从任务文件夹加载大纲:', outline.pages.length, '页')
          } else {
            console.log('📋 历史记录大纲数据:', record.outline)
            console.log('📱 元数据:', record.outline.metadata)
            store.setOutline(record.outline.raw, record.outline.pages, record.outline.metadata)
            console.log('⚠️ 任务文件夹无大纲，从历史记录加载:', record.outline.pages.length, '页')
          }
          
          // 加载图片
          if (taskImagesRes.generated_indices) {
            const generatedSet = new Set(taskImagesRes.generated_indices)
            const pages = taskImagesRes.outline?.pages || record.outline.pages
            store.images = pages.map((page: any) => {
              const pageIndex = page.index
              if (generatedSet.has(pageIndex)) {
                const filename = `${pageIndex}.png`
                const timestamp = Date.now()
                const imageUrl = `/api/images/${record.images.task_id}/${filename}?t=${timestamp}`
                return {
                  index: pageIndex,
                  url: imageUrl,
                  status: 'done' as const,
                  retryable: true
                }
              } else {
                return {
                  index: pageIndex,
                  url: '',
                  status: 'error' as const,
                  retryable: true
                }
              }
            })
            console.log('✅ 从任务文件夹加载图片:', taskImagesRes.generated_indices.length, '张')
          }
        } else {
          // 扫描失败，使用历史记录中的数据
          store.setOutline(record.outline.raw, record.outline.pages, record.outline.metadata)
          store.images = record.outline.pages.map((page) => ({
            index: page.index,
            url: '',
            status: 'error' as const,
            retryable: true
          }))
          console.log('⚠️ 扫描失败，使用历史记录数据')
        }
      } catch (e) {
        console.error('❌ 加载任务数据失败:', e)
        store.setOutline(record.outline.raw, record.outline.pages, record.outline.metadata)
        store.images = record.outline.pages.map((page) => ({
          index: page.index,
          url: '',
          status: 'error' as const,
          retryable: true
        }))
      }
    } else {
      // 没有 task_id
      store.setOutline(record.outline.raw, record.outline.pages, record.outline.metadata)
      store.images = record.outline.pages.map((page) => ({
        index: page.index,
        url: '',
        status: 'error' as const,
        retryable: true
      }))
    }

    // 读取基调
    if (store.taskId) {
      try {
        const toneResult = await getTone(store.taskId)
        if (toneResult.success && toneResult.tone) {
          tone.value = toneResult.tone
          originalTone.value = toneResult.tone
          console.log('✅ 已加载基调')
        }
      } catch (e) {
        console.warn('⚠️ 读取基调失败:', e)
      }
    }

    // 设置进度状态
    const doneCount = store.images.filter(img => img.status === 'done').length
    const totalCount = store.images.length
    store.progress.current = doneCount
    store.progress.total = totalCount
    store.progress.status = doneCount === totalCount ? 'done' : 'paused'
    store.stage = 'generating'

    // 保存到缓存
    store.saveToStorage()
    
    console.log('✅ 数据加载完成')
  } catch (err) {
    console.error('❌ 加载数据失败:', err)
    router.push('/')
  }
}

/**
 * 同步 URL 参数
 */
function syncURLParams() {
  if (store.recordId && route.query.recordId !== store.recordId) {
    router.replace({ query: { recordId: store.recordId } })
    console.log('✅ 已同步 URL 参数:', store.recordId)
  }
}

// 组件挂载时初始化
onMounted(async () => {
  const recordId = route.query.recordId as string
  
  if (recordId) {
    // 从 URL 参数获取 recordId，加载数据
    console.log('📍 从 URL 加载任务:', recordId)
    
    // 先尝试从缓存快速恢复 UI
    const cached = store.loadFromCache(recordId)
    if (cached) {
      console.log('⚡ 从缓存快速恢复 UI')
      // 初始化翻转状态
      updateFlipStates()
    }
    
    // 从后端加载最新数据
    await loadDataFromBackend(recordId)
    
    // 更新翻转状态
    updateFlipStates()
  } else if (store.outline.pages.length > 0) {
    // 没有 URL 参数，但 store 中有数据（从首页生成）
    console.log('📝 使用 store 中的数据')
    
    // 如果没有 recordId，创建历史记录
    if (!store.recordId) {
      try {
        const result = await createHistory(store.topic, {
          raw: store.outline.raw,
          pages: store.outline.pages
        }, store.taskId || undefined)
        if (result.success && result.record_id) {
          store.recordId = result.record_id
          console.log('✅ 创建历史记录:', store.recordId)
          
          // 同步 URL
          syncURLParams()
          
          // 保存到缓存
          store.saveToStorage()
        }
      } catch (e) {
        console.error('❌ 创建历史记录失败:', e)
      }
    } else {
      // 已有 recordId，同步 URL
      syncURLParams()
    }
    
    // 读取基调
    if (store.taskId) {
      try {
        const toneResult = await getTone(store.taskId)
        if (toneResult.success && toneResult.tone) {
          tone.value = toneResult.tone
          originalTone.value = toneResult.tone
          console.log('✅ 已加载基调')
        }
      } catch (e) {
        console.warn('⚠️ 读取基调失败:', e)
      }
    }
    
    // 确保 images 数组完整
    if (store.images.length !== store.outline.pages.length) {
      const existingIndices = new Set(store.images.map(img => img.index))
      store.outline.pages.forEach((page) => {
        if (!existingIndices.has(page.index)) {
          store.images.push({
            index: page.index,
            url: '',
            status: 'error' as const,
            retryable: true
          })
        }
      })
      store.images.sort((a, b) => a.index - b.index)
    }
    
    // 设置进度状态
    const doneCount = store.images.filter(img => img.status === 'done').length
    const totalCount = store.outline.pages.length
    store.progress.current = doneCount
    store.progress.total = totalCount
    if (totalCount === 0) {
      store.progress.status = 'idle'
    } else if (doneCount === totalCount) {
      store.progress.status = 'done'
    } else {
      store.progress.status = 'paused'
    }
    if (totalCount > 0) {
      store.stage = 'generating'
    }
    
    // 初始化翻转状态
    updateFlipStates()
  } else {
    // 既没有 URL 参数，store 也没有数据，跳转到首页
    console.log('⚠️ 无数据，跳转到首页')
    router.push('/')
    return
  }
})

// 组件卸载时清理定时器和事件监听
onUnmounted(() => {
  if (saveTimer) {
    clearTimeout(saveTimer)
  }
  // 清理键盘事件监听
  document.removeEventListener('keydown', handleKeyDown)
})

const getPageTypeName = (type: string) => {
  const names = {
    cover: '封面',
    content: '内容',
    summary: '总结'
  }
  return names[type as keyof typeof names] || '内容'
}

// 拖拽逻辑
const onDragStart = (e: DragEvent, index: number) => {
  draggedIndex.value = index
  if (e.dataTransfer) {
    e.dataTransfer.effectAllowed = 'move'
    e.dataTransfer.dropEffect = 'move'
  }
}

const onDragOver = (e: DragEvent, index: number) => {
  if (draggedIndex.value === index) return
  dragOverIndex.value = index
}

const onDrop = async (e: DragEvent, index: number) => {
  dragOverIndex.value = null
  if (draggedIndex.value !== null && draggedIndex.value !== index) {
    const fromIndex = draggedIndex.value
    
    // 前端先移动
    store.movePage(fromIndex, index)
    
    // 如果有 taskId，调用后端 API 更新大纲和图片文件
    if (store.taskId) {
      try {
        const result = await updateOutline(store.taskId, store.outline.pages)
        if (!result.success) {
          console.error('更新大纲失败:', result.error)
          alert('移动失败：' + result.error)
        } else {
          console.log('大纲更新成功，图片文件已重命名')
          
          // 重新生成所有图片的 URL（因为后端文件已重命名）
          const timestamp = Date.now()
          store.images.forEach(img => {
            if (img.url && img.status === 'done') {
              // 更新 URL 为新的索引
              img.url = `/api/images/${store.taskId}/${img.index}.png?t=${timestamp}`
            }
          })
          console.log('图片 URL 已更新')
          
          // 如果有 recordId，也需要更新历史记录
          if (store.recordId) {
            try {
              const generatedImageIndices = store.images
                .filter(img => img.status === 'done' && img.url)
                .map(img => `${img.index}.png`)
              
              await updateHistory(store.recordId, {
                outline: store.outline,
                images: {
                  task_id: store.taskId,
                  generated: generatedImageIndices
                }
              })
              console.log('历史记录已同步')
            } catch (e) {
              console.error('更新历史记录失败:', e)
            }
          }
        }
      } catch (error) {
        console.error('调用 API 失败:', error)
        alert('移动失败，请稍后重试')
      }
    }
  }
  draggedIndex.value = null
}

const deletePage = async (index: number) => {
  if (confirm('确定要删除这一页吗？')) {
    // 先在前端删除
    store.deletePage(index)
    
    // 如果有 taskId，调用后端 API 更新大纲和图片文件
    if (store.taskId) {
      try {
        const result = await updateOutline(store.taskId, store.outline.pages)
        if (!result.success) {
          console.error('更新大纲失败:', result.error)
          alert('删除失败：' + result.error)
        } else {
          console.log('大纲更新成功')
          
          // 重新生成所有图片的 URL（因为后端文件已重命名）
          const timestamp = Date.now()
          store.images.forEach(img => {
            if (img.url && img.status === 'done') {
              // 更新 URL 为新的索引
              img.url = `/api/images/${store.taskId}/${img.index}.png?t=${timestamp}`
            }
          })
          console.log('图片 URL 已更新')
          
          // 如果有 recordId，也需要更新历史记录
          if (store.recordId) {
            try {
              const generatedImageIndices = store.images
                .filter(img => img.status === 'done' && img.url)
                .map(img => `${img.index}.png`)
              
              const expectedCount = store.outline.pages.length
              const actualCount = generatedImageIndices.length
              const status = (actualCount >= expectedCount && !hasFailedImages.value) ? 'completed' : 'draft'
              const thumbnail = generatedImageIndices.length > 0 ? generatedImageIndices[0] : undefined

              await updateHistory(store.recordId, {
                outline: store.outline,
                images: {
                  task_id: store.taskId,
                  generated: generatedImageIndices
                },
                status: status,
                thumbnail: thumbnail
              })
              console.log('历史记录已同步')
            } catch (e) {
              console.error('更新历史记录失败:', e)
            }
          }
        }
      } catch (error) {
        console.error('调用 API 失败:', error)
        alert('删除失败，请稍后重试')
      }
    }
  }
}

const addPage = (type: 'cover' | 'content' | 'summary') => {
  store.addPage(type, '')
  // 滚动到底部
  nextTick(() => {
    window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' })
  })
}

const goBack = () => {
  router.back()
}

/**
 * 根据修改后的基调重新生成大纲
 */
async function regenerateOutline() {
  if (!tone.value.trim()) {
    error.value = '基调内容不能为空'
    return
  }

  if (!store.taskId) {
    error.value = '任务ID不存在，无法重新生成大纲'
    return
  }

  // 检查是否已有生成的图片，如果有则提醒用户
  if (hasGeneratedImages.value) {
    showConfirmDialog.value = true
    return
  }

  // 执行生成
  await doRegenerateOutline()
}

/**
 * 执行重新生成大纲
 */
async function doRegenerateOutline() {
  if (!store.taskId) {
    return
  }

  isRegeneratingOutline.value = true
  error.value = ''
  showConfirmDialog.value = false

  try {
    // 第一步：保存修改后的基调
    if (store.taskId) {
      try {
        await updateTone(store.taskId, tone.value)
        console.log('✅ 基调已更新')
        // 更新原始基调，这样按钮会再次禁用
        originalTone.value = tone.value
      } catch (e) {
        console.warn('⚠️ 保存基调失败:', e)
        // 继续执行，不阻断流程
      }
    }

    // 第二步：使用修改后的基调重新生成大纲
    const outlineResult = await generateOutline(
      store.topic || '',
      store.userImages.length > 0 ? store.userImages : undefined,
      tone.value,
      store.taskId  // 使用相同的 task_id
    )

    if (outlineResult.success && outlineResult.pages) {
      // 更新大纲内容
      store.setOutline(outlineResult.outline || '', outlineResult.pages, outlineResult.metadata)
      
      // 重置图片状态
      store.images = outlineResult.pages.map((page) => ({
        index: page.index,
        url: '',
        status: 'error' as const,
        retryable: true
      }))

      // 重置进度状态
      store.progress.current = 0
      store.progress.total = outlineResult.pages.length
      store.progress.status = 'paused'

      // 更新历史记录
      if (store.recordId) {
        try {
          await updateHistory(store.recordId, {
            outline: {
              raw: outlineResult.outline || '',
              pages: outlineResult.pages,
              metadata: outlineResult.metadata
            }
          })
          console.log('✅ 历史记录已更新')
        } catch (e) {
          console.error('更新历史记录失败:', e)
        }
      }

      console.log('✅ 大纲已重新生成')
    } else {
      error.value = outlineResult.error || '生成大纲失败'
    }
  } catch (err: any) {
    error.value = err.message || '网络错误，请重试'
  } finally {
    isRegeneratingOutline.value = false
  }
}

// 批量重试所有失败的图片
async function retryAllFailed() {
  if (!store.taskId) return

  const failedPages = store.getFailedPages()
  if (failedPages.length === 0) return

  isRetrying.value = true

  // 设置所有失败的图片为重试状态
  failedPages.forEach(page => {
    store.setImageRetrying(page.index)
  })

  try {
    await apiRetryFailed(
      store.taskId,
      failedPages,
      // onProgress
      () => {},
      // onComplete
      (event) => {
        if (event.image_url) {
          store.updateImage(event.index, event.image_url)
        }
      },
      // onError
      (event) => {
        store.updateProgress(event.index, 'error', undefined, event.message)
      },
      // onFinish
      () => {
        isRetrying.value = false
      },
      // onStreamError
      (err) => {
        console.error('重试失败:', err)
        isRetrying.value = false
        error.value = '重试失败: ' + err.message
      }
    )
  } catch (e) {
    isRetrying.value = false
    error.value = '重试失败: ' + String(e)
  }
}

// 停止生成
async function stopGeneration() {
  console.log('点击停止按钮，当前 taskId:', store.taskId, 'isStopping:', isStopping.value)
  
  // 如果 taskId 还没有，尝试从已生成的图片 URL 中提取
  let taskIdToUse = store.taskId
  if (!taskIdToUse) {
    // 查找第一个已生成的图片，从 URL 中提取 task_id
    const generatedImage = store.images.find(img => img.url && img.status === 'done')
    if (generatedImage && generatedImage.url) {
      // URL 格式: /api/images/{task_id}/{filename}
      const match = generatedImage.url.match(/\/api\/images\/([^\/]+)\//)
      if (match && match[1]) {
        taskIdToUse = match[1]
        store.taskId = taskIdToUse
        console.log('从图片 URL 中提取 taskId:', taskIdToUse)
      }
    }
  }
  
  if (!taskIdToUse) {
    console.warn('taskId 未设置，无法停止')
    error.value = '任务ID未就绪，请稍后再试'
    return
  }
  
  if (isStopping.value) {
    console.log('正在停止中，忽略重复点击')
    return
  }

  isStopping.value = true
  try {
    console.log('发送停止请求，taskId:', taskIdToUse)
    const result = await apiStopGeneration(taskIdToUse)
    console.log('停止请求响应:', result)
    
    if (result.success) {
      store.pauseGeneration()
      console.log('已暂停生成')
    } else {
      error.value = result.error || '停止失败'
    }
  } catch (e) {
    console.error('停止失败:', e)
    error.value = '停止失败: ' + String(e)
  } finally {
    isStopping.value = false
  }
}

// 继续生成
async function continueGeneration() {
  if (!store.taskId || isContinuing.value) return

  isContinuing.value = true
  error.value = ''

  store.resumeGeneration()

  // 设置所有未完成的图片为生成中状态（后端会自动扫描）
  store.images.forEach(img => {
    if (img.status !== 'done' && img.status !== 'error') {
      img.status = 'generating'
    }
  })

  try {
    // 只需要传入 taskId，后端会自动扫描未完成的页面
    await apiContinueGeneration(
      store.taskId,
      // onProgress
      (event) => {
        console.log('Continue Progress:', event)
      },
      // onComplete
      (event) => {
        console.log('Continue Complete:', event)
        if (event.image_url) {
          store.updateProgress(event.index, 'done', event.image_url)
        }
      },
      // onError
      (event) => {
        console.error('Continue Error:', event)
        store.updateProgress(event.index, 'error', undefined, event.message)
      },
      // onFinish
      async (event) => {
        console.log('Continue Finish:', event)
        store.finishGeneration(event.task_id)
        isContinuing.value = false

        // 更新历史记录
        if (store.recordId) {
          try {
            const generatedImages = event.images.filter(img => img !== null)
            // 判断状态：所有图片都生成完成才算已完成，其他都是草稿
            const expectedCount = store.outline.pages.length
            const actualCount = generatedImages.length
            const status = (actualCount >= expectedCount && !hasFailedImages.value) ? 'completed' : 'draft'
            const thumbnail = generatedImages.length > 0 ? generatedImages[0] : undefined

            await updateHistory(store.recordId, {
              images: {
                task_id: event.task_id,
                generated: generatedImages
              },
              status: status,
              thumbnail: thumbnail
            })
          } catch (e) {
            console.error('更新历史记录失败:', e)
          }
        }
      },
      // onStopped
      (event) => {
        console.log('Continue Stopped:', event)
        store.pauseGeneration()
        isContinuing.value = false
      },
      // onStreamError
      (err) => {
        console.error('Continue Stream Error:', err)
        error.value = '继续生成失败: ' + err.message
        isContinuing.value = false
        store.pauseGeneration()
      }
    )
  } catch (e) {
    isContinuing.value = false
    store.pauseGeneration()
    error.value = '继续生成失败: ' + String(e)
  }
}

// 开始批量生成
async function startBatchGeneration() {
  if (store.outline.pages.length === 0) {
    error.value = '没有可生成的页面'
    return
  }

  // 如果有已生成的图片，不自动开始生成
  const hasGeneratedImages = store.images.some(img => img.status === 'done')
  
  if (!hasGeneratedImages) {
    store.startGeneration()
    
    // 确保有 taskId（应该在大纲生成时已创建）
    if (!store.taskId) {
      error.value = '任务ID未找到，请重新生成大纲'
      return
    }

    // 开始生成图片
    generateImagesPost(
      store.outline.pages,
      store.taskId,
      store.outline.raw,
      // onProgress
      (event) => {
        console.log('Progress:', event)
        // 如果 progress 事件中包含 task_id，立即保存（用于停止功能）
        if (event.task_id && !store.taskId) {
          store.taskId = event.task_id
          console.log('已保存 task_id:', event.task_id)
        }
      },
      // onComplete
      (event) => {
        console.log('Complete:', event)
        if (event.image_url) {
          store.updateProgress(event.index, 'done', event.image_url)
        }
      },
      // onError
      (event) => {
        console.error('Error:', event)
        store.updateProgress(event.index, 'error', undefined, event.message)
      },
      // onFinish
      async (event) => {
        console.log('Finish:', event)
        store.finishGeneration(event.task_id)

        // 更新历史记录
        if (store.recordId) {
          try {
            // 收集所有生成的图片文件名
            const generatedImages = event.images.filter(img => img !== null)

            // 确定状态：所有图片都生成完成才算已完成，其他都是草稿
            const expectedCount = store.outline.pages.length
            const actualCount = generatedImages.length
            const status = (actualCount >= expectedCount && !hasFailedImages.value) ? 'completed' : 'draft'

            // 获取封面图作为缩略图（只保存文件名，不是完整URL）
            const thumbnail = generatedImages.length > 0 ? generatedImages[0] : undefined

            await updateHistory(store.recordId, {
              images: {
                task_id: event.task_id,
                generated: generatedImages
              },
              status: status,
              thumbnail: thumbnail
            })
            console.log('历史记录已更新')
          } catch (e) {
            console.error('更新历史记录失败:', e)
          }
        }
      },
      // onStreamError
      (err) => {
        console.error('Stream Error:', err)
        error.value = '生成失败: ' + err.message
      },
      // userImages - 用户上传的参考图片
      store.userImages.length > 0 ? store.userImages : undefined,
      // userTopic - 用户原始输入
      store.topic,
      // onStopped - 生成被停止
      (event) => {
        console.log('Stopped:', event)
        // 保存 task_id 以便继续生成
        if (event.task_id) {
          store.taskId = event.task_id
        }
        store.pauseGeneration()
      },
      // referenceMode - 参考图模式
      referenceMode.value
    )
  }
}

const startGeneration = () => {
  // 改为调用批量生成，而不是跳转页面
  startBatchGeneration()
}

// 查看大图
function viewLargeImage(pageIndex: number) {
  const image = getImageForPage(pageIndex)
  if (image?.url && store.taskId) {
    // 找到当前图片在已生成图片列表中的索引
    const index = generatedImageIndices.value.indexOf(pageIndex)
    if (index !== -1) {
      currentImageIndex.value = index
      loadImageByIndex(index)
      viewingLargeImage.value = true
      // 添加键盘事件监听
      document.addEventListener('keydown', handleKeyDown)
    }
  }
}

// 根据索引加载图片
function loadImageByIndex(index: number) {
  const pageIndex = generatedImageIndices.value[index]
  if (pageIndex !== undefined && store.taskId) {
    const filename = `${pageIndex}.png`
    largeImageUrl.value = `/api/images/${store.taskId}/${filename}?thumbnail=false`
    currentImageIndex.value = index
  }
}

// 上一张图片
function previousImage() {
  if (hasPreviousImage.value) {
    loadImageByIndex(currentImageIndex.value - 1)
  }
}

// 下一张图片
function nextImage() {
  if (hasNextImage.value) {
    loadImageByIndex(currentImageIndex.value + 1)
  }
}

// 键盘事件处理
function handleKeyDown(event: KeyboardEvent) {
  if (!viewingLargeImage.value) return

  switch (event.key) {
    case 'ArrowLeft':
      event.preventDefault()
      previousImage()
      break
    case 'ArrowRight':
      event.preventDefault()
      nextImage()
      break
    case 'Escape':
      event.preventDefault()
      closeLargeImage()
      break
  }
}

// 关闭大图查看
function closeLargeImage() {
  viewingLargeImage.value = false
  largeImageUrl.value = ''
  currentImageIndex.value = 0
  // 移除键盘事件监听
  document.removeEventListener('keydown', handleKeyDown)
}

// 下载单张图片
function downloadOne(pageIndex: number, displayIndex?: number) {
  const image = getImageForPage(pageIndex)
  if (image?.url && store.taskId) {
    // 如果没有传入 displayIndex，则计算当前显示序号
    let finalDisplayIndex = displayIndex
    if (finalDisplayIndex === undefined) {
      finalDisplayIndex = store.outline.pages.findIndex(p => p.index === pageIndex) + 1
    }
    
    const link = document.createElement('a')
    // 去掉 thumbnail 参数，获取原图
    const baseUrl = image.url.split('?')[0]
    link.href = baseUrl + '?thumbnail=false'
    link.download = `rednote_page_${finalDisplayIndex}.png`
    link.click()
  }
}

// 批量下载所有图片
function downloadAll() {
  if (store.recordId) {
    // 如果有 recordId，使用后端打包下载接口
    const link = document.createElement('a')
    link.href = `/api/history/${store.recordId}/download`
    link.click()
  } else {
    // 否则按照当前页面顺序逐个下载
    let downloadCount = 0
    store.outline.pages.forEach((page, displayIndex) => {
      const image = getImageForPage(page.index)
      if (image?.url && image.status === 'done') {
        setTimeout(() => {
          const link = document.createElement('a')
          const baseUrl = image.url.split('?')[0]
          link.href = baseUrl + '?thumbnail=false'
          link.download = `rednote_page_${displayIndex + 1}.png`
          link.click()
        }, downloadCount * 300) // 每张图片间隔 300ms
        downloadCount++
      }
    })
  }
}

// 生成图片（首次生成或重新生成）
async function generatePageImage(pageIndex: number) {
  if (!store.taskId) {
    alert('任务ID未找到，无法生成图片')
    return
  }

  const page = store.outline.pages.find(p => p.index === pageIndex)
  if (!page) {
    alert('页面信息未找到')
    return
  }

  // 如果正在生成，忽略
  if (generatingImages.value.has(pageIndex) || regeneratingImages.value.has(pageIndex)) {
    return
  }

  const image = getImageForPage(pageIndex)
  const isRegenerating = image?.status === 'error' && image?.error

  // 如果是重新生成（有错误状态），使用重新生成API
  if (isRegenerating) {
    await regeneratePageImage(pageIndex)
    return
  }

  // 首次生成，使用生成图片API
  generatingImages.value.add(pageIndex)
  
  // 初始化图片状态
  if (!image) {
    store.images.push({
      index: pageIndex,
      url: '',
      status: 'generating'
    })
  } else {
    store.updateProgress(pageIndex, 'generating')
  }

  try {
    // 构建上下文信息
    const context = {
      fullOutline: store.outline.raw || '',
      userTopic: store.topic || ''
    }

    // 调用生成图片 API（只生成单张）
    await generateImagesPost(
      [page],
      store.taskId,
      store.outline.raw || '',
      // onProgress
      (event) => {
        console.log('Generate Progress:', event)
      },
      // onComplete
      (event) => {
        console.log('Generate Complete:', event)
        if (event.image_url) {
          store.updateProgress(pageIndex, 'done', event.image_url)
          generatingImages.value.delete(pageIndex)
        }
      },
      // onError
      (event) => {
        console.error('Generate Error:', event)
        store.updateProgress(pageIndex, 'error', undefined, event.message)
        generatingImages.value.delete(pageIndex)
      },
      // onFinish
      (event) => {
        console.log('Generate Finish:', event)
        generatingImages.value.delete(pageIndex)
      },
      // onStreamError
      (err) => {
        console.error('Generate Stream Error:', err)
        store.updateProgress(pageIndex, 'error', undefined, err.message)
        generatingImages.value.delete(pageIndex)
      },
      // userImages
      store.userImages.length > 0 ? store.userImages : undefined,
      // userTopic
      store.topic,
      // onStopped
      undefined,
      // referenceMode
      referenceMode.value
    )
  } catch (e) {
    console.error('生成图片失败:', e)
    store.updateProgress(pageIndex, 'error', undefined, String(e))
    generatingImages.value.delete(pageIndex)
  }
}

// 重新生成图片
async function regeneratePageImage(pageIndex: number) {
  if (!store.taskId) {
    alert('任务ID未找到，无法重新生成')
    return
  }

  const page = store.outline.pages.find(p => p.index === pageIndex)
  if (!page) {
    alert('页面信息未找到')
    return
  }

  // 如果正在重新生成，忽略
  if (regeneratingImages.value.has(pageIndex)) {
    return
  }

  // 设置为重新生成状态
  regeneratingImages.value.add(pageIndex)
  store.setImageRetrying(pageIndex)

  try {
    // 构建上下文信息
    const context = {
      fullOutline: store.outline.raw || '',
      userTopic: store.topic || ''
    }

    // 调用重新生成 API
    const result = await apiRegenerateImage(
      store.taskId,
      page,
      true, // useReference
      context,
      referenceMode.value // referenceMode
    )

    if (result.success && result.image_url) {
      // 更新图片
      store.updateImage(pageIndex, result.image_url)
    } else {
      // 更新为错误状态
      store.updateProgress(pageIndex, 'error', undefined, result.error)
    }
  } catch (e) {
    console.error('重新生成图片失败:', e)
    store.updateProgress(pageIndex, 'error', undefined, String(e))
  } finally {
    regeneratingImages.value.delete(pageIndex)
  }
}
</script>

<style scoped>
/* 小红书元数据展示区域 */
.metadata-section {
  margin-top: 20px;
}

.metadata-card {
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  overflow: hidden;
}

.metadata-header {
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color);
  background: linear-gradient(135deg, rgba(255, 36, 66, 0.05) 0%, rgba(255, 36, 66, 0.02) 100%);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.metadata-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--text-main);
}

.btn-collapse {
  background: none;
  border: none;
  cursor: pointer;
  padding: 4px;
  display: flex;
  align-items: center;
  color: #999;
  transition: color 0.2s;
}

.btn-collapse:hover {
  color: var(--primary);
}

.metadata-content {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.metadata-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.metadata-label {
  font-size: 13px;
  font-weight: 600;
  color: #666;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  margin-bottom: 8px;
}

.metadata-label::before {
  content: '';
  width: 3px;
  height: 14px;
  background: var(--primary);
  border-radius: 2px;
  margin-right: 6px;
}

.char-count {
  font-size: 12px;
  color: #999;
  font-weight: 400;
}

.char-count.over-limit {
  color: #ff4d4f;
  font-weight: 600;
}

.char-count.under-limit {
  color: #faad14;
}

.metadata-input {
  width: 100%;
  padding: 12px 16px;
  border: 2px solid #e8e8e8;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 500;
  line-height: 1.6;
  color: var(--text-main);
  transition: all 0.2s;
  background: white;
}

.metadata-input:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 0 3px rgba(255, 36, 66, 0.1);
}

.metadata-input::placeholder {
  color: #ccc;
  font-weight: 400;
}

.title-input {
  font-size: 16px;
  font-weight: 600;
  background: linear-gradient(135deg, #fff5f5 0%, #ffffff 100%);
}

.metadata-textarea {
  width: 100%;
  padding: 12px 16px;
  border: 2px solid #e8e8e8;
  border-radius: 8px;
  font-size: 14px;
  line-height: 1.8;
  color: var(--text-main);
  transition: all 0.2s;
  resize: vertical;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue', sans-serif;
  background: white;
}

.metadata-textarea:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 0 3px rgba(255, 36, 66, 0.1);
}

.metadata-textarea::placeholder {
  color: #ccc;
}

.content-textarea {
  min-height: 150px;
}

.tags-textarea {
  background: #f9f9f9;
}

.tags-preview {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
  padding: 12px;
  background: white;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  min-height: 48px;
}

.tag-item {
  display: inline-block;
  padding: 6px 12px;
  background: linear-gradient(135deg, #fff0f0 0%, #fff5f5 100%);
  border: 1px solid #ffd4d4;
  border-radius: 16px;
  font-size: 13px;
  color: var(--primary);
  font-weight: 500;
  transition: all 0.2s;
}

.tag-item:hover {
  background: var(--primary);
  border-color: var(--primary);
  color: white;
  transform: translateY(-2px);
  box-shadow: 0 2px 8px rgba(255, 36, 66, 0.3);
}

/* 基调展示区域 */
.tone-section {
  margin-top: 20px;
}

.tone-card {
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  overflow: hidden;
}

.tone-header {
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color);
  background: linear-gradient(135deg, rgba(255, 36, 66, 0.05) 0%, rgba(255, 36, 66, 0.02) 100%);
}

.tone-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--text-main);
}

.tone-content {
  padding: 20px;
}

.tone-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
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
  padding: 8px 16px;
  font-size: 13px;
  display: flex;
  align-items: center;
}

/* 确认对话框 */
.confirm-dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  animation: fadeIn 0.2s ease-out;
}

.confirm-dialog {
  background: white;
  border-radius: 16px;
  width: 90%;
  max-width: 500px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  animation: slideUp 0.3s ease-out;
}

.confirm-dialog-header {
  padding: 24px 24px 16px;
  border-bottom: 1px solid var(--border-color);
}

.confirm-dialog-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: var(--text-main);
}

.confirm-dialog-content {
  padding: 24px;
}

.confirm-dialog-content p {
  margin: 0 0 12px 0;
  font-size: 14px;
  line-height: 1.6;
  color: var(--text-main);
}

.confirm-dialog-content ul {
  margin: 12px 0;
  padding-left: 24px;
  color: var(--text-main);
}

.confirm-dialog-content li {
  margin: 8px 0;
  font-size: 14px;
  line-height: 1.6;
}

.confirm-dialog-footer {
  padding: 16px 24px 24px;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  border-top: 1px solid var(--border-color);
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slideUp {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

/* 网格布局 */
.outline-grid {
  display: grid;
  /* 响应式列：最小宽度 280px，自动填充 */
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 24px;
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 20px;
}

/* 翻转卡片容器 */
.flip-card-wrapper {
  perspective: 1000px;
  position: relative;
  aspect-ratio: 3/4;
  min-height: 400px;
}

.flip-card {
  position: relative;
  width: 100%;
  height: 100%;
  transition: transform 0.6s;
  transform-style: preserve-3d;
}

.flip-card.flipped {
  transform: rotateY(180deg);
}

.flip-card-face {
  position: absolute;
  width: 100%;
  height: 100%;
  backface-visibility: hidden;
  -webkit-backface-visibility: hidden;
}

.flip-card-front {
  z-index: 2;
}

.flip-card-back {
  transform: rotateY(180deg);
}

.outline-card {
  display: flex;
  flex-direction: column;
  padding: 16px; /* 减小内边距 */
  transition: all 0.2s ease;
  border: none;
  border-radius: 8px; /* 较小的圆角 */
  background: white;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
  position: relative;
  width: 100%;
  height: 100%;
}

.outline-card:hover {
  box-shadow: 0 8px 24px rgba(0,0,0,0.08);
}

.image-card {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.flip-card-wrapper.dragging-over .outline-card {
  border: 2px dashed var(--primary);
  opacity: 0.8;
}

/* 顶部栏 */
.card-top-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #f5f5f5;
}

.page-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.page-number {
  font-size: 14px;
  font-weight: 700;
  color: #ccc;
  font-family: 'Inter', sans-serif;
}

.page-type {
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.page-type.cover { color: #FF4D4F; background: #FFF1F0; }
.page-type.content { color: #8c8c8c; background: #f5f5f5; }
.page-type.summary { color: #52C41A; background: #F6FFED; }

.card-controls {
  display: flex;
  gap: 8px;
  opacity: 0.4;
  transition: opacity 0.2s;
}
.outline-card:hover .card-controls { opacity: 1; }

.drag-handle {
  cursor: grab;
  padding: 2px;
}
.drag-handle:active { cursor: grabbing; }

.icon-btn {
  background: none;
  border: none;
  cursor: pointer;
  color: #999;
  padding: 2px;
  transition: color 0.2s;
}
.icon-btn:hover { color: #FF4D4F; }

/* 文本区域 - 核心 */
.textarea-paper {
  flex: 1; /* 占据剩余空间 */
  width: 100%;
  border: none;
  background: transparent;
  padding: 0;
  font-size: 16px; /* 更大的字号 */
  line-height: 1.7; /* 舒适行高 */
  color: #333;
  resize: none; /* 禁止手动拉伸，保持卡片整体感 */
  font-family: inherit;
  margin-bottom: 10px;
  min-height: 0;
  overflow-y: auto;
}

.textarea-paper:focus {
  outline: none;
}

.word-count {
  text-align: right;
  font-size: 11px;
  color: #ddd;
  flex-shrink: 0;
}

/* 添加卡片 */
.add-card-dashed {
  border: 2px dashed #eee;
  background: transparent;
  box-shadow: none;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  min-height: 360px;
  color: #ccc;
  transition: all 0.2s;
}

.add-card-dashed:hover {
  border-color: var(--primary);
  color: var(--primary);
  background: rgba(255, 36, 66, 0.02);
}

.add-content {
  text-align: center;
}

.add-icon {
  font-size: 32px;
  font-weight: 300;
  margin-bottom: 8px;
}

/* 保存状态提示 */
.save-status {
  margin-left: 12px;
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 4px;
  vertical-align: middle;
}

.save-status.saving {
  color: #1890FF;
  background: #E6F4FF;
}

.save-status.saved {
  color: #52C41A;
  background: #F6FFED;
}

/* 图片显示区域（图片面） */
.page-image-container-full {
  flex: 1;
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 8px;
  min-height: 0;
  overflow: hidden;
}

.page-image-preview-full {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  background: #f9f9f9;
  overflow: hidden;
  position: relative;
}

.page-image-preview-full img {
  max-width: 100%;
  max-height: 100%;
  width: auto;
  height: auto;
  object-fit: contain;
}

/* 重新生成按钮悬浮层 */
.image-regenerate-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.2s;
  border-radius: 6px;
}

.page-image-preview-full:hover .image-regenerate-overlay {
  opacity: 1;
}

.overlay-buttons {
  display: flex;
  flex-direction: column;
  gap: 12px;
  align-items: center;
}

.overlay-action-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 20px;
  background: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  color: #333;
  transition: all 0.2s;
  font-weight: 500;
  min-width: 140px;
  justify-content: center;
}

.overlay-action-btn:hover:not(:disabled) {
  background: var(--primary);
  color: white;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(255, 36, 66, 0.3);
}

.overlay-action-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
  transform: none;
}

/* 大图查看模态框 */
.large-image-modal {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.95);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
  animation: fadeIn 0.2s;
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.large-image-container {
  position: relative;
  max-width: 90vw;
  max-height: 90vh;
  display: flex;
  align-items: center;
  justify-content: center;
}

.large-image-container img {
  max-width: 100%;
  max-height: 90vh;
  object-fit: contain;
  border-radius: 8px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
  transition: opacity 0.2s;
}

.close-large-image-btn {
  position: absolute;
  top: -40px;
  right: 0;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
  z-index: 10;
}

.close-large-image-btn:hover {
  background: rgba(255, 255, 255, 0.2);
  transform: scale(1.1);
}

/* 导航箭头按钮 */
.nav-arrow-btn {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  width: 50px;
  height: 50px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
  z-index: 10;
}

.nav-arrow-btn:hover {
  background: rgba(255, 255, 255, 0.2);
  transform: translateY(-50%) scale(1.1);
}

.nav-arrow-left {
  left: 20px;
}

.nav-arrow-right {
  right: 20px;
}

/* 图片信息 */
.image-info {
  position: absolute;
  bottom: -40px;
  left: 50%;
  transform: translateX(-50%);
  color: white;
  font-size: 14px;
  background: rgba(0, 0, 0, 0.5);
  padding: 6px 16px;
  border-radius: 20px;
  z-index: 10;
}

.page-image-placeholder-full {
  width: 100%;
  height: 100%;
  background: #f9f9f9;
  border-radius: 6px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.generate-image-prompt {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.generate-image-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 20px;
  background: var(--primary);
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s;
  margin-top: 8px;
}

.generate-image-btn:hover:not(:disabled) {
  background: #ff3d5a;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(255, 36, 66, 0.3);
}

.generate-image-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.error-placeholder-small {
  background: #fff5f5;
}

.error-icon-small {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #ff4d4f;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: bold;
}

.status-text-small {
  font-size: 11px;
  color: #999;
}

.spinner-small {
  width: 16px;
  height: 16px;
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

/* 切换按钮 */
.flip-toggle-btn {
  position: absolute;
  bottom: 12px;
  right: 12px;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: white;
  border: 1px solid #e0e0e0;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  z-index: 100;
  transition: all 0.2s;
  color: #666;
}

.flip-toggle-btn:hover {
  background: var(--primary);
  color: white;
  border-color: var(--primary);
  transform: scale(1.1);
  box-shadow: 0 4px 12px rgba(255, 36, 66, 0.3);
}

/* 浮动工具栏（仅操作按钮） */
.generation-toolbar {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 1000;
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  padding: 12px;
  min-width: 200px;
  max-width: 300px;
  animation: slideInRight 0.3s ease-out;
}

@keyframes slideInRight {
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}


.progress-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.progress-label {
  font-size: 14px;
  font-weight: 600;
  color: #333;
}

.progress-percent {
  font-size: 16px;
  font-weight: 700;
  color: var(--primary);
}

.progress-container {
  width: 100%;
  height: 8px;
  background: #f0f0f0;
  border-radius: 4px;
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  background: var(--primary);
  border-radius: 4px;
  transition: width 0.3s ease;
}

.progress-status {
  font-size: 12px;
  color: #666;
  text-align: center;
  margin-top: 8px;
}

/* 进度卡片 */
.progress-section {
  margin-bottom: 0;
}

.progress-card {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.toolbar-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.toolbar-btn {
  flex: 1;
  min-width: 100px;
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.toolbar-btn.btn-primary {
  background: var(--primary);
  color: white;
}

.toolbar-btn.btn-primary:hover:not(:disabled) {
  background: #ff3d5a;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(255, 36, 66, 0.3);
}

.toolbar-btn.btn-danger {
  background: #ff4d4f;
  color: white;
}

.toolbar-btn.btn-danger:hover:not(:disabled) {
  background: #ff7875;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(255, 77, 79, 0.3);
}

.toolbar-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.toolbar-error {
  margin-top: 12px;
  padding: 8px 12px;
  background: #fff1f0;
  border: 1px solid #ffccc7;
  border-radius: 6px;
  color: #ff4d4f;
  font-size: 12px;
}

/* 参考图模式选择器 */
.reference-mode-selector {
  margin-top: 16px;
  padding: 12px;
  background: #f9f9f9;
  border-radius: 8px;
  border: 1px solid #e8e8e8;
}

.reference-mode-label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: #666;
  margin-bottom: 8px;
}

.reference-mode-options {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

.reference-mode-option {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #333;
  cursor: pointer;
  user-select: none;
}

.reference-mode-option input[type="radio"] {
  cursor: pointer;
  margin: 0;
}

.reference-mode-option:has(input:disabled) {
  opacity: 0.5;
  cursor: not-allowed;
}

.reference-mode-option:has(input:checked) {
  color: var(--primary);
  font-weight: 500;
}

.option-hint {
  font-size: 11px;
  color: #999;
  font-style: italic;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .generation-toolbar {
    top: 10px;
    right: 10px;
    left: 10px;
    min-width: auto;
    max-width: none;
  }
  
  .toolbar-actions {
    flex-direction: column;
  }
  
  .toolbar-btn {
    width: 100%;
  }

  .reference-mode-options {
    flex-direction: column;
    gap: 8px;
  }
}
</style>
