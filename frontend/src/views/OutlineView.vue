<template>
  <div class="outline-page">
    <!-- 浮动错误提示 -->
    <div v-if="error" class="error-toast">
      <div class="error-content">
        {{ error }}
      </div>
    </div>

    <!-- 主内容区域 - 使用flex布局 -->
    <div class="outline-content">
      <!-- 左侧内容区 -->
      <div class="outline-main">
        <!-- 主题编辑区域 -->
        <div v-if="topic" class="section-card topic-section">
          <div class="card-header">
            <h3 class="card-title">主题内容</h3>
            <button class="btn btn-primary btn-sm" @click="regenerateTone"
              :disabled="isRegeneratingTone || !localTopic.trim()" :title="!localTopic.trim() ? '主题内容不能为空' : ''">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
                stroke-linecap="round" stroke-linejoin="round">
                <path d="M23 4v6h-6"></path>
                <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
              </svg>
              {{ isRegeneratingTone ? '生成中...' : '重新生成基调' }}
            </button>
          </div>
          <div class="card-body">
            <input v-model="localTopic" class="topic-input" placeholder="输入主题内容..." @input="onTopicChange" />
          </div>
        </div>

        <!-- 基调展示区域 -->
        <div v-if="tone" class="section-card tone-section">
          <div class="card-header">
            <h3 class="card-title">内容基调</h3>
            <button class="btn btn-primary btn-sm" @click="regenerateOutline"
              :disabled="isRegeneratingOutline || !toneHasChanged" :title="!toneHasChanged ? '请先修改基调内容' : ''">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
                stroke-linecap="round" stroke-linejoin="round">
                <path d="M20.24 12.24a6 6 0 0 0-8.49-8.49L5 10.5V19h8.5z"></path>
                <line x1="16" y1="8" x2="2" y2="22"></line>
                <line x1="17.5" y1="15" x2="9" y2="15"></line>
              </svg>
              {{ isRegeneratingOutline ? '生成中...' : '生成大纲' }}
            </button>
          </div>
          <div class="card-body">
            <textarea v-model="tone" class="tone-textarea" placeholder="编辑内容基调..." rows="12"></textarea>
          </div>
        </div>

        <!-- 小红书内容编辑区域 -->
        <div v-if="outline.metadata || localMetadata" class="section-card metadata-section">
          <div class="card-header">
            <h3 class="card-title">📱 小红书内容</h3>
            <button class="btn-icon" @click="metadataCollapsed = !metadataCollapsed"
              :title="metadataCollapsed ? '展开' : '收起'">
              <svg v-if="metadataCollapsed" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="6 9 12 15 18 9"></polyline>
              </svg>
              <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
                stroke-linecap="round" stroke-linejoin="round">
                <polyline points="18 15 12 9 6 15"></polyline>
              </svg>
            </button>
          </div>
          <div v-if="!metadataCollapsed" class="card-body">
            <!-- 标题 -->
            <div class="metadata-item">
              <label class="metadata-label">
                标题
                <span class="char-count" :class="{ 'over-limit': titleCharCount > 20 }">
                  {{ titleCharCount }}/20
                </span>
              </label>
              <input v-model="localMetadata.title" class="metadata-input title-input" placeholder="输入小红书标题（20字以内）..."
                maxlength="30" @input="onMetadataChange" />
            </div>

            <!-- 正文 -->
            <div class="metadata-item">
              <label class="metadata-label">
                正文
                <span class="char-count"
                  :class="{ 'under-limit': contentCharCount < 100, 'over-limit': contentCharCount > 300 }">
                  {{ contentCharCount }}/100-300
                </span>
              </label>
              <textarea v-model="localMetadata.content" class="metadata-textarea content-textarea"
                placeholder="输入小红书正文内容（100-300字）..." rows="6" @input="onMetadataChange"></textarea>
            </div>

            <!-- 标签 -->
            <div class="metadata-item">
              <label class="metadata-label">
                标签
                <span class="char-count">{{ tagCount }}个</span>
              </label>
              <textarea v-model="localMetadata.tags" class="metadata-textarea tags-textarea"
                placeholder="输入标签，用空格分隔（例如：#手冲咖啡 #咖啡教程 #居家咖啡）..." rows="2" @input="onMetadataChange"></textarea>
              <div v-if="localMetadata.tags" class="tags-preview">
                <span v-for="(tag, idx) in localMetadata.tags.split(/\s+/).filter(t => t)" :key="idx"
                  class="tag-item">{{ tag }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 页面头部和操作栏 -->
        <div class="section-card page-header-card">
          <div class="header-content">
            <div class="header-info">
              <h1 class="page-title">编辑大纲</h1>
              <p class="page-subtitle">
                调整页面顺序，修改文案，打造完美内容
                <span v-if="saveStatus === 'saving'" class="save-status saving">保存中...</span>
                <span v-else-if="saveStatus === 'saved'" class="save-status saved">已保存</span>
              </p>
            </div>
            <!-- 操作按钮组 -->
            <div class="action-buttons">
              <!-- 停止生成按钮（正在生成时显示） -->
              <button v-if="isGenerating || isStopping" class="btn btn-danger btn-sm" @click="stopGeneration"
                :disabled="isStopping">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
                  stroke-linecap="round" stroke-linejoin="round">
                  <rect x="6" y="6" width="12" height="12" rx="2"></rect>
                </svg>
                {{ isStopping ? '停止中...' : '停止生成' }}
              </button>
              <!-- 一键下载按钮（有已生成的图片时显示） -->
              <button v-if="hasGeneratedImages && !isGenerating && !isStopping" class="btn btn-secondary btn-sm" @click="downloadAll">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
                  stroke-linecap="round" stroke-linejoin="round">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                  <polyline points="7 10 12 15 17 10"></polyline>
                  <line x1="12" y1="15" x2="12" y2="3"></line>
                </svg>
                下载
              </button>
              <!-- 默认显示开始生成按钮 -->
              <button v-if="!isGenerating && !isStopping && hasUnfinishedImages" class="btn btn-primary btn-sm"
                @click="startGeneration">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
                  stroke-linecap="round" stroke-linejoin="round">
                  <path d="M20.24 12.24a6 6 0 0 0-8.49-8.49L5 10.5V19h8.5z"></path>
                  <line x1="16" y1="8" x2="2" y2="22"></line>
                  <line x1="17.5" y1="15" x2="9" y2="15"></line>
                </svg>
                {{ hasGeneratedImages ? '继续生成' : '开始生成' }}
              </button>
            </div>
          </div>
          <!-- 参考图模式选择 -->
          <div class="reference-mode-selector">
            <label class="reference-mode-label">参考图模式：</label>
            <div class="reference-mode-options">
              <label class="reference-mode-option">
                <input type="radio" v-model="referenceMode" value="custom" :disabled="userImages.length === 0" />
                <span>自定义参考图</span>
                <span v-if="userImages.length === 0" class="option-hint">（需上传）</span>
              </label>
              <label class="reference-mode-option">
                <input type="radio" v-model="referenceMode" value="cover" />
                <span>封面参考</span>
              </label>
              <label class="reference-mode-option">
                <input type="radio" v-model="referenceMode" value="previous" />
                <span>上一张参考</span>
              </label>
            </div>
          </div>
        </div>

        <!-- 大纲网格 -->
        <div class="outline-grid">
          <div v-for="(page, idx) in outline.pages" :key="page.id ?? `temp-${idx}`" class="flip-card-wrapper" :draggable="true"
            @dragstart="onDragStart($event, idx)" @dragover.prevent="onDragOver($event, idx)"
            @drop="onDrop($event, idx)" :class="{ 'dragging-over': dragOverIndex === idx }">
            <div class="flip-card" :class="{ 'flipped': page.id && flippedCards.has(page.id) }">
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
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#999" stroke-width="2"
                          stroke-linecap="round" stroke-linejoin="round">
                          <circle cx="9" cy="12" r="1"></circle>
                          <circle cx="9" cy="5" r="1"></circle>
                          <circle cx="9" cy="19" r="1"></circle>
                          <circle cx="15" cy="12" r="1"></circle>
                          <circle cx="15" cy="5" r="1"></circle>
                          <circle cx="15" cy="19" r="1"></circle>
                        </svg>
                      </div>
                      <button class="icon-btn" @click.stop="deletePageByPage(page)" title="删除此页">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                          stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                          <line x1="18" y1="6" x2="6" y2="18"></line>
                          <line x1="6" y1="6" x2="18" y2="18"></line>
                        </svg>
                      </button>
                    </div>
                  </div>

                  <textarea v-model="page.content" class="textarea-paper" placeholder="在此输入文案..."
                    @input="onPageContentInput(page)" />

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
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#999" stroke-width="2"
                          stroke-linecap="round" stroke-linejoin="round">
                          <circle cx="9" cy="12" r="1"></circle>
                          <circle cx="9" cy="5" r="1"></circle>
                          <circle cx="9" cy="19" r="1"></circle>
                          <circle cx="15" cy="12" r="1"></circle>
                          <circle cx="15" cy="5" r="1"></circle>
                          <circle cx="15" cy="19" r="1"></circle>
                        </svg>
                      </div>
                      <button class="icon-btn" @click.stop="deletePageByPage(page)" title="删除此页">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                          stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                          <line x1="18" y1="6" x2="6" y2="18"></line>
                          <line x1="6" y1="6" x2="18" y2="18"></line>
                        </svg>
                      </button>
                    </div>
                  </div>

                  <!-- 图片内容 -->
                  <div class="page-image-container-full">
                    <!-- 已生成的图片 -->
                    <div v-if="getImageForPage(page)?.status === 'done' && getImageForPage(page)?.url"
                      class="page-image-preview-full">
                      <img :src="getImageForPage(page)?.url" :alt="`第 ${page.index + 1} 页`" />
                      <!-- 重新生成按钮（悬浮显示） -->
                      <div class="image-regenerate-overlay">
                        <div class="overlay-buttons">
                          <button class="overlay-action-btn" @click.stop="viewLargeImage(page.id)" title="查看大图">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                              stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                              <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                              <circle cx="12" cy="12" r="3"></circle>
                            </svg>
                            <span>查看大图</span>
                          </button>
                          <button class="overlay-action-btn" @click.stop="downloadOne(page.id, idx + 1)"
                            title="下载此图">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                              stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                              <polyline points="7 10 12 15 17 10"></polyline>
                              <line x1="12" y1="15" x2="12" y2="3"></line>
                            </svg>
                            <span>下载</span>
                          </button>
                          <button class="overlay-action-btn" @click.stop="regeneratePageImage(page.id)"
                            :disabled="!!page.id && regeneratingImages.has(page.id)" title="重新生成图片">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                              stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                              <path d="M23 4v6h-6"></path>
                              <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
                            </svg>
                            <span>{{ page.id && regeneratingImages.has(page.id) ? '生成中...' : '重新生成' }}</span>
                          </button>
                        </div>
                      </div>
                    </div>
                    <!-- 生成中/重试中状态 -->
                    <div
                      v-else-if="getImageForPage(page)?.status === 'generating' || getImageForPage(page)?.status === 'retrying'"
                      class="page-image-placeholder-full">
                      <div class="spinner-small"></div>
                      <div class="status-text-small">
                        {{ getImageForPage(page)?.status === 'retrying' ? '重试中...' : '生成中...' }}
                      </div>
                    </div>
                    <!-- 生成失败状态（有错误信息） -->
                    <div
                      v-else-if="getImageForPage(page)?.status === 'error' && getImageForPage(page)?.error"
                      class="page-image-placeholder-full error-placeholder-small">
                      <div class="error-icon-small">!</div>
                      <div class="status-text-small">生成失败</div>
                      <button class="generate-image-btn" @click.stop="generatePageImage(page.id)"
                        :disabled="!!page.id && generatingImages.has(page.id)">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                          stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                          <path d="M23 4v6h-6"></path>
                          <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
                        </svg>
                        <span>{{ page.id && generatingImages.has(page.id) ? '生成中...' : '重新生成' }}</span>
                      </button>
                    </div>
                    <!-- 还没有生成图片（没有图片数据） -->
                    <div v-else class="page-image-placeholder-full">
                      <div class="generate-image-prompt">
                        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                          stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="opacity: 0.3;">
                          <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                          <circle cx="8.5" cy="8.5" r="1.5"></circle>
                          <path d="M21 15l-5-5L5 21"></path>
                        </svg>
                        <div class="status-text-small" style="margin: 12px 0;">还未生成图片</div>
                        <button class="generate-image-btn" @click.stop="generatePageImage(page.id)"
                          :disabled="(page.id && generatingImages.has(page.id)) || !recordId">
                          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                            stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M23 4v6h-6"></path>
                            <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
                          </svg>
                          <span>{{ page.id && generatingImages.has(page.id) ? '生成中...' : '生成图片' }}</span>
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- 切换按钮 -->
            <button class="flip-toggle-btn" @click.stop="toggleFlip(page.id)"
              :title="page.id && flippedCards.has(page.id) ? '查看文字' : '查看图片'">
              <svg v-if="page.id && flippedCards.has(page.id)" width="16" height="16" viewBox="0 0 24 24" fill="none"
                stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                <path d="M14 2v6h6"></path>
                <path d="M16 13H8"></path>
                <path d="M16 17H8"></path>
                <path d="M10 9H8"></path>
              </svg>
              <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
                stroke-linecap="round" stroke-linejoin="round">
                <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                <circle cx="8.5" cy="8.5" r="1.5"></circle>
                <path d="M21 15l-5-5L5 21"></path>
              </svg>
            </button>
          </div>

          <!-- 添加按钮卡片 -->
          <div class="add-card-dashed" @click="addPage('content')">
            <div class="add-content">
              <div class="add-icon">+</div>
              <span>添加页面</span>
            </div>
          </div>
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

    <!-- 大图查看模态框 -->
    <div v-if="viewingLargeImage" class="large-image-modal" @click="closeLargeImage">
      <div class="large-image-container" @click.stop>
        <button class="close-large-image-btn" @click="closeLargeImage" title="关闭 (ESC)">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
            stroke-linecap="round" stroke-linejoin="round">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>

        <!-- 左箭头 -->
        <button v-if="hasPreviousImage" class="nav-arrow-btn nav-arrow-left" @click.stop="previousImage"
          title="上一张 (←)">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
            stroke-linecap="round" stroke-linejoin="round">
            <polyline points="15 18 9 12 15 6"></polyline>
          </svg>
        </button>

        <!-- 右箭头 -->
        <button v-if="hasNextImage" class="nav-arrow-btn nav-arrow-right" @click.stop="nextImage" title="下一张 (→)">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
            stroke-linecap="round" stroke-linejoin="round">
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
import { updateHistory, regenerateImage as apiRegenerateImage, getTone, generateTone, generateOutline, updateTone, getHistory, updateOutline, generateSingleImage, type Page } from '../api'

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
  index?: number
  url: string
  status: 'generating' | 'done' | 'error' | 'retrying'
  error?: string
  retryable?: boolean
}>>([])
const userImages = ref<File[]>([])

const dragOverIndex = ref<number | null>(null)
const draggedIndex = ref<number | null>(null)
const saveStatus = ref<'saved' | 'saving' | 'idle'>('idle')
const isLoadingData = ref(false)  // 标记是否正在加载数据，用于避免加载时触发自动保存

// 跟踪每个卡片的翻转状态（使用 page.id 作为 key，确保唯一性）
const flippedCards = ref<Set<number>>(new Set())

// 跟踪正在重新生成的图片（使用 page.id 作为 key）
const regeneratingImages = ref<Set<number>>(new Set())

// 跟踪正在生成的图片（首次生成，使用 page.id 作为 key）
const generatingImages = ref<Set<number>>(new Set())

// 批量生成相关状态
const error = ref('')
const shouldStopGeneration = ref(false)  // 前端停止标志
const isStopping = ref(false)  // 是否正在停止（等待所有正在处理的图片完成）
const tone = ref<string>('')
const originalTone = ref<string>('')  // 保存原始基调，用于比较是否有修改
const isRegeneratingOutline = ref(false)
const isRegeneratingTone = ref(false)  // 是否正在重新生成基调
const showConfirmDialog = ref(false)  // 确认对话框
const metadataCollapsed = ref(false)  // 小红书元数据是否收起

// 本地编辑的主题
const localTopic = ref<string>('')

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

// 主题变化时的处理
function onTopicChange() {
  // 触发自动保存
  debouncedSaveTopic()
}

// 页面内容输入事件（仅同步 raw 文本，content 通过 v-model 已自动更新）
function onPageContentInput(_page: Page) {
  // 同步更新 raw 文本
  syncRawFromPages()
}

// 根据 pages 重新生成 raw 文本
function syncRawFromPages() {
  outline.value.raw = outline.value.pages
    .map(page => page.content)
    .join('\n\n<page>\n\n')
}

// 更新图片状态
function updateImageStatus(pageId: number, status: 'generating' | 'done' | 'error' | 'retrying', url?: string, error?: string) {
  console.log(`🔄 更新图片状态: pageId=${pageId}, status=${status}, url=${url}`)
  const image = images.value.find(img => img.page_id === pageId)
  const page = outline.value.pages.find(p => p.id === pageId)
  
  console.log(`📋 查找图片:`, image ? '找到' : '未找到', `页面:`, page ? `找到 (index=${page.index})` : '未找到')
  
  if (image) {
    image.status = status
    if (url) {
      // 添加时间戳以强制刷新图片，避免浏览器缓存
      const separator = url.includes('?') ? '&' : '?'
      image.url = `${url}${separator}_t=${Date.now()}`
      console.log(`✅ 图片URL已更新:`, image.url)
    }
    if (error) image.error = error
    
    // 当状态变为 generating、retrying 或 done 时，自动翻转卡片到图片面（使用 page.id）
    if ((status === 'generating' || status === 'retrying' || status === 'done') && page && page.id) {
      flippedCards.value.add(page.id)
      console.log(`🔄 卡片已翻转到图片面: page_id=${page.id}`)
    }
  } else {
    // 如果图片不存在，尝试从页面中获取 index 并创建
    if (page) {
      let finalUrl = url || ''
      if (url) {
        // 添加时间戳以强制刷新图片，避免浏览器缓存
        const separator = url.includes('?') ? '&' : '?'
        finalUrl = `${url}${separator}_t=${Date.now()}`
      }
      const newImage = {
        page_id: pageId,
        index: page.index,
        url: finalUrl,
        status
      }
      images.value.push(newImage)
      console.log(`✅ 创建新图片记录:`, newImage)
      
      // 当状态为 generating、retrying 或 done 时，自动翻转卡片到图片面（使用 page.id）
      if ((status === 'generating' || status === 'retrying' || status === 'done') && page.id) {
        flippedCards.value.add(page.id)
        console.log(`🔄 卡片已翻转到图片面: page_id=${page.id}`)
      }
    } else {
      console.error(`❌ 无法更新图片状态: 找不到pageId=${pageId}对应的页面`)
    }
  }
  
  // 如果正在停止中，检查是否所有正在处理的图片都已完成
  if (isStopping.value) {
    checkAndUpdateStoppingStatus()
  }
}

// 元数据变化时的处理
function onMetadataChange() {
  // 确保 metadata 对象存在
  if (!outline.value.metadata) {
    outline.value.metadata = {
      title: '',
      content: '',
      tags: ''
    }
  }
  // 更新到本地状态
  outline.value.metadata.title = localMetadata.value.title
  outline.value.metadata.content = localMetadata.value.content
  outline.value.metadata.tags = localMetadata.value.tags
  // 触发自动保存
  debouncedSave()
}

// 参考图模式：'custom' | 'cover' | 'previous'
const referenceMode = ref<'custom' | 'cover' | 'previous'>('cover')

// 计算属性：是否正在批量生成
const isGenerating = computed(() => {
  return images.value.some(img => img.status === 'generating' || img.status === 'retrying')
})

// 大图查看相关
const viewingLargeImage = ref(false)
const largeImageUrl = ref<string>('')
const currentImageIndex = ref<number>(0)

// 获取所有已生成图片的 page_id 列表（按 pages 顺序排序）
const generatedImagePageIds = computed(() => {
  // 按照 outline.pages 的顺序返回已生成图片的 page_id
  return outline.value.pages
    .filter(page => {
      if (!page.id) return false
      const img = images.value.find(i => i.page_id === page.id)
      return img && img.status === 'done' && img.url
    })
    .map(page => page.id!)
})

// 总图片数
const totalImages = computed(() => generatedImagePageIds.value.length)

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
  return images.value.some(img => img.status === 'done' && img.url)
})

// 检查是否还有未生成的图片
const hasUnfinishedImages = computed(() => {
  // 检查是否有页面没有对应的图片，或者图片状态不是 'done'
  return outline.value.pages.some(page => {
    if (!page.id) return false
    const image = images.value.find(img => img.page_id === page.id)
    return !image || image.status !== 'done'
  })
})

// 检查基调是否有修改
const toneHasChanged = computed(() => {
  return tone.value.trim() !== originalTone.value.trim()
})

// 获取对应页面的图片（基于 page_id）
function getImageForPage(page: Page) {
  if (!page.id) {
    console.warn(`⚠️ getImageForPage: 页面缺少ID, page_index=${page.index}`)
    return undefined
  }
  const image = images.value.find(img => img.page_id === page.id)
  if (!image) {
    console.warn(`⚠️ getImageForPage: 找不到图片, page_id=${page.id}, page_index=${page.index}`)
    console.log(`📋 当前所有图片:`, images.value.map(img => ({ page_id: img.page_id, index: img.index, status: img.status })))
  }
  return image
}

// 检查页面是否有已生成的图片
function hasImage(page: Page): boolean {
  const image = getImageForPage(page)
  return image?.status === 'done' && !!image?.url
}

// 切换卡片翻转状态（使用 page.id）
function toggleFlip(pageId: number | undefined) {
  if (!pageId) return
  if (flippedCards.value.has(pageId)) {
    flippedCards.value.delete(pageId)
  } else {
    flippedCards.value.add(pageId)
  }
}

// 初始化翻转状态：有图片的默认显示图片面（使用 page.id）
function updateFlipStates() {
  outline.value.pages.forEach(page => {
    if (!page.id) return
    if (hasImage(page)) {
      flippedCards.value.add(page.id)
    } else if (!flippedCards.value.has(page.id)) {
      // 如果没有图片且用户没有手动翻转过，则显示文字面
      flippedCards.value.delete(page.id)
    }
    // 如果用户已经手动翻转过，保持当前状态
  })
}

// 监听图片变化，自动更新翻转状态（仅在图片状态变化时，不影响用户手动翻转）
// 使用 page_id 而非 index 来确保唯一性
watch(
  () => images.value.map(img => ({ page_id: img.page_id, status: img.status, url: img.url })),
  (newImages, oldImages) => {
    // 只在图片真正生成完成时才更新翻转状态
    if (oldImages) {
      newImages.forEach((newImg, idx) => {
        const oldImg = oldImages[idx]
        // 如果图片刚刚生成完成（从非 done 变为 done）
        if (oldImg && oldImg.status !== 'done' && newImg.status === 'done' && newImg.url && newImg.page_id) {
          flippedCards.value.add(newImg.page_id)
        }
      })
    }
  },
  { deep: true }
)

// 防抖保存函数
let saveTimer: ReturnType<typeof setTimeout> | null = null

async function saveToHistory() {
  if (!recordId.value) return

  saveStatus.value = 'saving'
  try {
    await updateHistory(recordId.value, {
      outline: {
        raw: outline.value.raw,
        pages: outline.value.pages,
        metadata: outline.value.metadata
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

// 主题保存函数
let topicSaveTimer: ReturnType<typeof setTimeout> | null = null

async function saveTopicToHistory() {
  if (!recordId.value) return

  try {
    await updateHistory(recordId.value, {
      topic: localTopic.value
    })
    topic.value = localTopic.value
    console.log('✅ 主题已保存')
  } catch (e) {
    console.error('保存主题失败:', e)
  }
}

function debouncedSaveTopic() {
  if (topicSaveTimer) {
    clearTimeout(topicSaveTimer)
  }
  topicSaveTimer = setTimeout(() => {
    saveTopicToHistory()
  }, 1000) // 1秒防抖
}

// 监听大纲变化，自动保存到后端
watch(
  () => outline.value,
  () => {
    // 如果正在加载数据，不触发自动保存（避免刷新页面时重复更新）
    if (isLoadingData.value) {
      return
    }
    debouncedSave()
  },
  { deep: true }
)

// 监听 topic 变化，同步到本地编辑
watch(
  () => topic.value,
  (newTopic) => {
    if (newTopic !== localTopic.value) {
      localTopic.value = newTopic || ''
    }
  },
  { immediate: true }
)

// 监听 metadata 变化，同步到本地编辑
watch(
  () => outline.value.metadata,
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
  () => recordId.value,
  (newRecordId) => {
    if (newRecordId) {
      syncURLParams()
    }
  }
)

/**
 * 从后端加载任务数据
 */
async function loadDataFromBackend(recordIdParam: string) {
  console.log(`🔄 从后端加载任务数据: recordId=${recordIdParam}`)

  // 标记开始加载数据，避免触发自动保存
  isLoadingData.value = true

  try {
    const res = await getHistory(recordIdParam)
    if (!res.success || !res.record) {
      console.error('❌ 加载历史记录失败')
      router.push('/')
      return
    }

    const record = res.record

    // 设置基本信息
    recordId.value = record.id
    topic.value = record.topic || record.title || ''

    // 直接从历史记录中加载大纲和图片数据
    console.log('📋 历史记录大纲数据:', record.outline)
    if (record.outline) {
      console.log('📱 元数据:', record.outline.metadata)
      outline.value = {
        raw: record.outline.raw || '',
        pages: record.outline.pages || [],
        metadata: record.outline.metadata
      }
    } else {
      // 如果没有大纲数据，设置空大纲
      outline.value = {
        raw: '',
        pages: [],
        metadata: undefined
      }
    }

    // 从 pages 中加载图片信息
    if (record.outline && record.outline.pages) {
      images.value = record.outline.pages.map((page) => {
        const imageUrl = page.image?.filename
          ? `/api/images/${record.id}/${page.image.filename}`
          : ''
        const status: 'done' | 'error' = page.image ? 'done' : 'error'
        return {
          page_id: page.id!,
          index: page.index,
          url: imageUrl,
          status,
          retryable: true
        }
      })
    } else {
      images.value = []
    }

    const imageCount = images.value.filter(img => img.status === 'done').length
    const pageCount = record.outline?.pages?.length || 0
    console.log('✅ 从历史记录加载数据:', pageCount, '页,', imageCount, '张图片')

    // 读取基调
    if (recordId.value) {
      try {
        const toneResult = await getTone(recordId.value)
        if (toneResult.success && toneResult.tone) {
          tone.value = toneResult.tone
          originalTone.value = toneResult.tone
          console.log('✅ 已加载基调')
        }
      } catch (e) {
        console.warn('⚠️ 读取基调失败:', e)
      }
    }


    console.log('✅ 数据加载完成')
  } catch (err) {
    console.error('❌ 加载数据失败:', err)
    console.error('错误详情:', err)
    // 不要立即跳转，先显示错误信息
    error.value = '加载数据失败: ' + (err instanceof Error ? err.message : String(err))
    // 如果确实无法加载，再跳转
    setTimeout(() => {
      if (!recordId.value || outline.value.pages.length === 0) {
        router.push('/')
      }
    }, 2000)
  } finally {
    // 标记加载完成，恢复自动保存功能
    isLoadingData.value = false
  }
}

/**
 * 同步 URL 参数
 */
function syncURLParams() {
  if (recordId.value && route.query.recordId !== recordId.value) {
    router.replace({ query: { recordId: recordId.value } })
    console.log('✅ 已同步 URL 参数:', recordId.value)
  }
}

// 组件挂载时初始化
onMounted(async () => {
  const recordId = route.query.recordId as string

  if (recordId) {
    // 从 URL 参数获取 recordId，加载数据
    console.log('📍 从 URL 加载任务:', recordId)

    // 从后端加载最新数据
    await loadDataFromBackend(recordId)

    // 更新翻转状态
    updateFlipStates()
  } else {
    // 既没有 URL 参数，也没有数据，跳转到首页
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
  if (topicSaveTimer) {
    clearTimeout(topicSaveTimer)
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

const onDragOver = (_e: DragEvent, index: number) => {
  if (draggedIndex.value === index) return
  dragOverIndex.value = index
}

const onDrop = async (_e: DragEvent, index: number) => {
  dragOverIndex.value = null
  if (draggedIndex.value !== null && draggedIndex.value !== index) {
    const fromIndex = draggedIndex.value

    // 标记开始加载数据，避免触发自动保存
    isLoadingData.value = true

    try {
      // 前端先移动
      const pages = [...outline.value.pages]
      const [movedPage] = pages.splice(fromIndex, 1)
      pages.splice(index, 0, movedPage)

      // 重新索引
      pages.forEach((page, idx) => {
        page.index = idx
        // 同步更新 images 中的 index（用于排序显示）
        const image = images.value.find(img => img.page_id === page.id)
        if (image) {
          image.index = idx
        }
      })

      outline.value.pages = pages
      syncRawFromPages()

      // 如果有 recordId，调用后端 API 更新大纲和图片文件
      if (recordId.value) {
        try {
          const result = await updateOutline(recordId.value, outline.value.pages)
          if (!result.success) {
            console.error('更新大纲失败:', result.error)
            alert('移动失败：' + result.error)
            // 如果更新失败，重新加载数据恢复状态
            await loadDataFromBackend(recordId.value)
            return
          } else {
            console.log('大纲更新成功')

            // 从后端重新加载数据，确保图片 URL 与页面索引正确对应
            await loadDataFromBackend(recordId.value)
            console.log('图片数据已重新加载')
          }
        } catch (error) {
          console.error('调用 API 失败:', error)
          alert('移动失败，请稍后重试')
          // 重新加载数据恢复状态
          if (recordId.value) {
            await loadDataFromBackend(recordId.value)
          }
        }
      }
    } finally {
      // 恢复自动保存功能
      isLoadingData.value = false
    }
  }
  draggedIndex.value = null
}

const deletePageByPage = async (pageToDelete: Page) => {
  if (confirm('确定要删除这一页吗？')) {
    // 只使用页面ID来唯一标识要删除的页面
    const pageId = pageToDelete.id
    
    if (!pageId) {
      console.error('页面缺少ID，无法删除')
      alert('页面信息不完整，无法删除。请刷新页面后重试。')
      return
    }
    
    // 从 images 数组中删除对应的图片（基于 page_id）
    images.value = images.value.filter(img => img.page_id !== pageId)
    
    // 从数组中删除页面：只使用ID匹配
    outline.value.pages = outline.value.pages.filter(p => p.id !== pageId)
    
    // 重新索引
    outline.value.pages.forEach((page, idx) => {
      page.index = idx
      // 同步更新 images 中的 index（用于排序显示）
      const image = images.value.find(img => img.page_id === page.id)
      if (image) {
        image.index = idx
      }
    })
    // 同步更新 raw 文本
    syncRawFromPages()

    // 如果有 recordId，调用后端 API 更新大纲和图片文件
    if (recordId.value) {
      try {
        const result = await updateOutline(recordId.value, outline.value.pages)
        if (!result.success) {
          console.error('更新大纲失败:', result.error)
          alert('删除失败：' + result.error)
          // 如果更新失败，重新加载数据恢复状态
          await loadDataFromBackend(recordId.value)
          return
        } else {
          console.log('大纲更新成功')

          // 从后端重新加载数据，确保图片 URL 与页面索引正确对应
          await loadDataFromBackend(recordId.value)
          console.log('图片数据已重新加载')
        }
      } catch (error) {
        console.error('调用 API 失败:', error)
        alert('删除失败，请稍后重试')
        // 重新加载数据恢复状态
        if (recordId.value) {
          await loadDataFromBackend(recordId.value)
        }
      }
    }
  }
}


const addPage = async (type: 'cover' | 'content' | 'summary') => {
  const newPage: Page = {
    index: outline.value.pages.length,
    type,
    content: ''
  }
  outline.value.pages.push(newPage)
  // 同步更新 raw 文本
  syncRawFromPages()
  
  // 如果有 recordId，立即保存到后端并重新加载数据以获取页面ID
  if (recordId.value) {
    try {
      // 标记开始加载数据，避免触发自动保存
      isLoadingData.value = true
      
      // 立即保存到后端（不使用防抖）
      const result = await updateOutline(recordId.value, outline.value.pages)
      if (result.success) {
        console.log('✅ 新页面已保存，重新加载数据以获取页面ID')
        // 重新加载数据以获取新页面的ID
        await loadDataFromBackend(recordId.value)
      } else {
        console.error('保存新页面失败:', result.error)
        alert('保存新页面失败：' + result.error)
        // 如果保存失败，移除刚添加的页面并重新索引
        outline.value.pages = outline.value.pages.filter(p => p !== newPage)
        outline.value.pages.forEach((page, idx) => {
          page.index = idx
        })
        syncRawFromPages()
      }
    } catch (error) {
      console.error('保存新页面失败:', error)
      alert('保存新页面失败，请稍后重试')
      // 如果保存失败，移除刚添加的页面并重新索引
      outline.value.pages = outline.value.pages.filter(p => p !== newPage)
      outline.value.pages.forEach((page, idx) => {
        page.index = idx
      })
      syncRawFromPages()
    } finally {
      isLoadingData.value = false
    }
  }
  
  // 滚动到底部
  nextTick(() => {
    window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' })
  })
}

/**
 * 根据修改后的主题重新生成基调
 */
async function regenerateTone() {
  if (!localTopic.value.trim()) {
    error.value = '主题内容不能为空'
    return
  }

  if (!recordId.value) {
    error.value = '记录ID不存在，无法重新生成基调'
    return
  }

  isRegeneratingTone.value = true
  error.value = ''

  try {
    // 第一步：保存修改后的主题
    if (recordId.value) {
      try {
        await updateHistory(recordId.value, {
          topic: localTopic.value
        })
        topic.value = localTopic.value
        console.log('✅ 主题已更新')
      } catch (e) {
        console.warn('⚠️ 保存主题失败:', e)
        // 继续执行，不阻断流程
      }
    }

    // 第二步：使用修改后的主题重新生成基调（传入现有的 recordId 以更新而不是创建新记录）
    const toneResult = await generateTone(localTopic.value.trim(), recordId.value)

    if (toneResult.success && toneResult.tone) {
      // 更新基调内容
      tone.value = toneResult.tone
      // 不更新 originalTone，这样 toneHasChanged 会是 true，允许生成大纲
      // originalTone.value = toneResult.tone

      // 保存基调到后端
      if (recordId.value) {
        try {
          await updateTone(recordId.value, tone.value)
          console.log('✅ 基调已更新')
        } catch (e) {
          console.warn('⚠️ 保存基调失败:', e)
        }
      }

      console.log('✅ 基调已重新生成')
    } else {
      error.value = toneResult.error || '生成基调失败'
    }
  } catch (err: any) {
    error.value = err.message || '网络错误，请重试'
  } finally {
    isRegeneratingTone.value = false
  }
}

/**
 * 根据修改后的基调重新生成大纲
 */
async function regenerateOutline() {
  if (!tone.value.trim()) {
    error.value = '基调内容不能为空'
    return
  }

  if (!recordId.value) {
    error.value = '记录ID不存在，无法重新生成大纲'
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
  if (!recordId.value) {
    return
  }

  isRegeneratingOutline.value = true
  error.value = ''
  showConfirmDialog.value = false

  // 🔥 立即清空大纲和图片状态，避免在生成期间被修改
  outline.value = {
    raw: '',
    pages: [],
    metadata: undefined
  }
  images.value = []
  flippedCards.value.clear()

  try {
    // 第一步：保存修改后的基调
    if (recordId.value) {
      try {
        await updateTone(recordId.value, tone.value)
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
      topic.value || '',
      userImages.value.length > 0 ? userImages.value : undefined,
      tone.value,
      recordId.value  // 使用相同的 record_id
    )

    if (outlineResult.success && outlineResult.pages) {
      // 更新大纲内容
      outline.value = {
        raw: outlineResult.outline || '',
        pages: outlineResult.pages,
        metadata: outlineResult.metadata
      }

      // 重置图片状态
      images.value = outlineResult.pages.map((page) => ({
        page_id: page.id!,
        index: page.index,
        url: '',
        status: 'error' as const,
        retryable: true
      }))


      // 更新历史记录
      if (recordId.value) {
        try {
          await updateHistory(recordId.value, {
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

// 开始批量生成（重构为依次调用单张接口）
async function startBatchGeneration() {
  if (outline.value.pages.length === 0) {
    error.value = '没有可生成的页面'
    return
  }

  // 确保有 recordId（应该在大纲生成时已创建）
  if (!recordId.value) {
    error.value = '记录ID未找到，请重新生成大纲'
    return
  }

  // 初始化图片数组（但不设置状态为生成中，只在真正开始生成时设置）
  outline.value.pages.forEach(page => {
    if (page.id) {
      const existingImage = images.value.find(img => img.page_id === page.id)
      if (!existingImage) {
        images.value.push({
          page_id: page.id,
          index: page.index,
          url: '',
          status: 'error' as const  // 初始状态为error，表示还未生成
        })
      }
    }
  })

  // 重置停止标志和停止状态（只在开始新的批量生成时重置）
  shouldStopGeneration.value = false
  isStopping.value = false

  // 依次生成每张图片（只生成未完成的图片）
  for (const page of outline.value.pages) {
    // 在循环开始时检查停止标志（每次循环都检查）
    if (shouldStopGeneration.value) {
      console.log('🛑 检测到停止标志，停止生成后续图片（循环开始）')
      break
    }
    
    console.log(`🔄 准备生成图片: page_id=${page.id}, page_index=${page.index}, shouldStop=${shouldStopGeneration.value}`)

    if (!page.id) {
      console.error('页面缺少ID:', page)
      continue
    }

    // 检查该页面是否已经生成完成，如果已完成则跳过
    const existingImage = images.value.find(img => img.page_id === page.id)
    if (existingImage && existingImage.status === 'done' && existingImage.url) {
      console.log(`页面 ${page.index} 已生成完成，跳过`)
      // 跳过已完成的页面后，也要检查停止标志
      if (shouldStopGeneration.value) {
        console.log('🛑 检测到停止标志，停止生成（跳过已完成页面后）')
        break
      }
      continue
    }

    // 在开始生成前再次检查停止标志（可能在循环检查后、开始生成前被设置）
    if (shouldStopGeneration.value) {
      console.log('🛑 检测到停止标志，停止生成（在开始生成前）')
      break
    }

    // 在开始生成前才设置状态为生成中
    updateImageStatus(page.id, 'generating')

    try {
      // 调用单张图片生成接口
      const result = await generateSingleImage(
        recordId.value,
        page.id,
        outline.value.raw,
        topic.value,
        userImages.value.length > 0 ? userImages.value : undefined,
        referenceMode.value
      )

      // 无论是否停止，都要正常处理响应并更新图片状态
      if (result.success && result.image_url) {
        // 更新图片状态为完成
        console.log(`✅ 图片生成成功: page_id=${page.id}, page_index=${page.index}, image_url=${result.image_url}`)
        updateImageStatus(page.id, 'done', result.image_url)
        // 使用 nextTick 确保 Vue 能够检测到变化
        await nextTick()
        const updatedImage = images.value.find(img => img.page_id === page.id)
        console.log(`📸 图片状态已更新，当前图片数据:`, updatedImage)
        console.log(`📋 所有图片数据:`, images.value)
      } else {
        // 更新图片状态为错误
        console.error(`❌ 图片生成失败: page_id=${page.id}, error=${result.error || '生成失败'}`)
        updateImageStatus(page.id, 'error', undefined, result.error || '生成失败')
      }

      // 在更新图片状态后，检查停止标志（如果已停止，不再继续生成后续图片）
      if (shouldStopGeneration.value) {
        console.log('🛑 检测到停止标志，停止生成后续图片（在图片状态更新后）')
        break
      }
    } catch (e) {
      console.error('生成图片失败:', e)
      updateImageStatus(page.id, 'error', undefined, String(e))
      // 在异常处理中也检查停止标志
      if (shouldStopGeneration.value) {
        console.log('🛑 检测到停止标志，停止生成后续图片（在异常处理中）')
        break
      }
    }
  }

  // 更新历史记录
  if (recordId.value) {
    try {
      // 收集所有生成的图片文件名
      const generatedImages: string[] = []
      for (const img of images.value) {
        if (img.status === 'done' && img.url) {
          // 从URL中提取文件名
          const urlParts = img.url.split('/')
          const filename = urlParts[urlParts.length - 1].split('?')[0]
          if (filename) {
            generatedImages.push(filename)
          }
        }
      }

      // 确定状态：所有图片都生成完成才算已完成，其他都是草稿
      const expectedCount = outline.value.pages.length
      const actualCount = generatedImages.length
      const status = (actualCount >= expectedCount) ? 'completed' : 'draft'

      // 获取封面图作为缩略图（只保存文件名，不是完整URL）
      const thumbnail = generatedImages.length > 0 ? generatedImages[0] : undefined

      await updateHistory(recordId.value, {
        images: {
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
}


const startGeneration = () => {
  // 改为调用批量生成，而不是跳转页面
  startBatchGeneration()
}

// 检查并更新停止状态（当所有正在处理的图片都完成时，取消停止状态）
function checkAndUpdateStoppingStatus() {
  const hasGeneratingImages = images.value.some(img => img.status === 'generating' || img.status === 'retrying')
  
  if (!hasGeneratingImages && isStopping.value) {
    // 所有正在处理的图片都已完成，取消停止状态（但保持停止标志，防止继续生成）
    isStopping.value = false
    // 注意：不重置 shouldStopGeneration.value，让它保持为 true，这样即使所有图片完成，也不会继续生成
    console.log('✅ 所有正在处理的图片已完成，停止状态已取消（停止标志保持）')
  } else if (hasGeneratingImages && isStopping.value) {
    // 还有正在处理的图片，继续等待
    // 使用 nextTick 和 setTimeout 定期检查
    nextTick(() => {
      setTimeout(() => {
        checkAndUpdateStoppingStatus()
      }, 500) // 每500ms检查一次
    })
  }
}

// 停止生成
function stopGeneration() {
  if (isStopping.value) {
    // 如果已经在停止中，不重复执行
    console.log('⚠️ 已经在停止中，忽略重复的停止请求')
    return
  }
  
  shouldStopGeneration.value = true
  isStopping.value = true
  console.log('🛑 用户请求停止生成，停止标志已设置，等待所有正在处理的图片完成')
  console.log(`📊 当前停止状态: shouldStopGeneration=${shouldStopGeneration.value}, isStopping=${isStopping.value}`)
  
  // 检查是否还有正在生成的图片
  checkAndUpdateStoppingStatus()
}

// 查看大图（基于 pageId，用于 UI 操作）
function viewLargeImage(pageId: number | undefined) {
  if (!pageId) return
  const page = outline.value.pages.find(p => p.id === pageId)
  if (!page) return
  
  const image = getImageForPage(page)
  if (image?.url && recordId.value) {
    // 找到当前图片在已生成图片列表中的索引（generatedImagePageIds 存储的是 page.id）
    const index = generatedImagePageIds.value.indexOf(pageId)
    if (index !== -1) {
      currentImageIndex.value = index
      loadImageByIndex(index)
      viewingLargeImage.value = true
      // 添加键盘事件监听
      document.addEventListener('keydown', handleKeyDown)
    }
  }
}

// 根据索引加载图片（使用 page_id）
function loadImageByIndex(index: number) {
  const pageId = generatedImagePageIds.value[index]
  if (pageId !== undefined && recordId.value) {
    const page = outline.value.pages.find(p => p.id === pageId)
    if (page) {
      const image = getImageForPage(page)
      if (image?.url) {
        // 从 URL 中提取文件名，或者直接使用 URL（去掉可能的 thumbnail 参数）
        // URL 格式: /api/images/{record_id}/{filename}?thumbnail=true
        const urlWithoutParams = image.url.split('?')[0]
        // 确保使用 thumbnail=false 参数
        largeImageUrl.value = `${urlWithoutParams}?thumbnail=false`
        currentImageIndex.value = index
      }
    }
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

// 下载单张图片（基于 pageId，用于 UI 操作）
function downloadOne(pageId: number | undefined, displayIndex?: number) {
  if (!pageId) return
  const page = outline.value.pages.find(p => p.id === pageId)
  if (!page) return
  
  const image = getImageForPage(page)
  if (image?.url && recordId.value) {
    // 如果没有传入 displayIndex，则计算当前显示序号
    let finalDisplayIndex = displayIndex
    if (finalDisplayIndex === undefined) {
      finalDisplayIndex = outline.value.pages.findIndex(p => p.id === pageId) + 1
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
  if (recordId.value) {
    // 如果有 recordId，使用后端打包下载接口
    const link = document.createElement('a')
    link.href = `/api/history/${recordId.value}/download`
    link.click()
  } else {
    // 否则按照当前页面顺序逐个下载
    let downloadCount = 0
    outline.value.pages.forEach((page, displayIndex) => {
      const image = getImageForPage(page)
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

// 生成图片（首次生成或重新生成，基于 pageId）
async function generatePageImage(pageId: number | undefined) {
  if (!pageId) {
    alert('页面ID无效，无法生成图片')
    return
  }

  if (!recordId.value) {
    alert('记录ID未找到，无法生成图片')
    return
  }

  const page = outline.value.pages.find(p => p.id === pageId)
  if (!page) {
    alert('页面信息未找到')
    return
  }

  // 如果正在生成，忽略（使用 pageId 检查）
  if (generatingImages.value.has(pageId) || regeneratingImages.value.has(pageId)) {
    return
  }

  const image = getImageForPage(page)
  const isRegenerating = image?.status === 'error' && image?.error

  // 如果是重新生成（有错误状态），使用重新生成API
  if (isRegenerating) {
    await regeneratePageImage(pageId)
    return
  }

  // 首次生成，使用生成图片API（使用 pageId）
  generatingImages.value.add(pageId)

  // 初始化图片状态为生成中（在调用接口前设置）
  if (!image) {
    images.value.push({
      page_id: pageId,
      index: page.index,
      url: '',
      status: 'generating'
    })
  } else {
    updateImageStatus(pageId, 'generating')
  }

  try {
    // 确保状态为生成中（在等待接口响应期间显示）
    updateImageStatus(pageId, 'generating')

    const result = await generateSingleImage(
      recordId.value!,
      pageId,
      outline.value.raw || '',
      topic.value,
      userImages.value.length > 0 ? userImages.value : undefined,
      referenceMode.value
    )

    if (result.success && result.image_url) {
      updateImageStatus(pageId, 'done', result.image_url)
      generatingImages.value.delete(pageId)
    } else {
      updateImageStatus(pageId, 'error', undefined, result.error || '生成失败')
      generatingImages.value.delete(pageId)
    }
  } catch (e) {
    console.error('生成图片失败:', e)
    updateImageStatus(pageId, 'error', undefined, String(e))
    generatingImages.value.delete(pageId)
  }
}

// 重新生成图片（基于 pageId，用于 UI 操作）
async function regeneratePageImage(pageId: number | undefined) {
  if (!pageId) {
    alert('页面ID无效，无法重新生成')
    return
  }

  if (!recordId.value) {
    alert('记录ID未找到，无法重新生成')
    return
  }

  const page = outline.value.pages.find(p => p.id === pageId)
  if (!page) {
    alert('页面信息未找到')
    return
  }

  // 如果正在重新生成，忽略（使用 pageId 检查）
  if (regeneratingImages.value.has(pageId)) {
    return
  }

  // 设置为重新生成状态（使用 pageId）
  regeneratingImages.value.add(pageId)
  updateImageStatus(pageId, 'retrying')

  try {
    // 构建上下文信息
    const context = {
      fullOutline: outline.value.raw || '',
      userTopic: topic.value || ''
    }

    // 调用重新生成 API
    const result = await apiRegenerateImage(
      recordId.value!,
      page,
      true, // useReference
      context,
      referenceMode.value // referenceMode
    )

    if (result.success && result.image_url) {
      // 更新图片（使用 page_id）
      updateImageStatus(pageId, 'done', result.image_url)
    } else {
      // 更新为错误状态（使用 page_id）
      updateImageStatus(pageId, 'error', undefined, result.error)
    }
  } catch (e) {
    console.error('重新生成图片失败:', e)
    updateImageStatus(pageId, 'error', undefined, String(e))
  } finally {
    regeneratingImages.value.delete(pageId)
  }
}
</script>

<style scoped>
/* 主容器 - 使用flex布局 */
.outline-page {
  width: 100%;
  min-height: 100vh;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.outline-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-width: 1400px;
  margin: 0 auto;
  width: 100%;
}

.outline-main {
  display: flex;
  flex-direction: column;
  gap: 16px;
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
  display: flex;
  flex-direction: column;
  gap: 16px;
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

.btn-danger {
  background: #ff4d4f;
  color: white;
}

.btn-danger:hover:not(:disabled) {
  background: #ff7875;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(255, 77, 79, 0.3);
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.btn-icon {
  background: none;
  border: none;
  cursor: pointer;
  padding: 4px;
  display: flex;
  align-items: center;
  color: #999;
  transition: color 0.2s;
  flex-shrink: 0;
}

.btn-icon:hover {
  color: var(--primary);
}

/* 主题区域 */
.topic-section .card-body {
  padding: 16px;
}

.topic-input {
  width: 100%;
  padding: 12px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  font-size: 15px;
  font-weight: 500;
  font-family: inherit;
  line-height: 1.5;
  color: var(--text-main);
  background: linear-gradient(135deg, #fff5f5 0%, #ffffff 100%);
  transition: all 0.2s;
}

.topic-input:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 0 3px rgba(255, 36, 66, 0.1);
  background: white;
}

.topic-input::placeholder {
  color: #ccc;
  font-weight: 400;
}

/* 基调区域 */
.tone-section .card-body {
  padding: 16px;
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

/* 小红书元数据区域 */
.metadata-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.metadata-label {
  font-size: 12px;
  font-weight: 600;
  color: #666;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.metadata-label::before {
  content: '';
  width: 2px;
  height: 12px;
  background: var(--primary);
  border-radius: 1px;
  margin-right: 4px;
}

.char-count {
  font-size: 11px;
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
  padding: 10px 12px;
  border: 1px solid #e8e8e8;
  border-radius: var(--radius-sm);
  font-size: 14px;
  font-weight: 500;
  line-height: 1.5;
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
  font-size: 15px;
  font-weight: 600;
  background: linear-gradient(135deg, #fff5f5 0%, #ffffff 100%);
}

.metadata-textarea {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #e8e8e8;
  border-radius: var(--radius-sm);
  font-size: 13px;
  line-height: 1.7;
  color: var(--text-main);
  transition: all 0.2s;
  resize: vertical;
  font-family: inherit;
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
  min-height: 120px;
}

.tags-textarea {
  background: #f9f9f9;
}

.tags-preview {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
  padding: 10px;
  background: white;
  border: 1px solid #e8e8e8;
  border-radius: var(--radius-sm);
  min-height: 40px;
}

.tag-item {
  display: inline-block;
  padding: 4px 10px;
  background: linear-gradient(135deg, #fff0f0 0%, #fff5f5 100%);
  border: 1px solid #ffd4d4;
  border-radius: 12px;
  font-size: 12px;
  color: var(--primary);
  font-weight: 500;
  transition: all 0.2s;
}

.tag-item:hover {
  background: var(--primary);
  border-color: var(--primary);
  color: white;
  transform: translateY(-1px);
  box-shadow: 0 2px 6px rgba(255, 36, 66, 0.3);
}

/* 页面头部卡片 */
.page-header-card {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  padding: 16px;
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

.save-status {
  margin-left: 8px;
  font-size: 11px;
  padding: 2px 6px;
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

.action-buttons {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  flex-shrink: 0;
}

/* 参考图模式选择器 */
.reference-mode-selector {
  padding: 12px 16px;
  background: #f9f9f9;
  border-top: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.reference-mode-label {
  font-size: 12px;
  font-weight: 600;
  color: #666;
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
  font-size: 12px;
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
  font-size: 10px;
  color: #999;
  font-style: italic;
}


/* 网格布局 - 使用flex */
.outline-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  width: 100%;
}

/* 翻转卡片容器 */
.flip-card-wrapper {
  perspective: 1000px;
  position: relative;
  flex: 0 0 calc(25% - 12px);
  min-width: 240px;
  aspect-ratio: 3/4;
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
  padding: 12px;
  transition: all 0.2s ease;
  border: none;
  border-radius: var(--radius-sm);
  background: white;
  box-shadow: var(--shadow-sm);
  position: relative;
  width: 100%;
  height: 100%;
}

.outline-card:hover {
  box-shadow: var(--shadow-md);
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

/* 卡片顶部栏 */
.card-top-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  padding-bottom: 8px;
  border-bottom: 1px solid #f5f5f5;
}

.page-info {
  display: flex;
  align-items: center;
  gap: 6px;
}

.page-number {
  font-size: 12px;
  font-weight: 700;
  color: #ccc;
  font-family: 'Inter', sans-serif;
}

.page-type {
  font-size: 10px;
  padding: 2px 5px;
  border-radius: 3px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.page-type.cover {
  color: #FF4D4F;
  background: #FFF1F0;
}

.page-type.content {
  color: #8c8c8c;
  background: #f5f5f5;
}

.page-type.summary {
  color: #52C41A;
  background: #F6FFED;
}

.card-controls {
  display: flex;
  gap: 6px;
  opacity: 0.4;
  transition: opacity 0.2s;
}

.outline-card:hover .card-controls {
  opacity: 1;
}

.drag-handle {
  cursor: grab;
  padding: 2px;
}

.drag-handle:active {
  cursor: grabbing;
}

.icon-btn {
  background: none;
  border: none;
  cursor: pointer;
  color: #999;
  padding: 2px;
  transition: color 0.2s;
}

.icon-btn:hover {
  color: #FF4D4F;
}

/* 文本区域 */
.textarea-paper {
  flex: 1;
  width: 100%;
  border: none;
  background: transparent;
  padding: 0;
  font-size: 14px;
  line-height: 1.6;
  color: #333;
  resize: none;
  font-family: inherit;
  margin-bottom: 8px;
  min-height: 0;
  overflow-y: auto;
}

.textarea-paper:focus {
  outline: none;
}

.word-count {
  text-align: right;
  font-size: 10px;
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
  flex: 0 0 calc(25% - 12px);
  min-width: 240px;
  aspect-ratio: 3/4;
  color: #ccc;
  transition: all 0.2s;
  border-radius: var(--radius-sm);
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
  font-size: 28px;
  font-weight: 300;
  margin-bottom: 6px;
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
  border-radius: var(--radius-sm);
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
  border-radius: var(--radius-sm);
}

.page-image-preview-full:hover .image-regenerate-overlay {
  opacity: 1;
}

.overlay-buttons {
  display: flex;
  flex-direction: column;
  gap: 10px;
  align-items: center;
}

.overlay-action-btn {
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
  font-weight: 500;
  min-width: 120px;
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

/* 错误提示 */
.error-toast {
  position: fixed;
  top: 16px;
  right: 16px;
  z-index: 2000;
  background: white;
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  padding: 12px 16px;
  min-width: 200px;
  max-width: 400px;
  animation: slideInRight 0.3s ease-out;
}

.error-content {
  color: #ff4d4f;
  font-size: 13px;
  line-height: 1.5;
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
  padding: 16px;
}

.confirm-dialog {
  background: white;
  border-radius: var(--radius-lg);
  width: 100%;
  max-width: 500px;
  box-shadow: var(--shadow-lg);
  animation: slideUp 0.3s ease-out;
}

.confirm-dialog-header {
  padding: 20px 20px 16px;
  border-bottom: 1px solid var(--border-color);
}

.confirm-dialog-header h3 {
  margin: 0;
  font-size: 17px;
  font-weight: 600;
  color: var(--text-main);
}

.confirm-dialog-content {
  padding: 20px;
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
  padding: 16px 20px 20px;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  border-top: 1px solid var(--border-color);
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }

  to {
    opacity: 1;
  }
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }

  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 图片占位符 */
.page-image-placeholder-full {
  width: 100%;
  height: 100%;
  background: #f9f9f9;
  border-radius: var(--radius-sm);
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
  padding: 8px 16px;
  background: var(--primary);
  color: white;
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 12px;
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
  bottom: 10px;
  right: 10px;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: white;
  border: 1px solid #e0e0e0;
  box-shadow: var(--shadow-sm);
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

/* 大图查看模态框 */
.large-image-modal {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.95);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  animation: fadeIn 0.2s;
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
  border-radius: var(--radius-sm);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
  transition: opacity 0.2s;
}

.close-large-image-btn {
  position: absolute;
  top: -40px;
  right: 0;
  width: 36px;
  height: 36px;
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
  width: 44px;
  height: 44px;
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
  left: 16px;
}

.nav-arrow-right {
  right: 16px;
}

/* 图片信息 */
.image-info {
  position: absolute;
  bottom: -40px;
  left: 50%;
  transform: translateX(-50%);
  color: white;
  font-size: 13px;
  background: rgba(0, 0, 0, 0.5);
  padding: 6px 14px;
  border-radius: 20px;
  z-index: 10;
}

/* 响应式设计 */
@media (max-width: 1024px) {
  .flip-card-wrapper,
  .add-card-dashed {
    flex: 0 0 calc(50% - 8px);
    min-width: calc(50% - 8px);
  }
  
  .outline-grid {
    gap: 16px;
  }
}

@media (max-width: 768px) {
  .outline-page {
    padding: 12px;
    gap: 12px;
  }

  .outline-content {
    gap: 12px;
  }

  .outline-main {
    gap: 12px;
  }

  .section-card {
    border-radius: var(--radius-sm);
  }

  .card-header {
    padding: 10px 12px;
  }

  .card-body {
    padding: 12px;
    gap: 12px;
  }

  .page-title {
    font-size: 20px;
  }

  .header-content {
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
    padding: 12px;
  }

  .action-buttons {
    width: 100%;
    flex-direction: column;
  }

  .btn {
    width: 100%;
    justify-content: center;
  }

  .reference-mode-selector {
    padding: 10px 12px;
  }

  .reference-mode-options {
    flex-direction: column;
    gap: 8px;
  }

  .flip-card-wrapper,
  .add-card-dashed {
    flex: 0 0 100%;
    min-width: 100%;
  }

  .outline-grid {
    gap: 12px;
  }

  .error-toast {
    top: 12px;
    right: 12px;
    left: 12px;
    max-width: none;
  }

  .nav-arrow-btn {
    width: 36px;
    height: 36px;
  }

  .nav-arrow-left {
    left: 8px;
  }

  .nav-arrow-right {
    right: 8px;
  }
}

@media (max-width: 480px) {
  .outline-page {
    padding: 8px;
    gap: 10px;
  }

  .card-header {
    padding: 8px 10px;
  }

  .card-body {
    padding: 10px;
    gap: 10px;
  }

  .page-title {
    font-size: 18px;
  }

  .topic-input {
    font-size: 14px;
    padding: 10px 12px;
  }

  .tone-textarea {
    min-height: 150px;
    font-size: 12px;
  }

  .metadata-input,
  .metadata-textarea {
    font-size: 12px;
    padding: 8px 10px;
  }
}
</style>
