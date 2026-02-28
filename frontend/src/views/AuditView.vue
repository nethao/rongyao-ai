<template>
  <div class="audit-container">
    <el-card class="header-card">
      <div class="header-content">
        <div class="header-left">
          <el-button @click="handleBack">
            <el-icon><ArrowLeft /></el-icon>
            返回列表
          </el-button>
          <h2>内容审核</h2>
          <el-tag v-if="contentSource" :type="getSourceTagType(contentSource)" size="large" style="margin-left: 12px;">
            <img :src="getSourceIconUrl(contentSource)" :alt="getSourceLabel(contentSource)" style="width: 18px; height: 18px; margin-right: 4px; vertical-align: middle;" />
            {{ getSourceLabel(contentSource) }}
          </el-tag>
          <div class="header-meta">
            <span>合作方式：{{ getCooperationLabel(cooperationType) }}</span>
            <span>来稿单位：{{ sourceUnit || '-' }}</span>
            <span>发布媒体：{{ getMediaTypeLabel(mediaType) }}</span>
          </div>
        </div>
        <div class="header-right">
          <el-button type="warning" @click="handleRestoreAI">
            <el-icon><RefreshLeft /></el-icon>
            恢复AI版本
          </el-button>
          <el-button type="success" @click="handleSave" :loading="saving">
            <el-icon><Check /></el-icon>
            保存修改
          </el-button>
          <el-button type="primary" @click="handlePublish">
            <el-icon><Upload /></el-icon>
            发布
          </el-button>
        </div>
      </div>
    </el-card>

    <!-- 公众号/美篇文章提示 -->
    <el-alert
      v-if="contentSource === 'weixin' || contentSource === 'meipian'"
      :title="contentSource === 'weixin' ? '此为公众号文章，需手动修改' : '此为美篇文章，需手动修改'"
      type="warning"
      :closable="false"
      show-icon
      style="margin-bottom: 20px;"
    >
      <template #default>
        {{ contentSource === 'weixin' ? '公众号' : '美篇' }}文章已保留原始样式，请在编辑器中手动调整格式和内容。
      </template>
    </el-alert>

    <!-- 其他链接提示 -->
    <el-alert
      v-if="contentSource === 'other_url'"
      title="此为外部链接，需手动采集"
      type="warning"
      :closable="false"
      show-icon
      style="margin-bottom: 20px;"
    >
      <template #default>
        请在左侧「原始内容」区点击链接打开原文，手动复制内容后粘贴到中间编辑器，再点击「AI改写」。
      </template>
    </el-alert>

    <el-card v-loading="loading" class="content-card">
      <div class="three-pane-container">
        <!-- 左栏：原文（HTML预览） -->
        <div class="pane left-pane">
          <div class="pane-header">
            <h3>原始内容</h3>
            <div style="display: flex; gap: 8px; align-items: center;">
              <el-button-group size="small">
                <el-button @click="iframeGoBack" :disabled="!canGoBack">
                  <el-icon><ArrowLeft /></el-icon>
                  后退
                </el-button>
                <el-button @click="iframeGoForward" :disabled="!canGoForward">
                  前进
                  <el-icon><ArrowRight /></el-icon>
                </el-button>
              </el-button-group>
              <el-tag type="info">只读</el-tag>
            </div>
          </div>
          <div class="pane-content left-content-wrap">
            <!-- 原文标题（只读） -->
            <div class="article-title-section">
              <div class="article-title-readonly">{{ articleTitle }}</div>
            </div>
            
            <iframe
              v-if="originalHtml"
              ref="previewIframeRef"
              class="html-preview-iframe"
              sandbox="allow-same-origin allow-scripts allow-popups allow-popups-to-escape-sandbox"
              title="原文预览"
            />
            <div v-else class="html-preview-empty">暂无原文</div>
          </div>
        </div>

        <!-- 中间：AI转换内容（Tiptap 编辑器） -->
        <div class="pane middle-pane">
          <div class="pane-header">
            <h3>AI转换内容</h3>
            <div class="pane-actions">
              <el-button
                type="primary"
                :loading="transforming"
                :disabled="!submissionId || contentSource === 'video'"
                @click="handleAiTransform"
              >
                <el-icon><Edit /></el-icon>
                AI改写
              </el-button>
              <el-upload
                :show-file-list="false"
                :before-upload="handleWordUpload"
                accept=".doc,.docx"
              >
                <el-button :loading="wordUploading">
                  <el-icon><Document /></el-icon>
                  Word上传
                </el-button>
              </el-upload>
              <el-upload
                :show-file-list="false"
                :before-upload="handleImageUpload"
                accept="image/*"
              >
                <el-button>
                  <el-icon><Picture /></el-icon>
                  图片上传
                </el-button>
              </el-upload>
              <el-tooltip 
                v-if="contentSource === 'video'" 
                content="视频内容需要手工编辑，不支持AI改写" 
                placement="bottom"
              >
                <el-tag type="info" style="margin-left: 8px;">
                  <el-icon><InfoFilled /></el-icon>
                  视频内容
                </el-tag>
              </el-tooltip>
              <el-button
                @click="showSourceCode = !showSourceCode"
                :type="showSourceCode ? 'warning' : 'default'"
              >
                <el-icon><Document /></el-icon>
                {{ showSourceCode ? '可视化' : '源码' }}
              </el-button>
              <el-tag v-if="hasUnsavedChanges" type="warning">未保存</el-tag>
              <el-tag v-else type="success">已保存</el-tag>
              <span class="version-info">版本 {{ currentVersion }}</span>
            </div>
          </div>
          <div class="pane-content middle-editor-wrap">
            <!-- 文章标题 -->
            <div class="article-title-section">
              <el-input
                v-model="articleTitle"
                placeholder="请输入文章标题"
                size="large"
                class="article-title-input"
                @input="handleTitleChange"
              />
            </div>

            <!-- AI改写进度条 -->
            <div v-if="transforming" class="transform-progress">
              <el-progress 
                :percentage="transformProgress" 
                :stroke-width="20"
                :text-inside="true"
                status="success"
              >
                <span class="progress-text">AI改写中... {{ transformProgress }}%</span>
              </el-progress>
              <p class="progress-tip">正在保持图文排版进行智能改写，请稍候...</p>
            </div>
            
            <!-- 源码编辑器 -->
            <el-input
              v-if="showSourceCode"
              v-model="editableHtml"
              type="textarea"
              @input="handleContentChange"
              placeholder="HTML源码"
              class="source-code-editor"
            />
            
            <!-- 可视化编辑器 -->
            <TiptapEditor
              v-else
              ref="tiptapRef"
              v-model="editableHtml"
              @change="handleContentChange"
            />
          </div>
        </div>

        <!-- 右侧边栏：本文附件 -->
        <div class="sidebar right-sidebar">
          <div class="sidebar-header">
            <h3>本文附件</h3>
          </div>
          <div class="sidebar-content">
            <el-alert
              title="OSS文件自动删除规则"
              type="info"
              :closable="false"
              show-icon
              style="margin-bottom: 12px;"
            >
              <template #default>
                默认保留 {{ attachmentRetentionDays || 15 }} 天，过期自动清理。
              </template>
            </el-alert>

            <div v-if="attachments.length > 0" class="attachments-list">
              <div
                v-for="att in attachments"
                :key="`${att.type}-${att.id || att.url}`"
                class="attachment-item"
              >
                <div class="attachment-icon">
                  <el-icon v-if="att.type === 'image'"><Picture /></el-icon>
                  <img v-else-if="att.type === 'video'" :src="mp4IconUrl" alt="视频" />
                  <img v-else-if="att.type === 'word'" src="/icons/WORD.svg" alt="Word" />
                  <img v-else-if="att.type === 'archive'" :src="archiveIconUrl" alt="压缩包" />
                  <img v-else :src="webIconUrl" alt="附件" />
                </div>
                <div class="attachment-info">
                  <div class="attachment-name" :title="att.name">{{ att.name }}</div>
                  <div class="attachment-meta">
                    <span>{{ getAttachmentTypeLabel(att.type) }}</span>
                    <span v-if="att.size"> · {{ formatFileSize(att.size) }}</span>
                  </div>
                </div>
                <div class="attachment-actions">
                  <a :href="att.url" target="_blank">查看</a>
                </div>
              </div>
            </div>
            <el-empty v-else description="暂无附件" />
          </div>
        </div>
      </div>
    </el-card>

    <!-- 发布对话框 -->
    <el-dialog
      v-model="publishDialogVisible"
      title="发布到WordPress"
      width="600px"
    >
      <el-form label-width="100px">
        <el-form-item label="选择站点">
          <el-select
            v-model="selectedSiteId"
            placeholder="请选择发布站点"
            style="width: 100%"
          >
            <el-option
              v-for="site in wordpressSites"
              :key="site.id"
              :label="`${site.name} (ID: ${site.id})`"
              :value="site.id"
            >
              <span>{{ site.name }}</span>
              <span style="color: #8492a6; font-size: 12px; margin-left: 10px">ID: {{ site.id }}</span>
              <span style="color: #8492a6; font-size: 12px; margin-left: 8px">{{ site.url }}</span>
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="合作方式">
          <el-input :value="getCooperationLabel(cooperationType)" disabled />
        </el-form-item>
        <el-form-item label="来稿单位">
          <el-input :value="sourceUnit || '-'" disabled />
        </el-form-item>
        <el-form-item label="发布媒体">
          <el-input :value="getMediaTypeLabel(mediaType)" disabled />
        </el-form-item>
        <el-form-item label="文章标题">
          <el-input :value="articleTitle" disabled />
        </el-form-item>
      </el-form>
      
      <!-- 发布历史 -->
      <div v-if="publishHistory.length > 0" style="margin-top: 20px;">
        <el-divider content-position="left">发布历史</el-divider>
        <el-timeline>
          <el-timeline-item
            v-for="item in publishHistory"
            :key="item.id"
            :timestamp="formatDateTime(item.created_at)"
            :type="item.status === 'success' ? 'success' : 'danger'"
            placement="top"
          >
            <div>
              <el-tag :type="item.status === 'success' ? 'success' : 'danger'" size="small">
                {{ item.status === 'success' ? '成功' : '失败' }}
              </el-tag>
              <span style="margin-left: 10px;">{{ item.site_name }}</span>
              <span v-if="item.wordpress_post_id" style="margin-left: 10px; color: #909399;">
                文章ID: {{ item.wordpress_post_id }}
              </span>
              <a 
                v-if="item.status === 'success' && item.wordpress_post_id && item.site_url"
                :href="`${item.site_url}?p=${item.wordpress_post_id}`"
                target="_blank"
                style="margin-left: 10px; color: #409eff;"
              >
                查看文章 <el-icon><Link /></el-icon>
              </a>
            </div>
            <div style="color: #909399; font-size: 12px; margin-top: 5px;">
              {{ item.message }}
            </div>
          </el-timeline-item>
        </el-timeline>
      </div>
      
      <template #footer>
        <el-button @click="publishDialogVisible = false">取消</el-button>
        <el-button
          type="primary"
          :loading="publishLoading"
          @click="confirmPublish"
        >
          确认发布
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ArrowLeft,
  ArrowRight,
  RefreshLeft,
  Check,
  Upload,
  Edit,
  Document,
  Picture,
  InfoFilled,
  Link,
} from '@element-plus/icons-vue'
import { getDraft, updateDraft, restoreAIVersion, uploadWordToDraft } from '../api/draft'
import { triggerTransform, getTransformStatus } from '../api/submission'
import { markdownToHtml, htmlToMarkdown } from '../utils/markdown'
import TiptapEditor from '../components/TiptapEditor.vue'

const router = useRouter()
const route = useRoute()

// 数据
const loading = ref(false)
const saving = ref(false)
const transforming = ref(false)
const wordUploading = ref(false)
const showSourceCode = ref(false)  // 源码模式
const draftId = ref(null)
const submissionId = ref(null)
const articleTitle = ref('')
const contentSource = ref('')
const originalContent = ref('')
const originalHtml = ref('')
const editableContent = ref('')
const editableHtml = ref('')
const currentVersion = ref(1)
const hasUnsavedChanges = ref(false)
const cooperationType = ref('')
const mediaType = ref('')
const sourceUnit = ref('')

// 版本历史
// 附件
const attachments = ref([])
const attachmentRetentionDays = ref(15)

// 自动保存定时器
let autoSaveTimer = null

// 编辑器 ref
const tiptapRef = ref(null)

// 原文预览 iframe
const previewIframeRef = ref(null)
const canGoBack = ref(false)
const canGoForward = ref(false)

// iframe 导航控制
const iframeGoBack = () => {
  if (previewIframeRef.value?.contentWindow) {
    previewIframeRef.value.contentWindow.history.back()
    updateNavigationState()
  }
}

const iframeGoForward = () => {
  if (previewIframeRef.value?.contentWindow) {
    previewIframeRef.value.contentWindow.history.forward()
    updateNavigationState()
  }
}

const updateNavigationState = () => {
  setTimeout(() => {
    if (previewIframeRef.value?.contentWindow) {
      const win = previewIframeRef.value.contentWindow
      canGoBack.value = win.history.length > 1
      canGoForward.value = false // 浏览器无法直接检测 forward 状态
    }
  }, 100)
}

// 公众号排版基础样式
const WEIXIN_PREVIEW_STYLE = `
  * { box-sizing: border-box !important; word-wrap: break-word !important; }
  html, body { margin: 0; padding: 0; background: #fff; min-height: 100%; overflow-x: hidden; }
  body { -webkit-overflow-scrolling: touch; }
  .rich_media_content {
    max-width: 677px;
    margin: 0 auto;
  }
  .rich_media_content img { max-width: 100% !important; height: auto !important; vertical-align: bottom; }
  .rich_media_content svg { max-width: 100%; height: auto; }
`

// 将原文 HTML 写入 iframe
function writePreviewIframe(html) {
  if (!html) return
  const doWrite = () => {
    const iframe = previewIframeRef.value
    if (!iframe || !iframe.contentDocument) return false
    const doc = iframe.contentDocument
    doc.open()
    doc.write(
      `<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><style>${WEIXIN_PREVIEW_STYLE}</style></head><body>${html}</body></html>`
    )
    doc.close()
    
    // 监听 iframe 内的导航事件
    try {
      iframe.contentWindow.addEventListener('popstate', updateNavigationState)
      iframe.contentWindow.addEventListener('hashchange', updateNavigationState)
    } catch (e) {
      // 跨域限制，忽略
    }
    updateNavigationState()
    
    return true
  }
  if (doWrite()) return
  nextTick(() => {
    if (!doWrite()) nextTick(doWrite)
  })
}

watch(originalHtml, (val) => {
  if (val) writePreviewIframe(val)
}, { immediate: false })

// 加载草稿数据
const loadDraft = async () => {
  loading.value = true
  try {
    const id = route.params.draftId || route.params.submissionId

    if (!id) {
      ElMessage.error('缺少草稿ID')
      router.push({ name: 'submissions' })
      return
    }

    draftId.value = parseInt(id)

    const response = await getDraft(draftId.value)
    submissionId.value = response.submission_id
    articleTitle.value = response.email_subject || ''
    contentSource.value = response.content_source || ''
    targetSiteId.value = response.target_site_id || null  // 获取目标站点ID
    cooperationType.value = response.cooperation_type || ''
    mediaType.value = response.media_type || ''
    sourceUnit.value = response.source_unit || ''
    console.log('加载草稿，目标站点ID:', targetSiteId.value)
    originalContent.value = response.original_content
    currentVersion.value = response.current_version
    hasUnsavedChanges.value = false

    // 编辑器内容：后端已做 Hydration（占位符→img），直接使用；无 media_map 时按旧数据转 HTML
    const hasPlaceholders = response.media_map && Object.keys(response.media_map).length > 0
    const isVideo = response.content_source === 'video'
    const processedContent = hasPlaceholders || isVideo
      ? response.current_content
      : markdownToHtml(response.current_content)
    
    editableContent.value = response.current_content
    editableHtml.value = processedContent

    // 优先使用原始HTML，否则转换Markdown
    if (response.original_html) {
      originalHtml.value = response.original_html
    } else {
      originalHtml.value = markdownToHtml(originalContent.value)
    }

    // 写入 iframe 以还原公众号排版
    if (response.original_html) {
      await nextTick()
      writePreviewIframe(originalHtml.value)
    }

    // 附件
    attachments.value = response.attachments || []
    attachmentRetentionDays.value = response.attachment_retention_days || 15
  } catch (error) {
    ElMessage.error('加载草稿失败: ' + (error.message || '未知错误'))
    router.push({ name: 'submissions' })
  } finally {
    loading.value = false
  }
}

// 内容变化处理
const handleContentChange = () => {
  hasUnsavedChanges.value = true
  // 暂时禁用自动保存，避免频繁创建版本
  // startAutoSave()
}

const handleTitleChange = () => {
  hasUnsavedChanges.value = true
  // 暂时禁用自动保存
  // startAutoSave()
}

// 自动保存
const startAutoSave = () => {
  if (autoSaveTimer) {
    clearTimeout(autoSaveTimer)
  }
  autoSaveTimer = setTimeout(() => {
    handleSave(true)
  }, 3000)
}

// 保存修改
const handleSave = async (isAutoSave = false) => {
  if (!hasUnsavedChanges.value) {
    if (!isAutoSave) {
      ElMessage.info('没有需要保存的修改')
    }
    return
  }

  let html = ''
  if (showSourceCode.value) {
    html = editableHtml.value || ''
  } else {
    html = tiptapRef.value?.getHTML?.() || editableHtml.value || ''
  }
  if (!html) return

  saving.value = true
  try {
    // 直接传HTML给后端，让后端的dehydrate处理
    const response = await updateDraft(draftId.value, html)

    currentVersion.value = response.current_version
    hasUnsavedChanges.value = false

    if (!isAutoSave) {
      ElMessage.success('保存成功')
    }
  } catch (error) {
    const detail = error.response?.data?.detail
    const msg = typeof detail === 'string' ? detail : (error.message || '未知错误')
    ElMessage.error('保存失败: ' + msg)
  } finally {
    saving.value = false
  }
}

// 返回列表
const handleBack = async () => {
  if (hasUnsavedChanges.value) {
    try {
      await ElMessageBox.confirm(
        '有未保存的修改，确定要离开吗？',
        '提示',
        {
          confirmButtonText: '离开',
          cancelButtonText: '取消',
          type: 'warning'
        }
      )
    } catch {
      return
    }
  }

  router.push({ name: 'submissions' })
}

// AI 改写
const POLL_INTERVAL = 2000  // 2秒轮询一次
const POLL_TIMEOUT = 180000  // 3分钟超时（AI改写需要更长时间）
const transformProgress = ref(0)  // 进度百分比

const handleAiTransform = async () => {
  if (!submissionId.value) {
    ElMessage.warning('无法获取投稿信息')
    return
  }
  try {
    await ElMessageBox.confirm(
      'AI改写将保持原文的图文排版不变，仅优化文字表达。预计需要1-3分钟，确定开始吗？',
      'AI 改写',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'info'
      }
    )

    console.log('=== AI改写开始 ===')
    console.log('投稿ID:', submissionId.value)
    console.log('草稿ID:', draftId.value)
    console.log('当前版本:', currentVersion.value)
    
    transforming.value = true
    transformProgress.value = 0
    
    console.log('步骤1: 调用triggerTransform API...')
    const triggerResult = await triggerTransform(submissionId.value)
    console.log('triggerTransform返回:', triggerResult)
    
    ElMessage.success('AI 改写任务已启动，正在处理中...')

    const startTime = Date.now()
    const prevContent = editableContent.value
    const prevVersion = currentVersion.value
    console.log('步骤2: 开始轮询，初始内容长度:', prevContent?.length)

    let pollCount = 0
    const applyDraftUpdate = async (res) => {
      const hasPlaceholders = res.media_map && Object.keys(res.media_map).length > 0
      const processedContent = hasPlaceholders ? res.current_content : markdownToHtml(res.current_content)
      editableContent.value = res.current_content
      editableHtml.value = processedContent
      currentVersion.value = res.current_version
      hasUnsavedChanges.value = false
      tiptapRef.value?.setHTML?.(processedContent)
      transforming.value = false
      transformProgress.value = 100
      setTimeout(() => {
        transformProgress.value = 0
        ElMessage.success('AI 改写已完成！图文排版已保留')
      }, 500)
    }

    const poll = async () => {
      pollCount++
      const elapsed = Date.now() - startTime

      if (elapsed < 30000) {
        transformProgress.value = Math.min(30, Math.floor(elapsed / 1000))
      } else if (elapsed < 90000) {
        transformProgress.value = Math.min(70, 30 + Math.floor((elapsed - 30000) / 1500))
      } else {
        transformProgress.value = Math.min(95, 70 + Math.floor((elapsed - 90000) / 3000))
      }

      if (elapsed > POLL_TIMEOUT) {
        transforming.value = false
        transformProgress.value = 0
        ElMessage.warning('等待超时，请手动刷新查看结果')
        return
      }

      try {
        // 先查任务状态：若已失败则直接提示并停止
        const statusRes = await getTransformStatus(submissionId.value)
        if (statusRes.status === 'failed') {
          transforming.value = false
          transformProgress.value = 0
          ElMessage.error('AI 改写失败：' + (statusRes.message || '未知错误'))
          return
        }
        // 任务已成功：拉一次草稿并应用
        if (statusRes.status === 'success') {
          const res = await getDraft(draftId.value)
          if (res.current_version !== prevVersion || res.current_content !== prevContent) {
            await applyDraftUpdate(res)
            return
          }
        }

        // 未完成则继续查草稿是否已有更新
        const res = await getDraft(draftId.value)
        if (res.current_version !== prevVersion || res.current_content !== prevContent) {
          await applyDraftUpdate(res)
          return
        }
      } catch (error) {
        console.error('轮询出错:', error)
      }
      setTimeout(poll, POLL_INTERVAL)
    }
    setTimeout(poll, POLL_INTERVAL)
  } catch (error) {
    if (error !== 'cancel') {
      console.error('AI改写失败:', error)
      ElMessage.error('启动 AI 改写失败: ' + (error?.message || '未知错误'))
    } else {
      console.log('用户取消')
    }
    transforming.value = false
    transformProgress.value = 0
  }
}

// Word上传并应用
const handleWordUpload = async (file) => {
  if (!draftId.value) {
    ElMessage.warning('草稿尚未加载完成')
    return false
  }
  if (!file) return false
  const name = file.name || ''
  if (!name.toLowerCase().endsWith('.doc') && !name.toLowerCase().endsWith('.docx')) {
    ElMessage.warning('仅支持上传 .doc 或 .docx 文件')
    return false
  }

  if (hasUnsavedChanges.value) {
    try {
      await ElMessageBox.confirm(
        '当前有未保存的修改，上传Word将覆盖编辑内容。确定继续吗？',
        '提示',
        {
          confirmButtonText: '继续',
          cancelButtonText: '取消',
          type: 'warning'
        }
      )
    } catch {
      return false
    }
  }

  wordUploading.value = true
  try {
    const res = await uploadWordToDraft(draftId.value, file)
    if (res?.title && res.title !== '无标题') {
      articleTitle.value = res.title
    }
    const html = res?.content_html || ''
    if (!html) {
      ElMessage.error('解析失败：未生成有效内容')
      return false
    }

    editableContent.value = html
    editableHtml.value = html
    await nextTick()
    tiptapRef.value?.setHTML?.(html)
    hasUnsavedChanges.value = true

    await handleSave(false)
    ElMessage.success('Word已解析并应用到编辑器')
  } catch (error) {
    ElMessage.error('Word解析失败: ' + (error?.message || '未知错误'))
  } finally {
    wordUploading.value = false
  }
  return false
}

// 图片上传并插入编辑器（base64，保存时自动上传OSS）
const handleImageUpload = async (file) => {
  if (!file) return false
  if (!file.type || !file.type.startsWith('image/')) {
    ElMessage.warning('仅支持图片文件')
    return false
  }

  const reader = new FileReader()
  reader.onload = async (e) => {
    const base64 = e.target?.result
    if (!base64) {
      ElMessage.error('图片读取失败')
      return
    }

    if (showSourceCode.value) {
      const imgTag = `<img src="${base64}" style="max-width:100%; height:auto;" />`
      editableHtml.value = `${editableHtml.value || ''}\n${imgTag}\n`
      handleContentChange()
    } else {
      tiptapRef.value?.editor?.chain().focus().setImage({ src: base64 }).run()
      handleContentChange()
    }

    await nextTick()
    await handleSave(false)
    ElMessage.success('图片已插入并保存')
  }
  reader.onerror = () => {
    ElMessage.error('图片读取失败')
  }
  reader.readAsDataURL(file)

  return false
}

// 恢复AI版本
const handleRestoreAI = async () => {
  try {
    await ElMessageBox.confirm(
      '确定要恢复到AI转换的原始版本吗？这将丢弃所有手动修改。',
      '提示',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    const response = await restoreAIVersion(draftId.value)
    editableContent.value = response.current_content
    editableHtml.value = markdownToHtml(response.current_content)
    currentVersion.value = response.current_version
    hasUnsavedChanges.value = false
    tiptapRef.value?.setHTML?.(editableHtml.value)
    ElMessage.success('已恢复到AI原始版本')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('恢复失败: ' + (error.message || '未知错误'))
    }
  }
}

// 获取来源图标
const normalizeContentSource = (source) => {
  return String(source || '').trim().toLowerCase().replace(/[\s-]+/g, '_')
}

// 来源 SVG 图标路径
const _base = import.meta.env.BASE_URL
const SOURCE_ICONS = {
  weixin:    _base + 'icons/weixin.svg',
  meipian:   _base + 'icons/meipian.svg',
  doc:       _base + 'icons/WORD.svg',
  docx:      _base + 'icons/WORD.svg',
  video:     _base + 'icons/mp4.svg',
  archive:   _base + 'icons/archive.svg',
  other_url: _base + 'icons/web.svg',
  large_attachment: _base + 'icons/large-attachment.svg',
  text:      _base + 'icons/text.svg',
}
const getSourceIconUrl = (source) => SOURCE_ICONS[normalizeContentSource(source)] || (_base + 'icons/text.svg')

// 获取来源标签
const getSourceLabel = (source) => {
  const labels = {
    weixin:    '微信公众号',
    meipian:   '美篇',
    doc:       'Word文档',
    docx:      'Word文档',
    video:     '视频',
    archive:   '压缩包',
    other_url: '其他链接',
    large_attachment: '超大附件',
    text:      '文本',
  }
  return labels[normalizeContentSource(source)] || '未知'
}

// 获取标签颜色类型
const getSourceTagType = (source) => {
  const types = {
    weixin:    'success',
    meipian:   'warning',
    doc:       'primary',
    docx:      'primary',
    video:     'danger',
    archive:   'warning',
    other_url: 'info',
    text:      'info',
  }
  return types[normalizeContentSource(source)] || 'info'
}

const mp4IconUrl = _base + 'icons/mp4.svg'
const archiveIconUrl = _base + 'icons/archive.svg'
const webIconUrl = _base + 'icons/web.svg'

const getAttachmentTypeLabel = (type) => {
  const labels = {
    image: '图片',
    video: '视频',
    word: 'Word',
    archive: '压缩包',
    other: '附件'
  }
  return labels[String(type || '').toLowerCase()] || '附件'
}

const formatFileSize = (size) => {
  if (!size || Number.isNaN(size)) return '-'
  const bytes = Number(size)
  if (bytes < 1024) return `${bytes} B`
  const kb = bytes / 1024
  if (kb < 1024) return `${kb.toFixed(1)} KB`
  const mb = kb / 1024
  if (mb < 1024) return `${mb.toFixed(1)} MB`
  const gb = mb / 1024
  return `${gb.toFixed(1)} GB`
}

const getCooperationLabel = (type) => {
  const labels = {
    free: '免费投稿',
    partner: '合作客户',
  }
  return labels[String(type || '').trim()] || '-'
}

const getMediaTypeLabel = (type) => {
  const labels = {
    rongyao: '荣耀网',
    shidai: '时代网',
    zhengxian: '争先网',
    zhengqi: '政企网',
    toutiao: '今日头条',
  }
  return labels[String(type || '').trim()] || '-'
}

// 发布相关
const publishDialogVisible = ref(false)
const publishLoading = ref(false)
const selectedSiteId = ref(null)
const targetSiteId = ref(null)  // 邮件解析的目标站点ID
const wordpressSites = ref([])
const publishHistory = ref([])

// 加载发布历史
const loadPublishHistory = async () => {
  try {
    const token = localStorage.getItem('access_token')
    const response = await fetch(`/api/drafts/${draftId.value}/publish-history`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })
    if (response.ok) {
      publishHistory.value = await response.json()
    }
  } catch (error) {
    console.error('加载发布历史失败:', error)
  }
}

// 加载WordPress站点列表
const loadWordPressSites = async () => {
  try {
    const token = localStorage.getItem('access_token')
    const response = await fetch('/api/wordpress-sites?active_only=true', {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })
    if (response.ok) {
      const data = await response.json()
      wordpressSites.value = data.sites || []
    } else {
      console.error('加载站点失败:', response.status, await response.text())
    }
  } catch (error) {
    console.error('加载站点列表失败:', error)
  }
}

// 打开发布对话框
const handlePublish = async () => {
  if (hasUnsavedChanges.value) {
    ElMessage.warning('请先保存修改再发布')
    return
  }
  
  await loadWordPressSites()
  await loadPublishHistory()
  
  if (wordpressSites.value.length === 0) {
    ElMessage.error('没有可用的WordPress站点，请先配置站点')
    return
  }
  
  // 默认选中目标站点（如果存在）
  console.log('目标站点ID:', targetSiteId.value)
  console.log('可用站点:', wordpressSites.value.map(s => ({ id: s.id, name: s.name })))
  
  if (targetSiteId.value) {
    const targetSite = wordpressSites.value.find(site => site.id === targetSiteId.value)
    if (targetSite) {
      selectedSiteId.value = targetSiteId.value
      console.log('已自动选中目标站点:', targetSite.name)
      ElMessage.info(`已自动选中目标站点：${targetSite.name}`)
    } else {
      selectedSiteId.value = null
      console.log('目标站点未配置，站点ID:', targetSiteId.value)
      ElMessage.warning('邮件指定的目标站点尚未配置，请手动选择发布站点')
    }
  } else {
    selectedSiteId.value = null
    console.log('未指定目标站点')
  }
  
  publishDialogVisible.value = true
}

// 确认发布
const confirmPublish = async () => {
  if (!selectedSiteId.value) {
    ElMessage.warning('请选择发布站点')
    return
  }
  
  publishLoading.value = true
  
  try {
    const token = localStorage.getItem('access_token')
    const response = await fetch(`/api/drafts/${draftId.value}/publish`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        site_id: selectedSiteId.value
      })
    })
    
    const result = await response.json()
    
    if (result.success) {
      ElMessage.success(`${result.message}，文章ID: ${result.wordpress_post_id}`)
      publishDialogVisible.value = false
      selectedSiteId.value = null
      // 重新加载草稿和发布历史
      await loadDraft()
      await loadPublishHistory()
    } else {
      // 如果是已发布的提示，使用info样式
      if (result.message && result.message.includes('已发布')) {
        ElMessage.info(result.message)
      } else {
        ElMessage.error(result.message || '发布失败')
      }
      // 即使失败也重新加载历史（记录了失败）
      await loadPublishHistory()
    }
  } catch (error) {
    ElMessage.error('发布失败: ' + error.message)
  } finally {
    publishLoading.value = false
  }
}

// 格式化日期
const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    timeZone: 'Asia/Shanghai'
  })
}

const formatDateTime = formatDate

// 页面离开前提示
const handleBeforeUnload = (e) => {
  if (hasUnsavedChanges.value) {
    e.preventDefault()
    e.returnValue = ''
  }
}

onMounted(() => {
  loadDraft()
  window.addEventListener('beforeunload', handleBeforeUnload)
})

onBeforeUnmount(() => {
  if (autoSaveTimer) {
    clearTimeout(autoSaveTimer)
  }
  window.removeEventListener('beforeunload', handleBeforeUnload)
})
</script>

<style scoped>
.audit-container {
  padding: 20px;
  height: calc(100vh - 40px);
  display: flex;
  flex-direction: column;
}

.header-card {
  margin-bottom: 20px;
  flex-shrink: 0;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 15px;
}

.header-meta {
  margin-left: 4px;
  display: flex;
  gap: 16px;
  color: #606266;
  font-size: 13px;
  white-space: nowrap;
}

.header-left h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.header-right {
  display: flex;
  gap: 10px;
}

.attachments-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.attachment-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  background: #fff;
}

.attachment-icon {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f7fa;
  border-radius: 6px;
  color: #606266;
}

.attachment-icon img {
  width: 20px;
  height: 20px;
}

.attachment-info {
  flex: 1;
  min-width: 0;
}

.attachment-name {
  font-size: 13px;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.attachment-meta {
  font-size: 12px;
  color: #909399;
  margin-top: 2px;
}

.attachment-actions a {
  font-size: 12px;
  color: #409eff;
  text-decoration: none;
}

.content-card {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

/* el-card 内部 body 也要铺满 */
.content-card :deep(.el-card__body) {
  height: 100%;
  padding: 15px;
  box-sizing: border-box;
}

.three-pane-container {
  display: flex;
  height: 100%;
  gap: 10px;
}

.pane {
  display: flex;
  flex-direction: column;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  overflow: hidden;
  min-height: 0;
}

.left-pane {
  flex: 1;
}

.middle-pane {
  flex: 1;
  min-width: 0;
}

.sidebar {
  width: 300px;
  display: flex;
  flex-direction: column;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  overflow: hidden;
  flex-shrink: 0;
}

.pane-header,
.sidebar-header {
  padding: 12px 15px;
  background-color: #f5f7fa;
  border-bottom: 1px solid #dcdfe6;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
}

.pane-header h3,
.sidebar-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.pane-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.version-info {
  font-size: 14px;
  color: #606266;
}

.pane-content {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 0;
}

.sidebar-content {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 10px;
}

/* 中间编辑器区域：Tiptap 铺满 */
.middle-editor-wrap,
.left-content-wrap {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: relative;
}

/* 文章标题区域 */
.article-title-section {
  padding: 15px;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  flex-shrink: 0;
}

/* 只读标题 */
.article-title-readonly {
  font-size: 24px;
  font-weight: 600;
  color: #303133;
  padding: 12px 15px;
  background: #f5f7fa;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  min-height: 56px;
  line-height: 1.5;
}

/* 可编辑标题 */
.article-title-input :deep(.el-input__wrapper) {
  font-size: 24px;
  font-weight: 600;
  padding: 12px 15px;
  box-shadow: none;
  border: 1px solid transparent;
  transition: all 0.3s;
}

.article-title-input :deep(.el-input__wrapper:hover) {
  border-color: #c0c4cc;
}

.article-title-input :deep(.el-input__wrapper.is-focus) {
  border-color: #409eff;
  box-shadow: 0 0 0 1px #409eff inset;
}

.article-title-input :deep(.el-input__inner) {
  font-size: 24px;
  font-weight: 600;
  color: #303133;
}

/* 原文预览 */
.html-preview-iframe {
  display: block;
  width: 100%;
  height: 100%;
  min-height: 400px;
  border: none;
  background: #fff;
}

.html-preview-empty {
  padding: 24px;
  color: #909399;
  text-align: center;
}

/* AI改写进度条 */
.transform-progress {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 400px;
  max-width: 80%;
  z-index: 1000;
  background: white;
  padding: 30px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

.progress-text {
  font-size: 14px;
  font-weight: 500;
  color: #409eff;
}

.progress-tip {
  margin-top: 15px;
  text-align: center;
  font-size: 13px;
  color: #606266;
}

/* 源码编辑器 */
.source-code-editor {
  font-family: 'Courier New', Consolas, monospace;
  font-size: 13px;
  height: 100%;
}

.source-code-editor :deep(textarea) {
  font-family: 'Courier New', Consolas, monospace;
  line-height: 1.6;
  height: 100% !important;
  resize: none;
}
</style>
