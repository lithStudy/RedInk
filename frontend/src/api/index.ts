import axios from 'axios'

const API_BASE_URL = '/api'

export interface Page {
  id?: number  // 页面数据库ID，用于匹配图片关联（避免索引偏移问题）
  index: number
  type: 'cover' | 'content' | 'summary'
  content: string
  image?: {
    id: number
    filename: string
    thumbnail_filename: string
  } | null
}

export interface OutlineMetadata {
  title: string
  content: string
  tags: string
}

export interface OutlineResponse {
  success: boolean
  outline?: string
  pages?: Page[]
  record_id?: string
  error?: string
  metadata?: OutlineMetadata
}

export interface ProgressEvent {
  index?: number  // 页面索引（兼容旧版本）
  page_id?: number  // 页面数据库ID（新版本使用）
  status: 'generating' | 'done' | 'error'
  current?: number
  total?: number
  image_url?: string
  message?: string
  record_id?: string  // 记录ID（用于停止功能）
}

export interface FinishEvent {
  success: boolean
  record_id: string
  images: string[]
}

export interface ToneResponse {
  success: boolean
  tone?: string
  error?: string
}

// 生成基调
export async function generateTone(topic: string, recordId?: string): Promise<ToneResponse & { record_id?: string }> {
  const response = await axios.post<ToneResponse & { record_id?: string }>(`${API_BASE_URL}/tone`, {
    topic,
    record_id: recordId
  })
  return response.data
}

// 获取基调
export async function getTone(recordId: string): Promise<ToneResponse> {
  const response = await axios.get<ToneResponse>(`${API_BASE_URL}/tone/${recordId}`)
  return response.data
}

// 更新基调
export async function updateTone(recordId: string, tone: string): Promise<{ success: boolean; error?: string }> {
  const response = await axios.put(`${API_BASE_URL}/tone/${recordId}`, { tone })
  return response.data
}

// 更新大纲（例如删除页面后）
export async function updateOutline(recordId: string, pages: Page[]): Promise<{ success: boolean; error?: string }> {
  const response = await axios.put(`${API_BASE_URL}/outline/${recordId}`, { pages })
  return response.data
}

// 生成大纲（支持图片上传和基调）
export async function generateOutline(
  topic: string,
  images?: File[],
  tone?: string,
  recordId?: string
): Promise<OutlineResponse & { has_images?: boolean }> {
  // 如果有图片，使用 FormData
  if (images && images.length > 0) {
    const formData = new FormData()
    formData.append('topic', topic)
    if (tone) {
      formData.append('tone', tone)
    }
    if (recordId) {
      formData.append('record_id', recordId)
    }
    images.forEach((file) => {
      formData.append('images', file)
    })

    const response = await axios.post<OutlineResponse & { has_images?: boolean }>(
      `${API_BASE_URL}/outline`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      }
    )
    return response.data
  }

  // 无图片，使用 JSON
  const response = await axios.post<OutlineResponse>(`${API_BASE_URL}/outline`, {
    topic,
    tone,
    record_id: recordId
  })
  return response.data
}

// 获取图片 URL（新格式：record_id/filename）
// thumbnail 参数：true=缩略图（默认），false=原图
export function getImageUrl(recordId: string, filename: string, thumbnail: boolean = true): string {
  const thumbParam = thumbnail ? '?thumbnail=true' : '?thumbnail=false'
  return `${API_BASE_URL}/images/${recordId}/${filename}${thumbParam}`
}

// 重新生成图片（即使成功的也可以重新生成）
export async function regenerateImage(
  recordId: string,
  page: Page,
  useReference: boolean = true,
  context?: {
    fullOutline?: string
    userTopic?: string
  },
  referenceMode?: 'custom' | 'cover' | 'previous'
): Promise<{ success: boolean; index: number; image_url?: string; error?: string }> {
  const response = await axios.post(`${API_BASE_URL}/regenerate`, {
    record_id: recordId,
    page,
    use_reference: useReference,
    full_outline: context?.fullOutline,
    user_topic: context?.userTopic,
    reference_mode: referenceMode
  })
  return response.data
}

// 批量重试失败的图片（SSE）
export async function retryFailedImages(
  recordId: string,
  pages: Page[],
  onProgress: (event: ProgressEvent) => void,
  onComplete: (event: ProgressEvent) => void,
  onError: (event: ProgressEvent) => void,
  onFinish: (event: { success: boolean; total: number; completed: number; failed: number }) => void,
  onStreamError: (error: Error) => void
) {
  try {
    const response = await fetch(`${API_BASE_URL}/retry-failed`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        record_id: recordId,
        pages
      })
    })

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    const reader = response.body?.getReader()
    if (!reader) {
      throw new Error('无法读取响应流')
    }

    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()

      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (!line.trim()) continue

        const [eventLine, dataLine] = line.split('\n')
        if (!eventLine || !dataLine) continue

        const eventType = eventLine.replace('event: ', '').trim()
        const eventData = dataLine.replace('data: ', '').trim()

        try {
          const data = JSON.parse(eventData)

          switch (eventType) {
            case 'retry_start':
              onProgress({ index: -1, status: 'generating', message: data.message })
              break
            case 'complete':
              onComplete(data)
              break
            case 'error':
              onError(data)
              break
            case 'retry_finish':
              onFinish(data)
              break
          }
        } catch (e) {
          console.error('解析 SSE 数据失败:', e)
        }
      }
    }
  } catch (error) {
    onStreamError(error as Error)
  }
}

// ==================== 历史记录相关 API ====================

export interface HistoryRecord {
  id: string
  title: string
  created_at: string
  updated_at: string
  status: string
  thumbnail: string | null
  page_count: number
}

export interface HistoryDetail {
  id: string
  title: string
  topic?: string
  created_at: string
  updated_at: string
  outline: {
    raw: string
    pages: Page[]
    metadata?: OutlineMetadata
  }
  status: string
  thumbnail: string | null
}

// 创建历史记录
export async function createHistory(
  topic: string,
  outline: { raw: string; pages: Page[] },
  recordId?: string
): Promise<{ success: boolean; record_id?: string; error?: string }> {
  const response = await axios.post(`${API_BASE_URL}/history`, {
    topic,
    outline,
    record_id: recordId
  })
  return response.data
}

// 获取历史记录列表
export async function getHistoryList(
  page: number = 1,
  pageSize: number = 20,
  status?: string
): Promise<{
  success: boolean
  records: HistoryRecord[]
  total: number
  page: number
  page_size: number
  total_pages: number
}> {
  const params: any = { page, page_size: pageSize }
  if (status) params.status = status

  const response = await axios.get(`${API_BASE_URL}/history`, { params })
  return response.data
}

// 获取历史记录详情
export async function getHistory(recordId: string): Promise<{
  success: boolean
  record?: HistoryDetail
  error?: string
}> {
  const response = await axios.get(`${API_BASE_URL}/history/${recordId}`)
  return response.data
}

// 更新历史记录
export async function updateHistory(
  recordId: string,
  data: {
    topic?: string
    outline?: { raw: string; pages: Page[]; metadata?: OutlineMetadata }
    images?: { generated: string[] }
    status?: string
    thumbnail?: string
  }
): Promise<{ success: boolean; error?: string }> {
  const response = await axios.put(`${API_BASE_URL}/history/${recordId}`, data)
  return response.data
}

// 删除历史记录
export async function deleteHistory(recordId: string): Promise<{
  success: boolean
  error?: string
}> {
  const response = await axios.delete(`${API_BASE_URL}/history/${recordId}`)
  return response.data
}

// 搜索历史记录
export async function searchHistory(keyword: string): Promise<{
  success: boolean
  records: HistoryRecord[]
}> {
  const response = await axios.get(`${API_BASE_URL}/history/search`, {
    params: { keyword }
  })
  return response.data
}

// 获取统计信息
export async function getHistoryStats(): Promise<{
  success: boolean
  total: number
  by_status: Record<string, number>
}> {
  const response = await axios.get(`${API_BASE_URL}/history/stats`)
  return response.data
}

// 使用 POST 方式生成图片（更可靠）
export async function generateImagesPost(
  pages: Page[],
  recordId: string,
  fullOutline: string,
  onProgress: (event: ProgressEvent) => void,
  onComplete: (event: ProgressEvent) => void,
  onError: (event: ProgressEvent) => void,
  onFinish: (event: FinishEvent) => void,
  onStreamError: (error: Error) => void,
  userImages?: File[],
  userTopic?: string,
  onStopped?: (event: { record_id: string; message: string; completed: number; pending: number }) => void,
  referenceMode?: 'custom' | 'cover' | 'previous'
) {
  try {
    // 将用户图片转换为 base64
    let userImagesBase64: string[] = []
    if (userImages && userImages.length > 0) {
      userImagesBase64 = await Promise.all(
        userImages.map(file => {
          return new Promise<string>((resolve, reject) => {
            const reader = new FileReader()
            reader.onload = () => resolve(reader.result as string)
            reader.onerror = reject
            reader.readAsDataURL(file)
          })
        })
      )
    }

    const response = await fetch(`${API_BASE_URL}/generate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        pages,
        record_id: recordId,
        full_outline: fullOutline,
        user_images: userImagesBase64.length > 0 ? userImagesBase64 : undefined,
        user_topic: userTopic || '',
        reference_mode: referenceMode
      })
    })

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    const reader = response.body?.getReader()
    if (!reader) {
      throw new Error('无法读取响应流')
    }

    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()

      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (!line.trim()) continue

        const [eventLine, dataLine] = line.split('\n')
        if (!eventLine || !dataLine) continue

        const eventType = eventLine.replace('event: ', '').trim()
        const eventData = dataLine.replace('data: ', '').trim()

        try {
          const data = JSON.parse(eventData)

          switch (eventType) {
            case 'progress':
              onProgress(data)
              break
            case 'complete':
              onComplete(data)
              break
            case 'error':
              onError(data)
              break
            case 'finish':
              onFinish(data)
              break
            case 'stopped':
              if (onStopped) onStopped(data)
              break
          }
        } catch (e) {
          console.error('解析 SSE 数据失败:', e)
        }
      }
    }
  } catch (error) {
    onStreamError(error as Error)
  }
}

// 停止图片生成
export async function stopGeneration(recordId: string): Promise<{
  success: boolean
  message?: string
  error?: string
}> {
  const response = await axios.post(`${API_BASE_URL}/stop-generation`, {
    record_id: recordId
  })
  return response.data
}

// 生成单张图片（根据pageId，同步接口）
export async function generateSingleImage(
  recordId: string,
  pageId: number,
  fullOutline?: string,
  userTopic?: string,
  userImages?: File[],
  referenceMode?: 'custom' | 'cover' | 'previous'
): Promise<{
  success: boolean
  page_id?: number
  image_url?: string
  error?: string
}> {
  // 将用户图片转换为 base64
  let userImagesBase64: string[] = []
  if (userImages && userImages.length > 0) {
    userImagesBase64 = await Promise.all(
      userImages.map(file => {
        return new Promise<string>((resolve, reject) => {
          const reader = new FileReader()
          reader.onload = () => resolve(reader.result as string)
          reader.onerror = reject
          reader.readAsDataURL(file)
        })
      })
    )
  }

  const response = await axios.post(`${API_BASE_URL}/generate-single`, {
    record_id: recordId,
    page_id: pageId,
    full_outline: fullOutline || '',
    user_topic: userTopic || '',
    user_images: userImagesBase64.length > 0 ? userImagesBase64 : undefined,
    reference_mode: referenceMode || 'cover'
  })
  return response.data
}


// 继续图片生成（SSE）- 自动扫描未完成的页面
export async function continueGeneration(
  recordId: string,
  onProgress: (event: ProgressEvent) => void,
  onComplete: (event: ProgressEvent) => void,
  onError: (event: ProgressEvent) => void,
  onFinish: (event: FinishEvent) => void,
  onStopped: (event: { record_id: string; message: string; completed: number; pending: number }) => void,
  onStreamError: (error: Error) => void
) {
  try {
    const response = await fetch(`${API_BASE_URL}/continue-generation`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        record_id: recordId
      })
    })

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    const reader = response.body?.getReader()
    if (!reader) {
      throw new Error('无法读取响应流')
    }

    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()

      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (!line.trim()) continue

        const [eventLine, dataLine] = line.split('\n')
        if (!eventLine || !dataLine) continue

        const eventType = eventLine.replace('event: ', '').trim()
        const eventData = dataLine.replace('data: ', '').trim()

        try {
          const data = JSON.parse(eventData)

          switch (eventType) {
            case 'continue_start':
              // 传递完整数据，包括 total 和 completed 用于更新进度
              onProgress({ 
                index: -1, 
                status: 'generating', 
                message: data.message,
                total: data.total,
                current: data.completed,
                ...data
              })
              break
            case 'progress':
              onProgress(data)
              break
            case 'complete':
              onComplete(data)
              break
            case 'error':
              onError(data)
              break
            case 'stopped':
              onStopped(data)
              break
            case 'finish':
              onFinish(data)
              break
          }
        } catch (e) {
          console.error('解析 SSE 数据失败:', e)
        }
      }
    }
  } catch (error) {
    onStreamError(error as Error)
  }
}

// 获取记录文件夹中的图片列表（扫描文件系统）
export async function getTaskImages(recordId: string): Promise<{
  success: boolean
  images?: string[]
  generated_indices?: number[]
  outline?: {
    raw?: string
    pages: Page[]
    topic?: string
    total: number
    metadata?: OutlineMetadata
  }
  error?: string
}> {
  const response = await axios.get(`${API_BASE_URL}/task/${recordId}/images`)
  return response.data
}

// 扫描所有任务并同步图片列表
export async function scanAllTasks(): Promise<{
  success: boolean
  total_tasks?: number
  synced?: number
  failed?: number
  orphan_tasks?: string[]
  results?: any[]
  error?: string
}> {
  const response = await axios.post(`${API_BASE_URL}/history/scan-all`)
  return response.data
}

// ==================== 配置管理 API ====================

export interface Config {
  text_generation: {
    active_provider: string
    providers: Record<string, any>
  }
  image_generation: {
    active_provider: string
    providers: Record<string, any>
  }
}

// 获取配置
export async function getConfig(): Promise<{
  success: boolean
  config?: Config
  error?: string
}> {
  const response = await axios.get(`${API_BASE_URL}/config`)
  return response.data
}

// 更新配置
export async function updateConfig(config: Partial<Config>): Promise<{
  success: boolean
  message?: string
  error?: string
}> {
  const response = await axios.post(`${API_BASE_URL}/config`, config)
  return response.data
}

// 测试服务商连接
export async function testConnection(config: {
  type: string
  provider_name?: string
  api_key?: string
  base_url?: string
  model: string
}): Promise<{
  success: boolean
  message?: string
  error?: string
}> {
  const response = await axios.post(`${API_BASE_URL}/config/test`, config)
  return response.data
}
