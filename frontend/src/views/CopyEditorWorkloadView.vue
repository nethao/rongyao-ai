<template>
  <div class="copy-editor-workload-container">
    <el-card class="header-card">
      <h2>文编工作量统计</h2>
      <p class="time-rule-tip">按发布成功时间统计：当日 14:01 至次日 14:00 归为「次日」（如 1月1日 14:01～1月2日 14:00 计为 1月2日）。</p>

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
        <el-form-item label="文编姓名">
          <el-select
            v-model="publisherUserId"
            placeholder="全部"
            clearable
            filterable
            style="width: 160px"
          >
            <el-option label="全部" :value="null" />
            <el-option
              v-for="opt in copyEditorOptions"
              :key="opt.user_id"
              :label="opt.label"
              :value="opt.user_id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="发布站点">
          <el-select
            v-model="siteId"
            placeholder="全部"
            clearable
            filterable
            style="width: 160px"
          >
            <el-option label="全部" :value="null" />
            <el-option
              v-for="s in siteOptions"
              :key="s.id"
              :label="s.name"
              :value="s.id"
            />
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
        <span>文编工作量（按发布成功时间）</span>
        <span v-if="publisherUserId != null || siteId != null" class="filter-summary">
          （当前筛选：{{ publisherUserId != null ? (copyEditorOptions.find(o => o.user_id === publisherUserId)?.label || '') : '全部文编' }} / {{ siteId != null ? (siteOptions.find(s => s.id === siteId)?.name || '') : '全部站点' }}）
        </span>
      </template>
      <el-table :data="list" stripe @row-click="onCopyEditorRowClick">
        <el-table-column prop="copy_editor" label="文编" min-width="160">
          <template #default="{ row }">
            <span class="cell-link">{{ row.copy_editor }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="published" label="发布量" width="120" />
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
const publisherUserId = ref(null)
const siteId = ref(null)
const copyEditorOptions = ref([])
const siteOptions = ref([])
const list = ref([])
const loading = ref(false)

const getToken = () => localStorage.getItem('access_token')

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

const onCopyEditorRowClick = (row) => {
  if (!dateRange.value?.length) return
  const uid = row.publisher_user_id
  if (uid == null) return
  router.push({
    path: '/copy-editor-workload/detail',
    query: {
      publisher_user_id: uid,
      start_date: dateRange.value[0],
      end_date: dateRange.value[1]
    }
  })
}

const resetFilters = () => {
  dateRange.value = []
  publisherUserId.value = null
  siteId.value = null
  list.value = []
}

const loadCopyEditorOptions = async () => {
  try {
    const token = getToken()
    const res = await fetch('/api/analytics/copy-editor-options', {
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }
    })
    if (res.ok) copyEditorOptions.value = await res.json()
  } catch (e) {
    console.error('加载文编选项失败', e)
  }
}

const loadSiteOptions = async () => {
  try {
    const token = getToken()
    const res = await fetch('/api/wordpress-sites', {
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }
    })
    if (res.ok) {
      const data = await res.json()
      siteOptions.value = data.sites || []
    }
  } catch (e) {
    console.error('加载站点列表失败', e)
  }
}

const loadData = async () => {
  const params = new URLSearchParams()
  if (dateRange.value && dateRange.value.length === 2) {
    params.append('start_date', dateRange.value[0])
    params.append('end_date', dateRange.value[1])
  }
  if (publisherUserId.value != null && publisherUserId.value !== '') {
    params.append('publisher_user_id', publisherUserId.value)
  }
  if (siteId.value != null && siteId.value !== '') {
    params.append('site_id', siteId.value)
  }

  const queryString = params.toString() ? `?${params}` : ''
  if (!dateRange.value?.length) {
    ElMessage.warning('请先选择时间范围')
    return
  }

  loading.value = true
  try {
    const token = getToken()
    const res = await fetch(`/api/analytics/copy-editors${queryString}`, {
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
  loadCopyEditorOptions()
  loadSiteOptions()
  setToday()
})
</script>

<style scoped>
.copy-editor-workload-container {
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
