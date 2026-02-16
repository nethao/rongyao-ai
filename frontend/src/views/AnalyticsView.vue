<template>
  <div class="analytics-container">
    <el-card class="header-card">
      <h2>数据分析</h2>
      
      <!-- 时间筛选 -->
      <el-form :inline="true" style="margin-top: 20px;">
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
        <el-form-item>
          <el-button type="primary" @click="loadData">查询</el-button>
          <el-button @click="resetDate">重置</el-button>
        </el-form-item>
      </el-form>

      <!-- 概览统计 -->
      <el-row :gutter="20" style="margin-top: 20px;">
        <el-col :span="6">
          <el-statistic title="总投稿数" :value="overview.total" />
        </el-col>
        <el-col :span="6">
          <el-statistic title="待处理" :value="overview.pending" />
        </el-col>
        <el-col :span="6">
          <el-statistic title="已完成" :value="overview.completed" />
        </el-col>
        <el-col :span="6">
          <el-statistic title="已发布" :value="overview.published" />
        </el-col>
      </el-row>
    </el-card>

    <!-- 投稿趋势 -->
    <el-card style="margin-top: 20px;">
      <template #header>
        <span>投稿趋势统计</span>
      </template>
      <el-table :data="trends" stripe>
        <el-table-column prop="date" label="日期" width="120" />
        <el-table-column prop="total" label="投稿数" width="100" />
        <el-table-column prop="completed" label="已完成" width="100" />
        <el-table-column prop="published" label="已发布" width="100" />
        <el-table-column prop="completion_rate" label="完成率" width="100">
          <template #default="{ row }">
            {{ row.completion_rate }}%
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 采编投稿统计 -->
    <el-card style="margin-top: 20px;">
      <template #header>
        <span>采编投稿统计</span>
      </template>
      <el-table :data="editors" stripe>
        <el-table-column prop="editor" label="采编" width="150" />
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
    </el-card>

    <!-- 媒体类型统计 -->
    <el-card style="margin-top: 20px;">
      <template #header>
        <span>媒体类型统计</span>
      </template>
      <el-table :data="media" stripe>
        <el-table-column prop="media_type" label="媒体" width="150" />
        <el-table-column prop="total" label="投稿数" width="120" />
        <el-table-column prop="published" label="已发布" width="120" />
        <el-table-column prop="publish_rate" label="发布率" width="120">
          <template #default="{ row }">
            {{ row.publish_rate }}%
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 来稿单位统计 -->
    <el-card style="margin-top: 20px;">
      <template #header>
        <span>来稿单位统计</span>
      </template>
      <el-table :data="units" stripe>
        <el-table-column prop="unit" label="单位" min-width="200" />
        <el-table-column prop="total" label="投稿数" width="120" />
        <el-table-column prop="published" label="已发布" width="120" />
        <el-table-column prop="publish_rate" label="发布率" width="120">
          <template #default="{ row }">
            {{ row.publish_rate }}%
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 站点发布统计 -->
    <el-card style="margin-top: 20px;">
      <template #header>
        <span>站点发布统计</span>
      </template>
      <el-table :data="sites" stripe>
        <el-table-column prop="site_name" label="站点" width="150" />
        <el-table-column prop="total" label="发布数" width="120" />
        <el-table-column prop="success" label="成功数" width="120" />
        <el-table-column prop="failed" label="失败数" width="120" />
        <el-table-column prop="success_rate" label="成功率" width="120">
          <template #default="{ row }">
            {{ row.success_rate }}%
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 内容来源统计 -->
    <el-card style="margin-top: 20px;">
      <template #header>
        <span>内容来源统计</span>
      </template>
      <el-table :data="sources" stripe>
        <el-table-column prop="source" label="来源类型" width="150" />
        <el-table-column prop="total" label="数量" width="120" />
        <el-table-column prop="percentage" label="占比" width="120">
          <template #default="{ row }">
            {{ row.percentage }}%
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'

const dateRange = ref([])
const overview = ref({ total: 0, pending: 0, completed: 0, published: 0 })
const trends = ref([])
const editors = ref([])
const media = ref([])
const units = ref([])
const sites = ref([])
const sources = ref([])

const getToken = () => localStorage.getItem('access_token')

const loadData = async () => {
  const params = new URLSearchParams()
  if (dateRange.value && dateRange.value.length === 2) {
    params.append('start_date', dateRange.value[0])
    params.append('end_date', dateRange.value[1])
  }
  
  try {
    const token = getToken()
    const headers = { 
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    }
    
    const queryString = params.toString() ? `?${params}` : ''
    
    // 加载概览
    const overviewRes = await fetch(`/api/analytics/overview${queryString}`, { headers })
    if (!overviewRes.ok) throw new Error('加载概览失败')
    overview.value = await overviewRes.json()
    
    // 加载趋势
    const trendsRes = await fetch(`/api/analytics/trends${queryString}`, { headers })
    if (!trendsRes.ok) throw new Error('加载趋势失败')
    trends.value = await trendsRes.json()
    
    // 加载采编统计
    const editorsRes = await fetch(`/api/analytics/editors${queryString}`, { headers })
    if (!editorsRes.ok) throw new Error('加载采编统计失败')
    editors.value = await editorsRes.json()
    
    // 加载媒体统计
    const mediaRes = await fetch(`/api/analytics/media${queryString}`, { headers })
    if (!mediaRes.ok) throw new Error('加载媒体统计失败')
    media.value = await mediaRes.json()
    
    // 加载单位统计
    const unitsRes = await fetch(`/api/analytics/units${queryString}`, { headers })
    if (!unitsRes.ok) throw new Error('加载单位统计失败')
    units.value = await unitsRes.json()
    
    // 加载站点统计
    const sitesRes = await fetch(`/api/analytics/sites${queryString}`, { headers })
    if (!sitesRes.ok) throw new Error('加载站点统计失败')
    sites.value = await sitesRes.json()
    
    // 加载来源统计
    const sourcesRes = await fetch(`/api/analytics/sources${queryString}`, { headers })
    if (!sourcesRes.ok) throw new Error('加载来源统计失败')
    sources.value = await sourcesRes.json()
    
    ElMessage.success('数据加载成功')
  } catch (error) {
    console.error('加载数据失败:', error)
    ElMessage.error(error.message || '加载数据失败')
  }
}

const resetDate = () => {
  dateRange.value = []
  loadData()
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.analytics-container {
  padding: 20px;
}

.header-card h2 {
  margin: 0;
}
</style>
