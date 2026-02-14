<template>
  <div class="submissions-container">
    <el-card class="header-card">
      <div class="header-content">
        <h2>投稿列表</h2>
        <div class="header-actions">
          <el-input
            v-model="searchKeyword"
            placeholder="搜索投稿内容..."
            style="width: 300px; margin-right: 10px"
            clearable
            @clear="handleSearch"
            @keyup.enter="handleSearch"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
          <el-select
            v-model="statusFilter"
            placeholder="状态筛选"
            style="width: 150px; margin-right: 10px"
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
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="email_subject" label="邮件主题" min-width="200" />
        <el-table-column prop="email_from" label="发件人" width="200" />
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="图片数量" width="100">
          <template #default="{ row }">
            {{ row.images?.length || 0 }}
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="row.status === 'completed'"
              type="primary"
              size="small"
              @click.stop="handleViewDraft(row)"
            >
              查看草稿
            </el-button>
            <el-button
              v-else-if="row.status === 'pending'"
              type="success"
              size="small"
              @click.stop="handleTransform(row)"
            >
              开始转换
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
        <div class="content-preview">
          {{ currentSubmission.original_content }}
        </div>

        <el-divider v-if="currentSubmission.images?.length > 0">图片列表</el-divider>
        <div v-if="currentSubmission.images?.length > 0" class="images-grid">
          <el-image
            v-for="img in currentSubmission.images"
            :key="img.id"
            :src="img.oss_url"
            :preview-src-list="currentSubmission.images.map(i => i.oss_url)"
            fit="cover"
            class="image-item"
          />
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
import { Search, Refresh } from '@element-plus/icons-vue'
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

// 详情对话框
const detailDialogVisible = ref(false)
const currentSubmission = ref(null)

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

    const response = await getSubmissions(params)
    submissions.value = response.items
    total.value = response.total
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
