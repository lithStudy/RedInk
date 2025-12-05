import { defineStore } from 'pinia'
import type { Page } from '../api'

export interface GeneratedImage {
  index: number
  url: string
  status: 'generating' | 'done' | 'error' | 'retrying'
  error?: string
  retryable?: boolean
}

export interface OutlineMetadata {
  title: string
  content: string
  tags: string
}

export interface GeneratorState {
  // 当前阶段
  stage: 'input' | 'outline' | 'generating' | 'result'

  // 用户输入
  topic: string

  // 大纲数据
  outline: {
    raw: string
    pages: Page[]
    metadata?: OutlineMetadata  // 小红书标题、正文和标签
  }

  // 生成进度
  progress: {
    current: number
    total: number
    status: 'idle' | 'generating' | 'done' | 'error' | 'paused'
  }

  // 生成结果
  images: GeneratedImage[]

  // 任务ID
  taskId: string | null

  // 历史记录ID
  recordId: string | null

  // 用户上传的图片（用于图片生成参考）
  userImages: File[]
}

const STORAGE_KEY_PREFIX = 'generator-state'

// 根据 recordId 生成 localStorage 键名
function getStorageKey(recordId: string | null): string {
  return `${STORAGE_KEY_PREFIX}-${recordId || 'draft'}`
}

// 从 localStorage 加载指定任务的状态
function loadStateFromCache(recordId: string | null): Partial<GeneratorState> {
  try {
    const key = getStorageKey(recordId)
    const saved = localStorage.getItem(key)
    if (saved) {
      const parsed = JSON.parse(saved)
      console.log(`✅ 从缓存加载任务状态: ${key}`)
      return parsed
    }
  } catch (e) {
    console.error('加载缓存失败:', e)
  }
  return {}
}

// 保存状态到 localStorage（基于 recordId）
function saveStateToCache(state: GeneratorState) {
  if (!state.recordId) {
    // 没有 recordId，使用 draft 键保存
    console.log('⚠️ 保存草稿状态（无 recordId）')
  }
  
  try {
    const key = getStorageKey(state.recordId)
    // 只保存关键数据，不保存 userImages（文件对象无法序列化）
    const toSave = {
      stage: state.stage,
      topic: state.topic,
      outline: state.outline,
      progress: state.progress,
      images: state.images,
      taskId: state.taskId,
      recordId: state.recordId
    }
    localStorage.setItem(key, JSON.stringify(toSave))
    console.log(`💾 已缓存任务状态: ${key}`)
  } catch (e) {
    console.error('保存缓存失败:', e)
  }
}

// 清除指定任务的缓存
function clearStateCache(recordId: string | null) {
  try {
    const key = getStorageKey(recordId)
    localStorage.removeItem(key)
    console.log(`🗑️ 已清除缓存: ${key}`)
  } catch (e) {
    console.error('清除缓存失败:', e)
  }
}

export const useGeneratorStore = defineStore('generator', {
  state: (): GeneratorState => {
    // 不再自动加载，由各个页面根据 URL 参数决定是否加载缓存
    return {
      stage: 'input',
      topic: '',
      outline: {
        raw: '',
        pages: [],
        metadata: undefined
      },
      progress: {
        current: 0,
        total: 0,
        status: 'idle'
      },
      images: [],
      taskId: null,
      recordId: null,
      userImages: []
    }
  },

  actions: {
    // 设置主题
    setTopic(topic: string) {
      this.topic = topic
    },

    // 设置大纲
    setOutline(raw: string, pages: Page[], metadata?: OutlineMetadata) {
      console.log('🔧 setOutline 被调用，metadata:', metadata)
      this.outline.raw = raw
      this.outline.pages = pages
      this.outline.metadata = metadata
      this.stage = 'outline'
      console.log('✅ outline.metadata 已设置:', this.outline.metadata)
    },

    // 更新页面
    updatePage(index: number, content: string) {
      const page = this.outline.pages.find(p => p.index === index)
      if (page) {
        page.content = content
        // 同步更新 raw 文本
        this.syncRawFromPages()
      }
    },

    // 根据 pages 重新生成 raw 文本
    syncRawFromPages() {
      this.outline.raw = this.outline.pages
        .map(page => page.content)
        .join('\n\n<page>\n\n')
    },

    // 删除页面
    deletePage(index: number) {
      // 先从数组中删除页面
      this.outline.pages = this.outline.pages.filter(p => p.index !== index)
      // 重新索引
      this.outline.pages.forEach((page, idx) => {
        page.index = idx
      })
      // 同步更新 raw 文本
      this.syncRawFromPages()
      
      // 同时更新 images 数组
      this.images = this.images.filter(img => img.index !== index)
      // 重新索引 images
      this.images.forEach((img, idx) => {
        img.index = idx
      })
      
      // 更新 progress.total
      this.progress.total = this.outline.pages.length
    },

    // 添加页面
    addPage(type: 'cover' | 'content' | 'summary', content: string = '') {
      const newPage: Page = {
        index: this.outline.pages.length,
        type,
        content
      }
      this.outline.pages.push(newPage)
      // 同步更新 raw 文本
      this.syncRawFromPages()
    },

    // 插入页面
    insertPage(afterIndex: number, type: 'cover' | 'content' | 'summary', content: string = '') {
      const newPage: Page = {
        index: afterIndex + 1,
        type,
        content
      }
      this.outline.pages.splice(afterIndex + 1, 0, newPage)
      // 重新索引
      this.outline.pages.forEach((page, idx) => {
        page.index = idx
      })
      // 同步更新 raw 文本
      this.syncRawFromPages()
    },

    // 移动页面 (拖拽排序)
    movePage(fromIndex: number, toIndex: number) {
      const pages = [...this.outline.pages]
      const [movedPage] = pages.splice(fromIndex, 1)
      pages.splice(toIndex, 0, movedPage)

      // 重新索引
      pages.forEach((page, idx) => {
        page.index = idx
      })

      this.outline.pages = pages
      
      // 同时移动 images 数组
      if (this.images.length > 0) {
        const images = [...this.images]
        const [movedImage] = images.splice(fromIndex, 1)
        images.splice(toIndex, 0, movedImage)
        
        // 重新索引 images
        images.forEach((img, idx) => {
          img.index = idx
        })
        
        this.images = images
      }
      
      // 同步更新 raw 文本
      this.syncRawFromPages()
    },

    // 开始生成
    startGeneration() {
      this.stage = 'generating'
      this.progress.current = 0
      this.progress.total = this.outline.pages.length
      this.progress.status = 'generating'
      this.images = this.outline.pages.map(page => ({
        index: page.index,
        url: '',
        status: 'generating'
      }))
    },

    // 更新进度
    updateProgress(index: number, status: 'generating' | 'done' | 'error', url?: string, error?: string) {
      const image = this.images.find(img => img.index === index)
      if (image) {
        image.status = status
        if (url) image.url = url
        if (error) image.error = error
      }
      if (status === 'done') {
        this.progress.current++
      }
    },

    updateImage(index: number, newUrl: string) {
      const image = this.images.find(img => img.index === index)
      if (image) {
        const timestamp = Date.now()
        image.url = `${newUrl}?t=${timestamp}`
        image.status = 'done'
        delete image.error
      }
    },

    // 完成生成
    finishGeneration(taskId: string) {
      this.taskId = taskId
      this.stage = 'result'
      this.progress.status = 'done'
    },

    // 暂停生成
    pauseGeneration() {
      this.progress.status = 'paused'
      // 将正在生成中的图片状态设为等待
      this.images.forEach(img => {
        if (img.status === 'generating') {
          img.status = 'generating' // 保持状态，等待 SSE 停止事件
        }
      })
    },

    // 继续生成
    resumeGeneration() {
      this.progress.status = 'generating'
    },

    // 获取未完成的页面
    getPendingPages() {
      const completedIndices = this.images
        .filter(img => img.status === 'done')
        .map(img => img.index)
      return this.outline.pages.filter(page => !completedIndices.includes(page.index))
    },

    // 标记图片为等待状态（停止后）
    markPendingImages() {
      this.images.forEach(img => {
        if (img.status === 'generating') {
          // 保持为 generating 状态但实际上已经被停止
          // 前端会显示为等待中
        }
      })
    },

    // 设置单个图片为重试中状态
    setImageRetrying(index: number) {
      const image = this.images.find(img => img.index === index)
      if (image) {
        image.status = 'retrying'
      }
    },

    // 获取失败的图片列表
    getFailedImages() {
      return this.images.filter(img => img.status === 'error')
    },

    // 获取失败图片对应的页面
    getFailedPages() {
      const failedIndices = this.images
        .filter(img => img.status === 'error')
        .map(img => img.index)
      return this.outline.pages.filter(page => failedIndices.includes(page.index))
    },

    // 检查是否有失败的图片
    hasFailedImages() {
      return this.images.some(img => img.status === 'error')
    },

    // 从缓存加载状态（优先使用缓存快速恢复 UI）
    loadFromCache(recordId: string | null) {
      const cached = loadStateFromCache(recordId)
      if (cached && Object.keys(cached).length > 0) {
        // 使用缓存数据
        this.stage = cached.stage || this.stage
        this.topic = cached.topic || this.topic
        this.outline = cached.outline || this.outline
        this.progress = cached.progress || this.progress
        this.images = cached.images || this.images
        this.taskId = cached.taskId || this.taskId
        this.recordId = cached.recordId || this.recordId
        // userImages 不从缓存恢复
        return true
      }
      return false
    },

    // 保存当前状态到缓存
    saveToStorage() {
      saveStateToCache(this)
    },

    // 清除缓存
    clearCache() {
      clearStateCache(this.recordId)
    },

    // 重置（清空所有状态并清除缓存）
    reset() {
      const oldRecordId = this.recordId
      this.stage = 'input'
      this.topic = ''
      this.outline = {
        raw: '',
        pages: [],
        metadata: undefined
      }
      this.progress = {
        current: 0,
        total: 0,
        status: 'idle'
      }
      this.images = []
      this.taskId = null
      this.recordId = null
      this.userImages = []
      // 清除缓存
      if (oldRecordId) {
        clearStateCache(oldRecordId)
      }
    }
  }
})
