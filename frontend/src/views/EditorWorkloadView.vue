<template>
  <div class="editor-workload-container">
    <el-card class="header-card">
      <h2>采编工作量统计</h2>
      <p class="time-rule-tip">按邮件到达邮箱时间统计：当日 14:01 至次日 14:00 归为「次日」稿件（如 1月1日 14:01～1月2日 14:00 计为 1月2日）。</p>

      <el-form :inline="true" class="filter-form">
        <el-form-item label="时间范围">
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
          />
        </el-form-item>
        <el-form-item label="采编人员">
          <el-select
            v-model="emailFrom"
            placeholder="全部"
            clearable
            filterable
            style="width: 180px"
          >
            <el-option label="全部" value="" />
            <el-option
              v-for="opt in editorOptions"
              :key="opt.email_from"
              :label="opt.label"
              :value="opt.email_from"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="媒体站点">
          <el-select v-model="mediaType" placeholder="全部" clearable style="width: 140px">
            <el-option label="全部" value="" />
            <el-option label="荣耀" value="rongyao" />
            <el-option label="时代" value="shidai" />
            <el-option label="政贤" value="zhengxian" />
            <el-option label="政气" value="zhengqi" />
            <el-option label="头条" value="toutiao" />
          </el-select>
        </el-form-item>
        <el-form-item label="合作方式">
          <el-select v-model="cooperationType" placeholder="全部" clearable style="width: 120px">
            <el-option label="全部" value="" />
            <el-option label="投" value="free" />
            <el-option label="合" value="partner" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button-group>
            <el-button size="small" @click="setToday">今天</el-button>
            <el-button size="small" @click="setYesterday">昨天</el-button>
            <el-button size="small" @click="setLast7Days">7天</el-button>
            <el-button size="small" @click="setThisMonth">本月</el-button>
          </el-button-group>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadData">查询</el-button>
          <el-button @click="resetFilters">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card class="table-card">
      <template #header>
        <span>采编工作量</span>
        <span v-if="emailFrom || mediaType || cooperationType" class="filter-summary">
          （当前筛选：{{ emailFrom ? (editorOptions.find(o => o.email_from === emailFrom)?.label || emailFrom) : '全部采编' }} / {{ mediaType ? getMediaTypeLabel(mediaType) : '全部媒体' }} / {{ cooperationType ? (cooperationType === 'free' ? '投' : '合') : '全部合作方式' }}）
        </span>
      </template>
      <el-table :data="list" stripe @row-click="onEditorRowClick">
        <el-table-column prop="editor" label="采编" min-width="160">
          <template #default="{ row }">
            <span class="cell-link">{{ row.editor }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="total" label="投稿数" width="100" />
        <el-table-column prop="pending" label="待处理" width="100" />
        <el-table-column prop="completed" label="已完成" width="100" />
        <el-table-column prop="published" label="已发布" width="100" />
        <el-table-column prop="completion_rate" label="完成率" width="100">
          <template #default="{ row }">
            {{ row.completion_rate }}%
          </template>
        </el-table-column>
        <el-table-column prop="publish_rate" label="发布率" width="100">
          <template #default="{ row }">
            {{ row.publish_rate }}%
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="list.length === 0 && !loading" description="暂无数据，请选择时间范围后查询" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

const router = useRouter()

const dateRange = ref([])
const emailFrom = ref('')
const editorOptions = ref([])
const mediaType = ref('')
const cooperationType = ref('')
const list = ref([])
const loading = ref(false)

const getToken = () => localStorage.getItem('access_token')

const getMediaTypeLabel = (v) => {
  const labels = { rongyao: '荣耀', shidai: '时代', zhengxian: '政贤', zhengqi: '政气', toutiao: '头条' }
  return labels[v] || v
}

const formatDate = (d) => {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

const setToday = () => {
  const today = new Date()
  dateRange.value = [formatDate(today), formatDate(today)]
  loadData()
}

const setYesterday = () => {
  const d = new Date()
  d.setDate(d.getDate() - 1)
  dateRange.value = [formatDate(d), formatDate(d)]
  loadData()
}

const setLast7Days = () => {
  const today = new Date()
  const start = new Date()
  start.setDate(start.getDate() - 6)
  dateRange.value = [formatDate(start), formatDate(today)]
  loadData()
}

const setThisMonth = () => {
  const today = new Date()
  const first = new Date(today.getFullYear(), today.getMonth(), 1)
  dateRange.value = [formatDate(first), formatDate(today)]
  loadData()
}

const resetFilters = () => {
  dateRange.value = []
  emailFrom.value = ''
  mediaType.value = ''
  cooperationType.value = ''
  list.value = []
}

const onEditorRowClick = (row) => {
  if (!dateRange.value?.length) return
  router.push({
    path: '/editor-workload/detail',
    query: {
      email_from: row.email_from,
      start_date: dateRange.value[0],
      end_date: dateRange.value[1]
    }
  })
}

const loadEditorOptions = async () => {
  try {
    const token = getToken()
    const res = await fetch('/api/analytics/editor-options', {
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }
    })
    if (res.ok) editorOptions.value = await res.json()
  } catch (e) {
    console.error('加载采编选项失败', e)
  }
}

const loadData = async () => {
  const params = new URLSearchParams()
  if (dateRange.value && dateRange.value.length === 2) {
    params.append('start_date', dateRange.value[0])
    params.append('end_date', dateRange.value[1])
  }
  if (emailFrom.value) params.append('email_from', emailFrom.value)
  if (mediaType.value) params.append('media_type', mediaType.value)
  if (cooperationType.value) params.append('cooperation_type', cooperationType.value)

  const queryString = params.toString() ? `?${params}` : ''
  if (!dateRange.value?.length) {
    ElMessage.warning('请先选择时间范围')
    return
  }

  loading.value = true
  try {
    const token = getToken()
    const res = await fetch(`/api/analytics/editor-workload${queryString}`, {
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }
    })
    if (!res.ok) throw new Error('加载失败')
    list.value = await res.json()
    ElMessage.success('加载成功')
  } catch (e) {
    console.error(e)
    ElMessage.error(e.message || '加载失败')
    list.value = []
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadEditorOptions()
  setToday()
})
</script>

<style scoped>
.editor-workload-container {
  padding: 20px;
}

.header-card h2 {
  margin: 0;
}

.time-rule-tip {
  margin: 8px 0 0;
  font-size: 12px;
  color: #909399;
}

.filter-form {
  margin-top: 16px;
}

.table-card {
  margin-top: 20px;
}

.filter-summary {
  font-size: 12px;
  color: #909399;
  margin-left: 8px;
}

.cell-link {
  color: var(--el-color-primary);
  cursor: pointer;
}
.cell-link:hover {
  text-decoration: underline;
}
</style>
