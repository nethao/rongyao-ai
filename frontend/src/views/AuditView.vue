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

    <el-card v-loading="loading" class="content-card">
      <div class="three-pane-container">
        <!-- 左栏：原文（HTML预览） -->
        <div class="pane left-pane">
          <div class="pane-header">
            <h3>原始内容</h3>
            <el-tag type="info">只读</el-tag>
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
              sandbox="allow-same-origin"
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
                :disabled="!submissionId"
                @click="handleAiTransform"
              >
                <el-icon><Edit /></el-icon>
                AI改写
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
            
            
            <TiptapEditor
              ref="tiptapRef"
              v-model="editableHtml"
              @change="handleContentChange"
            />
          </div>
        </div>

        <!-- 右侧边栏：修改历史 -->
        <div class="sidebar right-sidebar">
          <div class="sidebar-header">
            <h3>快照历史</h3>
            <el-button size="small" @click="createSnapshot('手动快照')">
              <el-icon><Check /></el-icon>
            </el-button>
          </div>
          <div class="sidebar-content">
            <div v-if="snapshots.length > 0" class="snapshots-list">
              <div
                v-for="snapshot in snapshots"
                :key="snapshot.id"
                class="snapshot-item"
                @click="handleSnapshotRestore(snapshot)"
              >
                <div class="snapshot-label">{{ snapshot.label }}</div>
                <div class="snapshot-time">{{ snapshot.timestamp }}</div>
              </div>
            </div>

            <el-divider>数据库版本</el-divider>
            <el-timeline v-if="versions.length > 0">
              <el-timeline-item
                v-for="version in versions"
                :key="version.id"
                :timestamp="formatDate(version.created_at)"
                placement="top"
              >
                <el-card
                  class="version-card"
                  :class="{ active: version.version_number === currentVersion }"
                  @click="handleVersionClick(version)"
                >
                  <div class="version-header">
                    <el-tag size="small">v{{ version.version_number }}</el-tag>
                    <el-tag v-if="version.version_number === 1" size="small" type="success">AI初版</el-tag>
                  </div>
                  <div class="version-preview">
                    {{ version.content.substring(0, 80) }}...
                  </div>
                  <el-button
                    v-if="version.version_number !== currentVersion"
                    size="small"
                    type="primary"
                    @click.stop="handleRestoreVersion(version)"
                  >
                    恢复此版本
                  </el-button>
                </el-card>
              </el-timeline-item>
            </el-timeline>
            <el-empty v-else description="暂无历史版本" />
          </div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ArrowLeft,
  RefreshLeft,
  Check,
  Upload,
  Edit
} from '@element-plus/icons-vue'
import { getDraft, updateDraft, getDraftVersions, restoreVersion, restoreAIVersion } from '../api/draft'
import { triggerTransform } from '../api/submission'
import { markdownToHtml, htmlToMarkdown } from '../utils/markdown'
import TiptapEditor from '../components/TiptapEditor.vue'

const router = useRouter()
const route = useRoute()

// 数据
const loading = ref(false)
const saving = ref(false)
const transforming = ref(false)
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

// 版本历史
const loadingVersions = ref(false)
const versions = ref([])

// 历史快照
const snapshots = ref([])

// 自动保存定时器
let autoSaveTimer = null

// 编辑器 ref
const tiptapRef = ref(null)

// 原文预览 iframe
const previewIframeRef = ref(null)

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
    originalContent.value = response.original_content
    editableContent.value = response.current_content
    currentVersion.value = response.current_version
    hasUnsavedChanges.value = false

    // 优先使用原始HTML，否则转换Markdown
    if (response.original_html) {
      originalHtml.value = response.original_html
    } else {
      originalHtml.value = markdownToHtml(originalContent.value)
    }
    editableHtml.value = markdownToHtml(editableContent.value)

    // 写入 iframe 以还原公众号排版
    if (response.original_html) {
      await nextTick()
      writePreviewIframe(originalHtml.value)
    }

    // 创建初始快照
    await nextTick()
    createSnapshot('初始版本')

    await loadVersions()
  } catch (error) {
    ElMessage.error('加载草稿失败: ' + (error.message || '未知错误'))
    router.push({ name: 'submissions' })
  } finally {
    loading.value = false
  }
}

// 创建快照
const createSnapshot = (label) => {
  const html = tiptapRef.value?.getHTML?.() || editableHtml.value
  if (!html) return

  snapshots.value.push({
    id: Date.now(),
    label: label || `修改 ${snapshots.value.length + 1}`,
    content: html,
    timestamp: new Date().toLocaleString('zh-CN')
  })
}

// 内容变化处理
const handleContentChange = () => {
  hasUnsavedChanges.value = true
  startAutoSave()
}

const handleTitleChange = () => {
  hasUnsavedChanges.value = true
  startAutoSave()
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

  const html = tiptapRef.value?.getHTML?.()
  if (!html) return

  saving.value = true
  try {
    const markdownContent = htmlToMarkdown(html)

    const response = await updateDraft(draftId.value, markdownContent)

    editableContent.value = markdownContent
    currentVersion.value = response.current_version
    hasUnsavedChanges.value = false

    if (!isAutoSave) {
      createSnapshot('手动保存')
      ElMessage.success('保存成功')
    }
  } catch (error) {
    ElMessage.error('保存失败: ' + (error.message || '未知错误'))
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

// 加载版本历史
const loadVersions = async () => {
  loadingVersions.value = true

  try {
    const response = await getDraftVersions(draftId.value)
    versions.value = response.versions
  } catch (error) {
    ElMessage.error('加载版本历史失败: ' + (error.message || '未知错误'))
  } finally {
    loadingVersions.value = false
  }
}

// 版本点击
const handleVersionClick = (version) => {
  const html = markdownToHtml(version.content)
  tiptapRef.value?.setHTML?.(html)
}

// 恢复版本
const handleRestoreVersion = async (version) => {
  try {
    await ElMessageBox.confirm(
      `确定要恢复到版本 ${version.version_number} 吗？`,
      '提示',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    const response = await restoreVersion(draftId.value, version.id)
    editableContent.value = response.current_content
    currentVersion.value = response.current_version
    hasUnsavedChanges.value = false

    const html = markdownToHtml(editableContent.value)
    tiptapRef.value?.setHTML?.(html)
    createSnapshot('恢复版本')

    await loadVersions()
    ElMessage.success('版本恢复成功')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('恢复版本失败: ' + (error.message || '未知错误'))
    }
  }
}

// 快照回滚
const handleSnapshotRestore = (snapshot) => {
  tiptapRef.value?.setHTML?.(snapshot.content)
  ElMessage.success('已回滚到: ' + snapshot.label)
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
    const poll = async () => {
      pollCount++
      const elapsed = Date.now() - startTime
      
      console.log(`轮询 #${pollCount}, 已耗时: ${Math.floor(elapsed/1000)}秒`)
      
      // 模拟进度
      if (elapsed < 30000) {
        transformProgress.value = Math.min(30, Math.floor(elapsed / 1000))
      } else if (elapsed < 90000) {
        transformProgress.value = Math.min(70, 30 + Math.floor((elapsed - 30000) / 1500))
      } else {
        transformProgress.value = Math.min(95, 70 + Math.floor((elapsed - 90000) / 3000))
      }
      
      if (elapsed > POLL_TIMEOUT) {
        console.error('❌ 超时！已等待:', Math.floor(elapsed/1000), '秒')
        transforming.value = false
        transformProgress.value = 0
        ElMessage.warning('等待超时，请手动刷新查看结果')
        return
      }
      
      try {
        console.log('步骤3: 获取草稿状态...')
        const res = await getDraft(draftId.value)
        console.log('草稿返回:', {
          version: res.current_version,
          contentLength: res.current_content?.length,
          versionChanged: res.current_version !== prevVersion,
          contentChanged: res.current_content !== prevContent
        })
        
        if (res.current_version !== prevVersion || res.current_content !== prevContent) {
          console.log('✅ 检测到内容变化！')
          transforming.value = false
          transformProgress.value = 100
          editableContent.value = res.current_content
          editableHtml.value = markdownToHtml(res.current_content)
          currentVersion.value = res.current_version
          hasUnsavedChanges.value = false
          
          console.log('步骤4: 更新编辑器...')
          tiptapRef.value?.setHTML?.(editableHtml.value)
          
          console.log('步骤5: 加载版本历史...')
          await loadVersions()
          
          setTimeout(() => {
            transformProgress.value = 0
            ElMessage.success('AI 改写已完成！图文排版已保留')
            console.log('=== AI改写完成 ===')
          }, 500)
          return
        } else {
          console.log('内容未变化，继续等待...')
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

// 发布
const handlePublish = () => {
  ElMessage.info('发布功能将在阶段6实现')
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
    second: '2-digit'
  })
}

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

.header-left h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.header-right {
  display: flex;
  gap: 10px;
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

/* 版本卡片 */
.version-card {
  cursor: pointer;
  margin-bottom: 10px;
  transition: all 0.3s;
}

.version-card:hover {
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.version-card.active {
  border-color: #409eff;
  background-color: #ecf5ff;
}

.version-header {
  display: flex;
  gap: 10px;
  margin-bottom: 10px;
}

.version-preview {
  font-size: 13px;
  color: #606266;
  margin-bottom: 10px;
  line-height: 1.5;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
}

/* 快照列表 */
.snapshots-list {
  margin-bottom: 10px;
}

.snapshot-item {
  padding: 10px;
  margin-bottom: 8px;
  background: #f5f7fa;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.3s;
}

.snapshot-item:hover {
  background: #e6f7ff;
  transform: translateX(-2px);
}

.snapshot-label {
  font-weight: 500;
  color: #303133;
  margin-bottom: 4px;
}

.snapshot-time {
  font-size: 12px;
  color: #909399;
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
</style>
