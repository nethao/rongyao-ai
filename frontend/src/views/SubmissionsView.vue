<template>
  <div class="submissions-container">
    <el-card class="header-card">
      <div class="header-content">
        <h2>投稿列表</h2>
        <div class="header-actions">
          <el-input
            v-model="searchKeyword"
            placeholder="搜索投稿内容..."
            style="width: 200px; margin-right: 10px"
            clearable
            @clear="handleSearch"
            @keyup.enter="handleSearch"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
          <el-select
            v-model="editorFilter"
            placeholder="采编筛选"
            style="width: 150px; margin-right: 10px"
            clearable
            @change="handleSearch"
          >
            <el-option
              v-for="editor in editorList"
              :key="editor"
              :label="editor"
              :value="editor"
            />
          </el-select>
          <el-select
            v-model="cooperationFilter"
            placeholder="合作方式"
            style="width: 120px; margin-right: 10px"
            clearable
            @change="handleSearch"
          >
            <el-option label="投稿" value="free" />
            <el-option label="合作" value="partner" />
          </el-select>
          <el-select
            v-model="mediaFilter"
            placeholder="媒体筛选"
            style="width: 130px; margin-right: 10px"
            clearable
            @change="handleSearch"
          >
            <el-option label="荣耀网" value="rongyao" />
            <el-option label="时代网" value="shidai" />
            <el-option label="争先网" value="zhengxian" />
            <el-option label="政企网" value="zhengqi" />
            <el-option label="今日头条" value="toutiao" />
          </el-select>
          <el-select
            v-model="unitFilter"
            placeholder="来稿单位"
            style="width: 150px; margin-right: 10px"
            clearable
            filterable
            @change="handleSearch"
          >
            <el-option
              v-for="unit in unitList"
              :key="unit"
              :label="unit"
              :value="unit"
            />
          </el-select>
          <el-select
            v-model="statusFilter"
            placeholder="状态筛选"
            style="width: 120px; margin-right: 10px"
            clearable
            @change="handleSearch"
          >
            <el-option label="待处理" value="pending" />
            <el-option label="处理中" value="processing" />
            <el-option label="已完成" value="completed" />
            <el-option label="失败" value="failed" />
          </el-select>
          <el-button type="primary" @click="handleRefresh">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </div>
      </div>
    </el-card>

    <el-card class="table-card">
      <el-table
        v-loading="loading"
        :data="submissions"
        style="width: 100%"
        @row-click="handleRowClick"
      >
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="email_from" label="采编" width="150">
          <template #default="{ row }">
            {{ row.email_from?.split('@')[0] || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="合作方式" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.cooperation_type === 'free'" type="info" size="small">投稿</el-tag>
            <el-tag v-else-if="row.cooperation_type === 'partner'" type="success" size="small">合作</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="媒体" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.media_type" size="small">{{ getMediaName(row.media_type) }}</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="source_unit" label="来稿单位" width="150" show-overflow-tooltip />
        <el-table-column prop="email_subject" label="标题" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <div style="display: flex; align-items: center; gap: 6px;">
              <!-- 来源图标 -->
              <img v-if="row.content_source === 'weixin'" src="/icons/weixin.svg" alt="微信公众号" title="微信公众号" style="width: 18px; height: 18px;" />
              <img v-else-if="row.content_source === 'meipian'" src="/icons/meipian.svg" alt="美篇" title="美篇" style="width: 18px; height: 18px;" />
              <img v-else-if="row.content_source === 'doc' || row.content_source === 'docx'" src="/icons/WORD.svg" alt="Word文档" title="Word文档" style="width: 18px; height: 18px;" />
              <img v-else-if="row.content_source === 'text'" src="/icons/text.svg" alt="纯文本" title="纯文本" style="width: 18px; height: 18px;" />
              <span>{{ row.email_subject }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="附件" width="100" align="center">
          <template #default="{ row }">
            <div style="display: flex; gap: 8px; justify-content: center; align-items: center;">
              <!-- 图片 -->
              <el-badge 
                v-if="getImageCount(row) > 0" 
                :value="getImageCount(row)" 
                :max="99"
                type="primary"
              >
                <el-icon :size="20" color="#409EFF"><Picture /></el-icon>
              </el-badge>
              <!-- 视频 -->
              <el-badge 
                v-if="getVideoCount(row) > 0" 
                :value="getVideoCount(row)" 
                :max="99"
                type="warning"
              >
                <el-icon :size="20" color="#E6A23C"><VideoCamera /></el-icon>
              </el-badge>
              <!-- Word文档 -->
              <el-icon 
                v-if="row.docx_file_path || row.doc_file_path" 
                :size="20" 
                color="#67C23A"
              >
                <Document />
              </el-icon>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="160">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <!-- 有草稿：查看草稿 + AI转换 -->
            <template v-if="row.drafts && row.drafts.length > 0">
              <el-button
                type="primary"
                size="small"
                @click.stop="handleViewDraft(row)"
              >
                查看草稿
              </el-button>
              <el-button
                type="success"
                size="small"
                @click.stop="handleTransform(row)"
              >
                AI转换
              </el-button>
            </template>
            <!-- 无草稿：仅AI转换 -->
            <el-button
              v-else
              type="success"
              size="small"
              @click.stop="handleTransform(row)"
            >
              AI转换
            </el-button>
            <el-button
              type="info"
              size="small"
              @click.stop="handleViewDetail(row)"
            >
              详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-container">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </el-card>

    <!-- 详情对话框 -->
    <el-dialog
      v-model="detailDialogVisible"
      title="投稿详情"
      width="70%"
      :close-on-click-modal="false"
    >
      <div v-if="currentSubmission" class="detail-content">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="ID">
            {{ currentSubmission.id }}
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusType(currentSubmission.status)">
              {{ getStatusText(currentSubmission.status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="邮件主题">
            {{ currentSubmission.email_subject }}
          </el-descriptions-item>
          <el-descriptions-item label="发件人">
            {{ currentSubmission.email_from }}
          </el-descriptions-item>
          <el-descriptions-item label="创建时间">
            {{ formatDate(currentSubmission.created_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="更新时间">
            {{ formatDate(currentSubmission.updated_at) }}
          </el-descriptions-item>
        </el-descriptions>

        <el-divider>原始内容</el-divider>
        <div class="content-preview" v-html="formatContent(currentSubmission.original_content)"></div>

        <!-- 图片列表 -->
        <el-divider v-if="getImageList(currentSubmission).length > 0">图片列表</el-divider>
        <div v-if="getImageList(currentSubmission).length > 0" class="images-grid">
          <el-image
            v-for="img in getImageList(currentSubmission)"
            :key="img.id"
            :src="img.oss_url"
            :preview-src-list="getImageList(currentSubmission).map(i => i.oss_url)"
            fit="cover"
            class="image-item"
          />
        </div>

        <!-- 视频列表 -->
        <el-divider v-if="getVideoList(currentSubmission).length > 0">视频列表</el-divider>
        <div v-if="getVideoList(currentSubmission).length > 0" class="videos-grid">
          <div v-for="video in getVideoList(currentSubmission)" :key="video.id" class="video-item">
            <video 
              :src="video.oss_url" 
              controls 
              style="width: 100%; max-height: 400px;"
            >
              您的浏览器不支持视频播放
            </video>
            <div class="video-name">{{ video.original_filename }}</div>
          </div>
        </div>

        <div v-if="currentSubmission.error_message" class="error-message">
          <el-alert
            title="错误信息"
            type="error"
            :description="currentSubmission.error_message"
            :closable="false"
          />
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Refresh, Picture, VideoCamera, Document } from '@element-plus/icons-vue'
import { getSubmissions, triggerTransform } from '../api/submission'

const router = useRouter()

// 数据
const loading = ref(false)
const submissions = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const searchKeyword = ref('')
const statusFilter = ref('')
const editorFilter = ref('')
const cooperationFilter = ref('')
const mediaFilter = ref('')
const unitFilter = ref('')

// 筛选选项列表
const editorList = ref([])
const unitList = ref([])

// 详情对话框
const detailDialogVisible = ref(false)
const currentSubmission = ref(null)

// 媒体名称映射
const getMediaName = (mediaType) => {
  const mediaMap = {
    'rongyao': '荣耀网',
    'shidai': '时代网',
    'zhengxian': '争先网',
    'zhengqi': '政企网',
    'toutiao': '今日头条'
  }
  return mediaMap[mediaType] || mediaType
}

// 获取图片数量（排除视频）
const getImageCount = (row) => {
  if (!row.images || row.images.length === 0) return 0
  return row.images.filter(img => {
    const filename = img.original_filename || ''
    return !filename.match(/\.(mp4|avi|mov|wmv|flv|mkv)$/i)
  }).length
}

// 获取视频数量
const getVideoCount = (row) => {
  if (!row.images || row.images.length === 0) return 0
  return row.images.filter(img => {
    const filename = img.original_filename || ''
    return filename.match(/\.(mp4|avi|mov|wmv|flv|mkv)$/i)
  }).length
}

// 获取图片列表（排除视频）
const getImageList = (submission) => {
  if (!submission.images || submission.images.length === 0) return []
  return submission.images.filter(img => {
    const filename = img.original_filename || ''
    return !filename.match(/\.(mp4|avi|mov|wmv|flv|mkv)$/i)
  })
}

// 获取视频列表
const getVideoList = (submission) => {
  if (!submission.images || submission.images.length === 0) return []
  return submission.images.filter(img => {
    const filename = img.original_filename || ''
    return filename.match(/\.(mp4|avi|mov|wmv|flv|mkv)$/i)
  })
}

// 格式化原始内容，将URL转为超链接
const formatContent = (content) => {
  if (!content) return ''
  // 匹配URL
  const urlRegex = /(https?:\/\/[^\s]+)/g
  return content.replace(urlRegex, '<a href="$1" target="_blank" style="color: #409eff; text-decoration: underline;">$1</a>')
}

// 提取筛选选项
const extractFilterOptions = (items) => {
  const editors = new Set()
  const units = new Set()
  
  items.forEach(item => {
    if (item.email_from) {
      const editor = item.email_from.split('@')[0]
      editors.add(editor)
    }
    if (item.source_unit) {
      units.add(item.source_unit)
    }
  })
  
  editorList.value = Array.from(editors).sort()
  unitList.value = Array.from(units).sort()
}

// 加载投稿列表
const loadSubmissions = async () => {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      size: pageSize.value
    }
    if (searchKeyword.value) {
      params.search = searchKeyword.value
    }
    if (statusFilter.value) {
      params.status = statusFilter.value
    }
    if (editorFilter.value) {
      params.editor = editorFilter.value
    }
    if (cooperationFilter.value) {
      params.cooperation = cooperationFilter.value
    }
    if (mediaFilter.value) {
      params.media = mediaFilter.value
    }
    if (unitFilter.value) {
      params.unit = unitFilter.value
    }

    const response = await getSubmissions(params)
    submissions.value = response.items
    total.value = response.total
    
    // 提取筛选选项
    extractFilterOptions(response.items)
  } catch (error) {
    ElMessage.error('加载投稿列表失败: ' + (error.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

// 搜索
const handleSearch = () => {
  currentPage.value = 1
  loadSubmissions()
}

// 刷新
const handleRefresh = () => {
  loadSubmissions()
}

// 分页变化
const handlePageChange = (page) => {
  currentPage.value = page
  loadSubmissions()
}

const handleSizeChange = (size) => {
  pageSize.value = size
  currentPage.value = 1
  loadSubmissions()
}

// 行点击
const handleRowClick = (row) => {
  handleViewDetail(row)
}

// 查看详情
const handleViewDetail = (row) => {
  currentSubmission.value = row
  detailDialogVisible.value = true
}

// 查看草稿
const handleViewDraft = (row) => {
  // 获取第一个草稿的ID
  if (row.drafts && row.drafts.length > 0) {
    const draftId = row.drafts[0].id
    router.push({ name: 'audit', params: { draftId } })
  } else {
    ElMessage.warning('该投稿还没有生成草稿')
  }
}

// 触发AI转换
const handleTransform = async (row) => {
  try {
    await ElMessageBox.confirm(
      '确定要开始AI转换吗？',
      '提示',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'info'
      }
    )

    const response = await triggerTransform(row.id)
    ElMessage.success(response.message || 'AI转换任务已启动')
    
    // 刷新列表
    setTimeout(() => {
      loadSubmissions()
    }, 1000)
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('启动转换失败: ' + (error.message || '未知错误'))
    }
  }
}

// 状态类型
const getStatusType = (status) => {
  const typeMap = {
    pending: 'info',
    processing: 'warning',
    completed: 'success',
    failed: 'danger'
  }
  return typeMap[status] || 'info'
}

// 状态文本
const getStatusText = (status) => {
  const textMap = {
    pending: '待处理',
    processing: '处理中',
    completed: '已完成',
    failed: '失败'
  }
  return textMap[status] || status
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
    minute: '2-digit'
  })
}

// 初始化
onMounted(() => {
  loadSubmissions()
})
</script>

<style scoped>
.submissions-container {
  padding: 20px;
}

.header-card {
  margin-bottom: 20px;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-content h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.header-actions {
  display: flex;
  align-items: center;
}

.table-card {
  min-height: 600px;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.detail-content {
  max-height: 70vh;
  overflow-y: auto;
}

.content-preview {
  padding: 15px;
  background-color: #f5f7fa;
  border-radius: 4px;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 300px;
  overflow-y: auto;
}

.images-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 10px;
}

.image-item {
  width: 100%;
  height: 150px;
  border-radius: 4px;
  cursor: pointer;
}

.videos-grid {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.video-item {
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  padding: 10px;
  background-color: #f5f7fa;
}

.video-name {
  margin-top: 10px;
  font-size: 14px;
  color: #606266;
  text-align: center;
}

.error-message {
  margin-top: 20px;
}

:deep(.el-table__row) {
  cursor: pointer;
}

:deep(.el-table__row:hover) {
  background-color: #f5f7fa;
}
</style>
