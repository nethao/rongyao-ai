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
          <el-button @click="handleShowVersions">
            <el-icon><Clock /></el-icon>
            版本历史
          </el-button>
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

    <el-card v-loading="loading" class="content-card">
      <div class="dual-pane-container">
        <!-- 左栏：原文 -->
        <div class="pane left-pane">
          <div class="pane-header">
            <h3>原始内容</h3>
            <el-tag type="info">只读</el-tag>
          </div>
          <div class="pane-content">
            <div class="content-display" v-html="formattedOriginalContent"></div>
          </div>
        </div>

        <!-- 分隔线 -->
        <div class="divider"></div>

        <!-- 右栏：AI转换内容（可编辑） -->
        <div class="pane right-pane">
          <div class="pane-header">
            <h3>AI转换内容</h3>
            <div class="pane-actions">
              <el-tag v-if="hasUnsavedChanges" type="warning">未保存</el-tag>
              <el-tag v-else type="success">已保存</el-tag>
              <span class="version-info">版本 {{ currentVersion }}</span>
            </div>
          </div>
          <div class="pane-content">
            <el-input
              v-model="editableContent"
              type="textarea"
              :autosize="{ minRows: 20, maxRows: 50 }"
              placeholder="AI转换后的内容..."
              @input="handleContentChange"
            />
          </div>
        </div>
      </div>
    </el-card>

    <!-- 版本历史对话框 -->
    <el-dialog
      v-model="versionsDialogVisible"
      title="版本历史"
      width="60%"
      :close-on-click-modal="false"
    >
      <el-table
        v-loading="loadingVersions"
        :data="versions"
        style="width: 100%"
        @row-click="handleVersionClick"
      >
        <el-table-column prop="version_number" label="版本号" width="100" />
        <el-table-column label="内容预览" min-width="300">
          <template #default="{ row }">
            <div class="version-preview">
              {{ row.content.substring(0, 100) }}...
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button
              type="primary"
              size="small"
              @click.stop="handleRestoreVersion(row)"
            >
              恢复
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>

    <!-- 版本详情对话框 -->
    <el-dialog
      v-model="versionDetailVisible"
      title="版本详情"
      width="70%"
      :close-on-click-modal="false"
    >
      <div v-if="selectedVersion" class="version-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="版本号">
            {{ selectedVersion.version_number }}
          </el-descriptions-item>
          <el-descriptions-item label="创建时间">
            {{ formatDate(selectedVersion.created_at) }}
          </el-descriptions-item>
        </el-descriptions>
        <el-divider>内容</el-divider>
        <div class="content-display">
          {{ selectedVersion.content }}
        </div>
      </div>
      <template #footer>
        <el-button @click="versionDetailVisible = false">关闭</el-button>
        <el-button type="primary" @click="handleRestoreVersion(selectedVersion)">
          恢复此版本
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ArrowLeft,
  Clock,
  RefreshLeft,
  Check,
  Upload
} from '@element-plus/icons-vue'
import { getDraft, updateDraft, getDraftVersions, restoreVersion, restoreAIVersion } from '../api/draft'
import { computeDiff } from '../utils/diff'

const router = useRouter()
const route = useRoute()

// 数据
const loading = ref(false)
const saving = ref(false)
const draftId = ref(null)
const originalContent = ref('')
const editableContent = ref('')
const currentVersion = ref(1)
const hasUnsavedChanges = ref(false)

// 版本历史
const versionsDialogVisible = ref(false)
const versionDetailVisible = ref(false)
const loadingVersions = ref(false)
const versions = ref([])
const selectedVersion = ref(null)

// 自动保存定时器
let autoSaveTimer = null

// 格式化原文（高亮差异）
const formattedOriginalContent = computed(() => {
  if (!originalContent.value) return ''
  
  // 简单处理：保留换行和空格
  return originalContent.value
    .replace(/\n/g, '<br>')
    .replace(/ /g, '&nbsp;')
})

// 加载草稿数据
const loadDraft = async () => {
  loading.value = true
  try {
    // 从路由参数获取draft_id或submission_id
    const id = route.params.draftId || route.params.submissionId
    
    if (!id) {
      ElMessage.error('缺少草稿ID')
      router.push({ name: 'submissions' })
      return
    }

    // 这里简化处理，假设传入的是draft_id
    // 实际应用中可能需要先通过submission_id查询draft_id
    draftId.value = parseInt(id)
    
    const response = await getDraft(draftId.value)
    originalContent.value = response.original_content
    editableContent.value = response.current_content
    currentVersion.value = response.current_version
    hasUnsavedChanges.value = false
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
  
  // 重置自动保存定时器
  if (autoSaveTimer) {
    clearTimeout(autoSaveTimer)
  }
  
  // 3秒后自动保存
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

  saving.value = true
  try {
    const response = await updateDraft(draftId.value, editableContent.value)
    currentVersion.value = response.current_version
    hasUnsavedChanges.value = false
    
    if (!isAutoSave) {
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

// 显示版本历史
const handleShowVersions = async () => {
  loadingVersions.value = true
  versionsDialogVisible.value = true
  
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
const handleVersionClick = (row) => {
  selectedVersion.value = row
  versionDetailVisible.value = true
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
    
    ElMessage.success('版本恢复成功')
    versionsDialogVisible.value = false
    versionDetailVisible.value = false
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('恢复版本失败: ' + (error.message || '未知错误'))
    }
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
    currentVersion.value = response.current_version
    hasUnsavedChanges.value = false
    
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

// 初始化
onMounted(() => {
  loadDraft()
  window.addEventListener('beforeunload', handleBeforeUnload)
})

// 清理
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
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.dual-pane-container {
  display: flex;
  height: 100%;
  gap: 20px;
}

.pane {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.pane-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 15px;
  border-bottom: 2px solid #e4e7ed;
  margin-bottom: 15px;
}

.pane-header h3 {
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
  color: #909399;
}

.pane-content {
  flex: 1;
  overflow-y: auto;
}

.content-display {
  padding: 15px;
  background-color: #f5f7fa;
  border-radius: 4px;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.8;
  font-size: 14px;
}

.divider {
  width: 2px;
  background-color: #dcdfe6;
  flex-shrink: 0;
}

.left-pane .content-display {
  background-color: #fef0f0;
  border: 1px solid #fde2e2;
}

:deep(.el-textarea__inner) {
  font-family: inherit;
  line-height: 1.8;
  font-size: 14px;
}

.version-preview {
  color: #606266;
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.version-detail .content-display {
  max-height: 400px;
  overflow-y: auto;
}

:deep(.el-table__row) {
  cursor: pointer;
}

:deep(.el-table__row:hover) {
  background-color: #f5f7fa;
}

/* 差异高亮样式 */
:deep(.diff-insert) {
  background-color: #d4edda;
  color: #155724;
}

:deep(.diff-delete) {
  background-color: #f8d7da;
  color: #721c24;
  text-decoration: line-through;
}
</style>
