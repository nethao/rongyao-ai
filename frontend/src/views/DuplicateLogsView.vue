<template>
  <div class="duplicate-logs-container">
    <el-card class="header-card">
      <h2>重复稿件</h2>
      <div class="filter-row">
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          value-format="YYYY-MM-DD"
          clearable
          class="filter-date"
        />
        <el-select
          v-model="duplicateTypeFilter"
          placeholder="类型"
          clearable
          class="filter-type"
          @change="loadData"
        >
          <el-option label="跳过（未处理）" value="skipped" />
          <el-option label="被替换" value="superseded" />
        </el-select>
        <el-button type="primary" @click="loadData">
          <el-icon><Search /></el-icon>
          查询
        </el-button>
        <el-button @click="resetFilters">重置</el-button>
      </div>
    </el-card>

    <el-card class="table-card">
      <el-table
        v-loading="loading"
        :data="items"
        style="width: 100%"
        stripe
      >
        <el-table-column prop="created_at" label="记录时间" width="170">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="duplicate_type" label="类型" width="100">
          <template #default="{ row }">
            <el-tag :type="row.duplicate_type === 'skipped' ? 'info' : 'warning'" size="small">
              {{ row.duplicate_type === 'skipped' ? '跳过' : '被替换' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="email_subject" label="邮件主题" min-width="200" show-overflow-tooltip />
        <el-table-column prop="email_from" label="发件人" width="140" show-overflow-tooltip />
        <el-table-column prop="email_date" label="邮件时间" width="160">
          <template #default="{ row }">
            {{ formatTime(row.email_date) }}
          </template>
        </el-table-column>
        <el-table-column prop="cooperation_type" label="合作方式" width="90">
          <template #default="{ row }">
            {{ row.cooperation_type === 'partner' ? '合作' : row.cooperation_type === 'free' ? '投稿' : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="media_type" label="媒体" width="90">
          <template #default="{ row }">
            {{ mediaLabel(row.media_type) }}
          </template>
        </el-table-column>
        <el-table-column prop="source_unit" label="来稿单位" width="130" show-overflow-tooltip />
        <el-table-column prop="effective_submission_id" label="有效稿ID" width="100" align="center">
          <template #default="{ row }">
            <el-link
              v-if="row.effective_submission_id"
              type="primary"
              :underline="false"
              @click="goToSubmission(row.effective_submission_id)"
            >
              #{{ row.effective_submission_id }}
            </el-link>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="superseded_submission_id" label="被替换稿ID" width="110" align="center">
          <template #default="{ row }">
            <span v-if="row.superseded_submission_id">#{{ row.superseded_submission_id }}</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-row">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50]"
          :total="total"
          layout="total, sizes, prev, pager, next"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Search } from '@element-plus/icons-vue'
import { getDuplicateLogs } from '../api/duplicateLogs'
import { ElMessage } from 'element-plus'

const router = useRouter()
const loading = ref(false)
const items = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const dateRange = ref(null)
const duplicateTypeFilter = ref(null)

const mediaMap = {
  rongyao: '荣耀网',
  shidai: '时代网',
  zhengxian: '争先网',
  zhengqi: '政企网',
  toutiao: '今日头条'
}

const mediaLabel = (v) => mediaMap[v] || v || '-'

const formatTime = (str) => {
  if (!str) return '-'
  const d = new Date(str)
  return d.toLocaleString('zh-CN', { hour12: false })
}

const loadData = async () => {
  loading.value = true
  try {
    const params = { page: currentPage.value, size: pageSize.value }
    if (dateRange.value && dateRange.value.length === 2) {
      params.start_date = dateRange.value[0]
      params.end_date = dateRange.value[1]
    }
    if (duplicateTypeFilter.value) {
      params.duplicate_type = duplicateTypeFilter.value
    }
    const res = await getDuplicateLogs(params)
    items.value = res.items || []
    total.value = res.total || 0
  } catch (e) {
    const msg = e.response?.data?.detail || e.message || '加载失败'
    ElMessage.error('加载重复稿件失败: ' + msg)
  } finally {
    loading.value = false
  }
}

const resetFilters = () => {
  dateRange.value = null
  duplicateTypeFilter.value = null
  currentPage.value = 1
  loadData()
}

const handlePageChange = () => loadData()
const handleSizeChange = () => {
  currentPage.value = 1
  loadData()
}

const goToSubmission = (id) => {
  router.push({ path: '/submissions', query: { highlight: id } })
}

onMounted(() => loadData())
</script>

<style scoped>
.duplicate-logs-container {
  padding: 20px;
}
.header-card h2 {
  margin: 0 0 16px 0;
  font-size: 18px;
}
.filter-row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.filter-date {
  width: 260px;
}
.filter-type {
  width: 140px;
}
.table-card {
  margin-top: 16px;
}
.pagination-row {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
