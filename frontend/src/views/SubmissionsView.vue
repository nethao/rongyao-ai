<template>
  <div class="submissions-container">
    <el-card class="header-card">
      <!-- 第一行：标题 + 三个主操作按钮，保证「手动发布」始终可见 -->
      <div class="header-row header-row-actions">
        <h2>投稿列表</h2>
        <div class="action-buttons">
          <el-button 
            v-if="selectedSubmissions.length > 0"
            type="danger" 
            @click="handleBatchDelete"
          >
            <el-icon><Delete /></el-icon>
            批量删除 ({{ selectedSubmissions.length }})
          </el-button>
          <el-button type="primary" @click="handleRefresh">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
          <el-button
            type="success"
            :loading="fetchingEmails"
            @click="handleFetchEmails"
          >
            <el-icon><Message /></el-icon>
            获取投稿
          </el-button>
          <el-button type="warning" @click="openManualCreateDialog">
            <el-icon><Edit /></el-icon>
            手动发稿
          </el-button>
        </div>
      </div>
      <!-- 第二行：筛选条件 -->
      <div class="header-row header-row-filters">
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          value-format="YYYY-MM-DD"
          clearable
          class="filter-date"
          @change="handleSearch"
        />
        <el-input
          v-model="searchKeyword"
          placeholder="搜索投稿内容..."
          class="filter-input"
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
          class="filter-select"
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
          class="filter-select"
          clearable
          @change="handleSearch"
        >
          <el-option label="投稿" value="free" />
          <el-option label="合作" value="partner" />
        </el-select>
        <el-select
          v-model="mediaFilter"
          placeholder="媒体筛选"
          class="filter-select"
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
          class="filter-select filter-select-unit"
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
          class="filter-select"
          clearable
          @change="handleSearch"
        >
          <el-option label="待处理" value="pending" />
          <el-option label="处理中" value="processing" />
          <el-option label="已完成" value="completed" />
          <el-option label="失败" value="failed" />
        </el-select>
      </div>
      <!-- 邮件抓取进度 -->
      <div v-if="emailFetchStatus" class="email-fetch-status" style="margin-top: 16px;">
        <el-alert
          :type="emailFetchStatus.status === 'success' ? 'success' : emailFetchStatus.status === 'failed' ? 'error' : 'info'"
          :closable="emailFetchStatus.status !== 'started'"
          @close="emailFetchStatus = null"
        >
          <template #title>
            <span style="font-weight: 600;">邮件抓取任务</span>
            <el-tag
              :type="emailFetchStatus.status === 'success' ? 'success' : emailFetchStatus.status === 'failed' ? 'danger' : 'warning'"
              size="small"
              style="margin-left: 8px;"
            >
              {{ emailFetchStatus.status === 'started' ? '进行中' : emailFetchStatus.status === 'success' ? '已完成' : '失败' }}
            </el-tag>
          </template>
          <div style="margin-top: 8px;">
            <div>{{ emailFetchStatus.message }}</div>
            <div v-if="emailFetchStatus.logs && emailFetchStatus.logs.length > 0" style="margin-top: 8px; font-size: 12px; color: #909399;">
              <div v-for="(log, idx) in emailFetchStatus.logs" :key="idx" style="margin-top: 4px;">
                {{ log.message }} ({{ formatTime(log.created_at) }})
              </div>
            </div>
          </div>
        </el-alert>
      </div>
    </el-card>

    <el-card class="table-card">
      <el-table
        v-loading="loading"
        :data="submissionsWithDateRows"
        row-key="id"
        style="width: 100%"
        @row-click="handleRowClick"
        @selection-change="handleSelectionChange"
        :row-class-name="getRowClassName"
        :span-method="spanMethod"
      >
        <el-table-column type="selection" width="55" :selectable="isRowSelectable" />
        <el-table-column prop="id" label="ID" width="70">
          <template #default="{ row }">
            <span v-if="row.isDateRow" style="font-size: 14px; color: #303133;">
              {{ row.dateDisplay }} - 共 {{ row.count }} 篇稿件
              <span class="date-row-tip">今日已统计结束</span>
            </span>
            <span v-else>{{ row.id }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="email_from" label="采编" min-width="220" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.email_from || '-' }}
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
              <img v-if="normalizeContentSource(row.content_source) === 'weixin'" src="/icons/weixin.svg" alt="微信公众号" title="微信公众号" style="width: 18px; height: 18px;" />
              <img v-else-if="normalizeContentSource(row.content_source) === 'meipian'" src="/icons/meipian.svg" alt="美篇" title="美篇" style="width: 18px; height: 18px;" />
              <img v-else-if="normalizeContentSource(row.content_source) === 'doc' || normalizeContentSource(row.content_source) === 'docx'" src="/icons/WORD.svg" alt="Word文档" title="Word文档" style="width: 18px; height: 18px;" />
              <img v-else-if="normalizeContentSource(row.content_source) === 'video'" :src="mp4IconUrl" alt="视频" title="视频" style="width: 18px; height: 18px;" />
              <img v-else-if="normalizeContentSource(row.content_source) === 'archive'" :src="archiveIconUrl" alt="压缩包" title="压缩包" style="width: 18px; height: 18px;" />
              <img v-else-if="normalizeContentSource(row.content_source) === 'large_attachment'" :src="largeAttachmentIconUrl" alt="超大附件" title="超大附件" style="width: 18px; height: 18px;" />
              <img v-else-if="normalizeContentSource(row.content_source) === 'other_url'" :src="webIconUrl" alt="其他链接" title="其他链接" style="width: 18px; height: 18px;" />
              <img v-else-if="normalizeContentSource(row.content_source) === 'text'" src="/icons/text.svg" alt="纯文本" title="纯文本" style="width: 18px; height: 18px;" />
              <span :style="needsManualEdit(row) && !hasPublished(row) ? 'font-weight: 600; color: #E6A23C;' : ''">{{ row.email_subject }}</span>
              <el-tag v-if="needsManualEdit(row) && !hasPublished(row)" type="info" size="small">待处理</el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusTypeByRow(row)" size="small">
              {{ getStatusTextByRow(row) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="附件" width="100" align="center">
          <template #default="{ row }">
            <div class="attachment-cell">
              <!-- 图片 -->
              <span v-if="getImageCount(row) > 0" class="attachment-badge-wrap">
                <el-badge 
                  :value="getImageCount(row)" 
                  :max="99"
                  type="primary"
                  class="attachment-badge"
                >
                  <el-icon :size="20" color="#409EFF"><Picture /></el-icon>
                </el-badge>
              </span>
              <!-- 视频 -->
              <span v-if="getVideoCount(row) > 0" class="attachment-badge-wrap">
                <el-badge 
                  :value="getVideoCount(row)" 
                  :max="99"
                  type="warning"
                  class="attachment-badge"
                >
                  <el-icon :size="20" color="#E6A23C"><VideoCamera /></el-icon>
                </el-badge>
              </span>
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
        <el-table-column prop="email_date" label="邮件时间" width="160" show-overflow-tooltip>
          <template #default="{ row }">
            {{ formatDate(row.email_date) }}
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="160">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="320" fixed="right">
          <template #default="{ row }">
            <div class="op-cell">
            <el-button
              v-if="!row.claimed_by_label"
              type="warning"
              size="small"
              @click.stop="handleClaim(row)"
            >
              认领
            </el-button>
            <span v-else class="claimed-badge">
              <el-icon class="claimed-icon"><User /></el-icon>
              {{ row.claimed_by_label }}
            </span>
            <!-- 有草稿：查看草稿 -->
            <el-button
              v-if="row.drafts && row.drafts.length > 0"
              type="primary"
              size="small"
              @click.stop="handleViewDraft(row)"
              :disabled="!row.can_edit"
            >
              查看草稿
            </el-button>
            <el-button type="info" size="small" @click.stop="handleViewDetail(row)">
              详情
            </el-button>
            <el-button
              type="danger"
              size="small"
              @click.stop="handleDelete(row)"
              :disabled="!row.can_edit"
            >
              删除
            </el-button>
            </div>
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
            <el-tag :type="getStatusTypeByRow(currentSubmission)">
              {{ getStatusTextByRow(currentSubmission) }}
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

    <!-- 手动发稿：公众号/美篇/Word 创建投稿 -->
    <el-dialog
      v-model="manualCreateDialogVisible"
      title="手动发稿"
      width="900px"
      :close-on-click-modal="false"
      @closed="resetManualCreateForm"
    >
      <!-- 第一步：选择类型并获取内容 -->
      <div v-if="manualCreateStep === 1">
        <el-form ref="previewFormRef" :model="manualCreateForm" :rules="previewRules" label-width="120px">
          <el-form-item label="文章类型" prop="article_type">
            <el-radio-group v-model="manualCreateForm.article_type" @change="handleArticleTypeChange">
              <el-radio value="weixin">公众号</el-radio>
              <el-radio value="meipian">美篇</el-radio>
              <el-radio value="other_url">其他链接</el-radio>
              <el-radio value="word">Word文档</el-radio>
            </el-radio-group>
          </el-form-item>
          
          <!-- 公众号、美篇、其他链接：链接输入 -->
          <el-form-item
            v-if="manualCreateForm.article_type === 'weixin' || manualCreateForm.article_type === 'meipian' || manualCreateForm.article_type === 'other_url'"
            label="文章链接"
            prop="article_url"
          >
            <el-input
              v-model="manualCreateForm.article_url"
              :placeholder="manualCreateForm.article_type === 'weixin' ? '请输入公众号文章链接' : manualCreateForm.article_type === 'meipian' ? '请输入美篇文章链接' : '请输入网页链接'"
              clearable
            />
          </el-form-item>
          
          <!-- Word文档：文件上传 -->
          <el-form-item 
            v-if="manualCreateForm.article_type === 'word'"
            label="Word文档" 
            prop="word_file"
          >
            <el-upload
              ref="wordUploadRef"
              :auto-upload="false"
              :limit="1"
              accept=".doc,.docx"
              :on-change="handleWordFileChange"
              :on-remove="handleWordFileRemove"
              :file-list="wordFileList"
            >
              <el-button type="primary">选择文件</el-button>
              <template #tip>
                <div class="el-upload__tip">支持 .doc 和 .docx 格式</div>
              </template>
            </el-upload>
          </el-form-item>
        </el-form>
      </div>
      
      <!-- 第二步：显示解析结果并填写信息 -->
      <div v-else-if="manualCreateStep === 2">
        <el-alert
          type="success"
          :closable="false"
          style="margin-bottom: 20px;"
        >
          <template #title>
            内容解析成功！请完善以下信息后创建投稿
          </template>
        </el-alert>
        
        <el-form ref="manualCreateFormRef" :model="manualCreateForm" :rules="manualCreateRules" label-width="120px">
          <el-form-item label="标题" prop="email_subject">
            <el-input 
              v-model="manualCreateForm.email_subject" 
              placeholder="标题（已自动提取，可修改）" 
            />
          </el-form-item>
          
          <!-- 内容预览 -->
          <el-form-item label="内容预览">
            <div class="manual-create-editor-wrapper" v-html="manualCreateForm.preview_html"></div>
            <div v-if="manualCreateForm.image_count > 0" style="margin-top: 8px; color: #909399; font-size: 12px;">
              检测到 {{ manualCreateForm.image_count }} 张图片（已上传）
            </div>
          </el-form-item>
          
          <el-form-item label="采编" prop="email_from">
            <el-input v-model="manualCreateForm.email_from" placeholder="请输入采编名称或邮箱" />
          </el-form-item>
          
          <el-form-item label="合作方式" prop="cooperation_type">
            <el-select v-model="manualCreateForm.cooperation_type" placeholder="请选择合作方式" clearable style="width: 100%">
              <el-option label="投稿" value="free" />
              <el-option label="合作" value="partner" />
            </el-select>
          </el-form-item>
          
          <el-form-item label="发布媒体" prop="media_type">
            <el-select v-model="manualCreateForm.media_type" placeholder="请选择发布媒体" clearable style="width: 100%">
              <el-option label="荣耀网" value="rongyao" />
              <el-option label="时代网" value="shidai" />
              <el-option label="争先网" value="zhengxian" />
              <el-option label="政企网" value="zhengqi" />
              <el-option label="今日头条" value="toutiao" />
            </el-select>
          </el-form-item>
          
          <el-form-item label="来稿单位" prop="source_unit">
            <el-input v-model="manualCreateForm.source_unit" placeholder="请输入来稿单位" />
          </el-form-item>
        </el-form>
      </div>
      
      <template #footer>
        <div v-if="manualCreateStep === 1">
          <el-button @click="manualCreateDialogVisible = false">取消</el-button>
          <el-button 
            type="primary" 
            :loading="manualCreatePreviewing" 
            @click="handlePreviewContent"
          >
            <span v-if="!manualCreatePreviewing">
              {{ manualCreateForm.article_type === 'word' ? '解析文档' : '获取内容' }}
            </span>
            <span v-else>
              {{ manualCreateForm.article_type === 'word' ? '解析中，请稍候...' : '获取中，正在抓取内容...' }}
            </span>
          </el-button>
        </div>
        <div v-else-if="manualCreateStep === 2">
          <el-button @click="manualCreateStep = 1">上一步</el-button>
          <el-button @click="manualCreateDialogVisible = false">取消</el-button>
          <el-button 
            type="primary" 
            :loading="manualCreateSubmitting" 
            @click="submitManualCreate"
          >
            创建投稿
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Refresh, Picture, VideoCamera, Document, Message, Edit, Delete, User } from '@element-plus/icons-vue'
import { getSubmissions, triggerTransform, deleteSubmission, createSubmission, previewContent, claimSubmission } from '../api/submission'
import { getUserInfo } from '../utils/auth'
import TiptapEditor from '../components/TiptapEditor.vue'
import { triggerFetchEmails, getFetchEmailsStatus } from '../api/monitoring'

const router = useRouter()

// 计算稿件所属日期：当日 14:01 至次日 14:00 归为「次日」的稿件
// 例：1月1日 14:01 ～ 1月2日 14:00 → 1月2日；1月2日 14:01 ～ 1月3日 14:00 → 1月3日
const getSubmissionDate = (createdAt) => {
  if (!createdAt) return null
  const d = new Date(createdAt)
  const dateOnly = new Date(d.getFullYear(), d.getMonth(), d.getDate())
  const cutoff = new Date(dateOnly)
  cutoff.setHours(14, 0, 0, 0)
  if (d <= cutoff) {
    return dateOnly.toISOString().split('T')[0]
  }
  dateOnly.setDate(dateOnly.getDate() + 1)
  return dateOnly.toISOString().split('T')[0]
}

// 格式化日期显示
const formatSubmissionDate = (dateStr) => {
  const date = new Date(dateStr)
  const today = new Date()
  const yesterday = new Date(today)
  yesterday.setDate(yesterday.getDate() - 1)
  
  const dateOnly = date.toISOString().split('T')[0]
  const todayStr = today.toISOString().split('T')[0]
  const yesterdayStr = yesterday.toISOString().split('T')[0]
  
  const weekDays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
  const weekDay = weekDays[date.getDay()]
  
  if (dateOnly === todayStr) {
    return `今天 ${date.getMonth() + 1}月${date.getDate()}日 ${weekDay}`
  } else if (dateOnly === yesterdayStr) {
    return `昨天 ${date.getMonth() + 1}月${date.getDate()}日 ${weekDay}`
  } else {
    return `${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日 ${weekDay}`
  }
}

// 将投稿列表按日期分组，并插入日期行
const submissionsWithDateRows = computed(() => {
  if (!submissions.value || submissions.value.length === 0) return []
  
  const grouped = {}
  
  // 按日期分组
  submissions.value.forEach(sub => {
    const dateKey = getSubmissionDate(sub.created_at)
    if (!dateKey) return
    
    if (!grouped[dateKey]) {
      grouped[dateKey] = []
    }
    grouped[dateKey].push(sub)
  })
  
  // 按日期排序（最新的在前）
  const sortedDates = Object.keys(grouped).sort((a, b) => b.localeCompare(a))
  
  // 构建带日期行的列表
  const result = []
  sortedDates.forEach(dateKey => {
    // 插入日期分隔行
    result.push({
      isDateRow: true,
      dateKey,
      dateDisplay: formatSubmissionDate(dateKey),
      count: grouped[dateKey].length,
      id: `date-${dateKey}` // 用于row-key
    })
    // 插入该日期的所有投稿
    result.push(...grouped[dateKey])
  })
  
  return result
})

// 判断行是否可选（日期行不可选）
const isRowSelectable = (row) => {
  return !row.isDateRow
}

// 设置行样式
const getRowClassName = ({ row }) => {
  if (row.isDateRow) {
    return 'date-row'
  }
  return ''
}

// 合并单元格（日期行合并所有列）
const spanMethod = ({ row, columnIndex }) => {
  if (row.isDateRow) {
    if (columnIndex === 1) { // 从第二列（ID列）开始合并
      return [1, 11] // 合并剩余11列（含邮件时间）
    } else if (columnIndex === 0) {
      return [1, 1] // 选择框列保持原样
    }
    return [0, 0]
  }
}
// 来源图标路径
const webIconUrl     = import.meta.env.BASE_URL + 'icons/web.svg'
const mp4IconUrl     = import.meta.env.BASE_URL + 'icons/mp4.svg'
const archiveIconUrl = import.meta.env.BASE_URL + 'icons/archive.svg'
const largeAttachmentIconUrl = import.meta.env.BASE_URL + 'icons/large-attachment.svg'
const normalizeContentSource = (source) => String(source || '').trim().toLowerCase().replace(/[\s-]+/g, '_')

// 判断是否需要人工编辑
const needsManualEdit = (row) => {
  const source = normalizeContentSource(row.content_source)
  return ['other_url', 'large_attachment', 'video', 'archive'].includes(source)
}

// 数据
const loading = ref(false)
const submissions = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const searchKeyword = ref('')
const dateRange = ref(null)
const statusFilter = ref('')
const editorFilter = ref('')
const cooperationFilter = ref('')
const mediaFilter = ref('')
const unitFilter = ref('')
const selectedSubmissions = ref([])

// 筛选选项列表
const editorList = ref([])
const unitList = ref([])

// 详情对话框
const detailDialogVisible = ref(false)
const currentSubmission = ref(null)

// 邮件抓取
const fetchingEmails = ref(false)
const emailFetchStatus = ref(null)
let emailFetchStatusTimer = null

// 管理员标识
const isAdmin = computed(() => {
  const user = JSON.parse(localStorage.getItem('user_info') || '{}')
  return user.role === 'admin'
})

// 手动创建投稿
const manualCreateDialogVisible = ref(false)
const manualCreateStep = ref(1) // 1: 预览步骤, 2: 填写信息步骤
const manualCreatePreviewing = ref(false)
const manualCreateSubmitting = ref(false)
const previewFormRef = ref(null)
const manualCreateFormRef = ref(null)
const wordUploadRef = ref(null)
const wordFileList = ref([])
const manualCreateForm = ref({
  article_type: 'weixin', // weixin, meipian, word
  article_url: '',
  word_file: null,
  email_subject: '',
  original_content: '',
  preview_html: '',
  original_html: null,
  content_source: '',
  image_count: 0,
  media_map: null,
  email_from: '',
  cooperation_type: '',
  media_type: '',
  source_unit: ''
})
const previewRules = {
  article_type: [{ required: true, message: '请选择文章类型', trigger: 'change' }],
  article_url: [
    { 
      validator: (rule, value, callback) => {
        const needsUrl = ['weixin', 'meipian', 'other_url'].includes(manualCreateForm.value.article_type)
        if (needsUrl) {
          if (!value || !value.trim()) {
            callback(new Error('请输入文章链接'))
          } else {
            callback()
          }
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ],
  word_file: [
    {
      validator: (rule, value, callback) => {
        if (manualCreateForm.value.article_type === 'word') {
          if (!manualCreateForm.value.word_file) {
            callback(new Error('请上传Word文档'))
          } else {
            callback()
          }
        } else {
          callback()
        }
      },
      trigger: 'change'
    }
  ]
}

const manualCreateRules = {
  email_subject: [{ required: true, message: '请输入标题', trigger: 'blur' }],
  email_from: [{ required: true, message: '请输入采编', trigger: 'blur' }],
  cooperation_type: [{ required: true, message: '请选择合作方式', trigger: 'change' }],
  media_type: [{ required: true, message: '请选择发布媒体', trigger: 'change' }],
  source_unit: [{ required: true, message: '请输入来稿单位', trigger: 'blur' }]
}

function openManualCreateDialog() {
  const user = JSON.parse(localStorage.getItem('user_info') || '{}')
  manualCreateStep.value = 1
  manualCreateForm.value = {
    article_type: 'weixin',
    article_url: '',
    word_file: null,
    email_subject: '',
    original_content: '',
    original_html: null,
    content_source: '',
    image_count: 0,
    email_from: user.username || '',
    cooperation_type: '',
    media_type: '',
    source_unit: ''
  }
  wordFileList.value = []
  manualCreateDialogVisible.value = true
}

function resetManualCreateForm() {
  manualCreateStep.value = 1
  manualCreateForm.value = {
    article_type: 'weixin',
    article_url: '',
    word_file: null,
    email_subject: '',
    original_content: '',
    original_html: null,
    content_source: '',
    image_count: 0,
    email_from: '',
    cooperation_type: '',
    media_type: '',
    source_unit: ''
  }
  wordFileList.value = []
  if (wordUploadRef.value) {
    wordUploadRef.value.clearFiles()
  }
}

function handleArticleTypeChange() {
  // 切换类型时清空相关字段
  manualCreateForm.value.article_url = ''
  manualCreateForm.value.word_file = null
  manualCreateForm.value.email_subject = ''
  manualCreateForm.value.original_content = ''
  manualCreateForm.value.preview_html = ''
  manualCreateForm.value.original_html = null
  manualCreateForm.value.content_source = ''
  manualCreateForm.value.image_count = 0
  manualCreateForm.value.media_map = null
  wordFileList.value = []
  if (wordUploadRef.value) {
    wordUploadRef.value.clearFiles()
  }
  manualCreateStep.value = 1
}

function handleWordFileChange(file) {
  manualCreateForm.value.word_file = file.raw
  wordFileList.value = [file]
}

function handleWordFileRemove() {
  manualCreateForm.value.word_file = null
  wordFileList.value = []
}

const handlePreviewContent = async () => {
  if (!previewFormRef.value) return
  await previewFormRef.value.validate(async (valid) => {
    if (!valid) return
    
    manualCreatePreviewing.value = true
    try {
      const formData = new FormData()
      formData.append('article_type', manualCreateForm.value.article_type)
      
      if (['weixin', 'meipian', 'other_url'].includes(manualCreateForm.value.article_type)) {
        if (!manualCreateForm.value.article_url) {
          ElMessage.warning('请输入文章链接')
          manualCreatePreviewing.value = false
          return
        }
        formData.append('article_url', manualCreateForm.value.article_url)
      } else if (manualCreateForm.value.article_type === 'word') {
        if (!manualCreateForm.value.word_file) {
          ElMessage.warning('请上传Word文档')
          manualCreatePreviewing.value = false
          return
        }
        formData.append('word_file', manualCreateForm.value.word_file)
      }
      
      const response = await previewContent(formData)
      
      // 填充解析结果
      manualCreateForm.value.email_subject = response.title
      manualCreateForm.value.original_content = response.content
      manualCreateForm.value.preview_html = response.preview_html
      manualCreateForm.value.original_html = response.original_html
      manualCreateForm.value.content_source = response.content_source
      manualCreateForm.value.image_count = response.image_count
      manualCreateForm.value.media_map = response.media_map
      
      // 进入第二步
      manualCreateStep.value = 2
      if (response.image_count > 0) {
        ElMessage.success(`内容解析成功，已上传 ${response.image_count} 张图片`)
      } else {
        ElMessage.success('内容解析成功')
      }
    } catch (error) {
      const msg = error.response?.data?.detail || error.message || '未知错误'
      if (msg.includes('链接')) {
        ElMessage.error('链接无效或无法访问，请检查链接是否正确')
      } else if (msg.includes('格式')) {
        ElMessage.error('文件格式不支持，请上传 .doc 或 .docx 文件')
      } else if (msg.includes('网络') || msg.includes('timeout')) {
        ElMessage.error('网络超时，请稍后重试')
      } else {
        ElMessage.error('解析失败: ' + msg)
      }
    } finally {
      manualCreatePreviewing.value = false
    }
  })
}

const submitManualCreate = async () => {
  if (!manualCreateFormRef.value) return
  await manualCreateFormRef.value.validate(async (valid) => {
    if (!valid) return
    
    manualCreateSubmitting.value = true
    try {
      const isOtherUrl = manualCreateForm.value.content_source === 'other_url'
      const response = await createSubmission({
        title: manualCreateForm.value.email_subject,
        content: manualCreateForm.value.original_content,
        original_html: manualCreateForm.value.original_html,
        content_source: manualCreateForm.value.content_source,
        media_map: manualCreateForm.value.media_map,
        email_from: manualCreateForm.value.email_from,
        cooperation_type: manualCreateForm.value.cooperation_type,
        media_type: manualCreateForm.value.media_type,
        source_unit: manualCreateForm.value.source_unit
      })
      manualCreateDialogVisible.value = false
      if (isOtherUrl) {
        ElMessage.success('创建成功，AI自动采集已启动')
      } else {
        ElMessage.success('创建成功')
      }
      // 跳转到审核页面（使用第一个草稿）
      if (response.drafts && response.drafts.length > 0) {
        router.push({ name: 'audit', params: { draftId: response.drafts[0].id } })
      } else {
        // 如果没有草稿，刷新列表
        loadSubmissions()
      }
    } catch (error) {
      const msg = error.response?.data?.detail || error.message || '未知错误'
      ElMessage.error('创建失败: ' + msg)
    } finally {
      manualCreateSubmitting.value = false
    }
  })
}

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

// 视频扩展名正则（与下面 getVideoList 一致）
const VIDEO_EXT_RE = /\.(mp4|avi|mov|wmv|flv|mkv)$/i

// 获取图片数量（排除视频）：仅统计 submission_images 中非视频项
const getImageCount = (row) => {
  if (!row || !Array.isArray(row.images) || row.images.length === 0) return 0
  return row.images.filter(img => {
    if (!img || typeof img !== 'object') return false
    const filename = (img.original_filename ?? img.originalFilename ?? '').toString()
    return !VIDEO_EXT_RE.test(filename)
  }).length
}

// 获取视频数量
const getVideoCount = (row) => {
  if (!row || !Array.isArray(row.images) || row.images.length === 0) return 0
  return row.images.filter(img => {
    if (!img || typeof img !== 'object') return false
    const filename = (img.original_filename ?? img.originalFilename ?? '').toString()
    return VIDEO_EXT_RE.test(filename)
  }).length
}

// 获取图片列表（排除视频）
const getImageList = (submission) => {
  if (!submission || !Array.isArray(submission.images) || submission.images.length === 0) return []
  return submission.images.filter(img => {
    if (!img || typeof img !== 'object') return false
    const filename = (img.original_filename ?? img.originalFilename ?? '').toString()
    return !VIDEO_EXT_RE.test(filename)
  })
}

// 获取视频列表
const getVideoList = (submission) => {
  if (!submission || !Array.isArray(submission.images) || submission.images.length === 0) return []
  return submission.images.filter(img => {
    if (!img || typeof img !== 'object') return false
    const filename = (img.original_filename ?? img.originalFilename ?? '').toString()
    return VIDEO_EXT_RE.test(filename)
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
    if (dateRange.value && dateRange.value.length === 2) {
      params.start_date = dateRange.value[0]
      params.end_date = dateRange.value[1]
    }

    const response = await getSubmissions(params)
    submissions.value = response.items
    total.value = response.total
    
    // 提取筛选选项
    extractFilterOptions(response.items)
  } catch (error) {
    const detail = error.response?.data?.detail
    const msg = typeof detail === 'string' ? detail : (detail?.msg || error.message || '未知错误')
    ElMessage.error('加载投稿列表失败: ' + msg)
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

// 多选处理
const handleSelectionChange = (selection) => {
  selectedSubmissions.value = selection
}

// 行点击：优先打开草稿,无草稿则打开详情
const handleRowClick = (row) => {
  // 日期行不响应点击
  if (row.isDateRow) return
  
  if (row.drafts && row.drafts.length > 0) {
    handleViewDraft(row)
  } else {
    handleViewDetail(row)
  }
}

// 查看详情
const handleViewDetail = (row) => {
  currentSubmission.value = row
  detailDialogVisible.value = true
}

// 查看草稿
const handleClaim = async (row) => {
  try {
    await claimSubmission(row.id)
    ElMessage.success('认领成功')
    loadSubmissions()
  } catch (error) {
    const msg = error.response?.data?.detail || error.message || '认领失败'
    ElMessage.error(msg)
  }
}

const doNavigateToDraft = (row) => {
  const draftId = row.drafts[0].id
  router.push({ name: 'audit', params: { draftId } })
}

const handleViewDraft = async (row) => {
  if (!row.drafts || row.drafts.length === 0) {
    ElMessage.warning('该投稿还没有生成草稿')
    return
  }
  const currentUser = getUserInfo()
  const claimedByOther = row.claimed_by_label && row.claimed_by_user_id && currentUser?.id !== row.claimed_by_user_id
  if (claimedByOther) {
    const timeStr = row.claimed_at ? formatClaimTime(row.claimed_at) : ''
    const msg = timeStr
      ? `该稿件${timeStr}由 ${row.claimed_by_label} 认领，是否继续编辑？`
      : `该稿件已由 ${row.claimed_by_label} 认领，是否继续编辑？`
    try {
      await ElMessageBox.confirm(msg, '提示', {
        confirmButtonText: '继续编辑',
        cancelButtonText: '取消',
        type: 'warning'
      })
    } catch {
      return
    }
  }
  doNavigateToDraft(row)
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

// 删除投稿
const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除投稿「${(row.email_subject || '无标题').slice(0, 30)}${(row.email_subject && row.email_subject.length > 30) ? '…' : ''}」吗？删除后无法恢复。`,
      '确认删除',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    await deleteSubmission(row.id)
    ElMessage.success('删除成功')
    loadSubmissions()
  } catch (error) {
    if (error !== 'cancel') {
      const msg = error.response?.data?.detail || error.message || '未知错误'
      ElMessage.error('删除失败: ' + msg)
    }
  }
}

// 批量删除
const handleBatchDelete = async () => {
  if (selectedSubmissions.value.length === 0) return
  
  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedSubmissions.value.length} 条投稿吗？删除后无法恢复。`,
      '确认批量删除',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    const deletePromises = selectedSubmissions.value.map(row => deleteSubmission(row.id))
    await Promise.all(deletePromises)
    
    ElMessage.success(`成功删除 ${selectedSubmissions.value.length} 条投稿`)
    selectedSubmissions.value = []
    loadSubmissions()
  } catch (error) {
    if (error !== 'cancel') {
      const msg = error.response?.data?.detail || error.message || '未知错误'
      ElMessage.error('批量删除失败: ' + msg)
    }
  }
}

// 刷新邮箱
const handleFetchEmails = async () => {
  if (fetchingEmails.value) return
  fetchingEmails.value = true
  emailFetchStatus.value = null
  
  try {
    await triggerFetchEmails()
    ElMessage.success('邮件抓取任务已启动')
    // 开始轮询状态
    startPollingEmailStatus()
  } catch (error) {
    const msg = error.response?.data?.detail || error.message || '未知错误'
    ElMessage.error('启动邮件抓取失败: ' + msg)
    fetchingEmails.value = false
  }
}

// 轮询邮件抓取状态
const startPollingEmailStatus = async () => {
  const poll = async () => {
    try {
      const status = await getFetchEmailsStatus()
      emailFetchStatus.value = status
      
      // 如果任务完成或失败，停止轮询
      if (status.status === 'success' || status.status === 'failed') {
        fetchingEmails.value = false
        if (emailFetchStatusTimer) {
          clearInterval(emailFetchStatusTimer)
          emailFetchStatusTimer = null
        }
        // 任务完成后刷新列表
        if (status.status === 'success') {
          setTimeout(() => {
            loadSubmissions()
          }, 1000)
        }
      }
    } catch (error) {
      console.error('获取邮件抓取状态失败:', error)
    }
  }
  
  // 立即查询一次
  await poll()
  
  // 每2秒轮询一次
  emailFetchStatusTimer = setInterval(poll, 2000)
}

// 格式化时间
const formatTime = (timeStr) => {
  if (!timeStr) return ''
  const d = new Date(timeStr)
  return d.toLocaleString('zh-CN', { hour12: false })
}

// 组件卸载时清理定时器
onUnmounted(() => {
  if (emailFetchStatusTimer) {
    clearInterval(emailFetchStatusTimer)
    emailFetchStatusTimer = null
  }
})

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

const hasPublished = (row) => {
  return Array.isArray(row?.drafts) && row.drafts.some(d => d.status === 'published')
}

const getStatusTypeByRow = (row) => {
  if (hasPublished(row)) return 'primary'
  return getStatusType(row?.status)
}

const getStatusTextByRow = (row) => {
  if (hasPublished(row)) return '已发布'
  return getStatusText(row?.status)
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

// 格式化认领时间：yy-m-d 00:00（如 26-2-28 16:15）
const formatClaimTime = (dateStr) => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  const yy = String(date.getFullYear()).slice(-2)
  const m = date.getMonth() + 1
  const d = date.getDate()
  const h = String(date.getHours()).padStart(2, '0')
  const min = String(date.getMinutes()).padStart(2, '0')
  return `${yy}-${m}-${d} ${h}:${min}`
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

.header-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}

.header-row-actions {
  justify-content: space-between;
  margin-bottom: 12px;
}

.header-row-actions h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.action-buttons {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.header-row-filters {
  padding-top: 8px;
  border-top: 1px solid #ebeef5;
}

.filter-input {
  width: 200px;
}

.filter-date {
  width: 260px;
}

.filter-select {
  width: 120px;
}

.filter-select-unit {
  width: 150px;
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

/* 日期分隔行样式 */
:deep(.date-row) {
  background: linear-gradient(to right, #e8f4fd, #f5f7fa) !important;
  font-weight: 600;
  font-size: 14px;
  color: #303133;
  cursor: default !important;
}

:deep(.date-row:hover) {
  background: linear-gradient(to right, #e8f4fd, #f5f7fa) !important;
}

:deep(.date-row td) {
  padding: 14px 0 !important;
  text-align: left !important;
  padding-left: 20px !important;
  border-bottom: 2px solid #409eff !important;
  border-top: 2px solid #409eff !important;
}

.date-row-tip {
  margin-left: 10px;
  color: #f56c6c;
  font-size: 13px;
  font-weight: 500;
}

/* 操作列：按钮与认领信息统一布局 */
.op-cell {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.claimed-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  font-size: 12px;
  color: #67c23a;
  background: #f0f9eb;
  border-radius: 4px;
  border: 1px solid #e1f3d8;
}

.claimed-badge .claimed-icon {
  font-size: 12px;
}

/* 附件列：徽章数字不错位、不裁切 */
.attachment-cell {
  display: flex;
  gap: 8px;
  justify-content: center;
  align-items: center;
}

.attachment-badge-wrap {
  display: inline-flex;
  position: relative;
  line-height: 0;
}

.attachment-badge-wrap :deep(.el-badge) {
  display: inline-flex;
}

.attachment-badge-wrap :deep(.el-badge__content) {
  position: absolute;
  top: 0;
  right: 0;
  margin: 0;
  min-width: 18px;
  height: 18px;
  line-height: 18px;
  padding: 0 6px;
  text-align: center;
  transform: translate(50%, -50%);
  border-radius: 9px;
  font-size: 12px;
}

.attachment-badge-wrap :deep(.el-badge__content.is-fixed) {
  position: absolute;
  top: 0;
  right: 0;
  transform: translate(50%, -50%);
}

/* 手动创建投稿编辑器容器 */
.manual-create-editor-wrapper {
  width: 100%;
  max-height: 500px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  overflow-y: auto;
  background: #fff;
  padding: 16px;
}

.manual-create-editor-wrapper img {
  max-width: 100%;
  height: auto;
  display: block;
  margin: 10px 0;
}

.manual-create-editor-wrapper p {
  margin: 8px 0;
  line-height: 1.6;
}

.manual-create-editor-wrapper :deep(.tiptap-editor-root) {
  height: 100%;
  border: none;
  border-radius: 0;
}

.manual-create-editor-wrapper :deep(.tiptap-content-wrap) {
  height: calc(100% - 40px);
  overflow-y: auto;
}
</style>
