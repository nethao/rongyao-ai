<template>
  <div class="analytics-container">
    <el-card class="header-card">
      <h2>数据分析</h2>
      <p class="time-rule-tip">统计日期规则：当日 14:01 至次日 14:00 归为「次日」稿件（如 1月1日 14:01～1月2日 14:00 计为 1月2日）。</p>

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
          <el-button-group>
            <el-button size="small" @click="setToday">今天</el-button>
            <el-button size="small" @click="setYesterday">昨天</el-button>
            <el-button size="small" @click="setLast7Days">7天</el-button>
            <el-button size="small" @click="setThisMonth">本月</el-button>
          </el-button-group>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadData">查询</el-button>
          <el-button @click="resetDate">重置</el-button>
        </el-form-item>
      </el-form>

      <!-- 概览统计 -->
      <el-row :gutter="20" style="margin-top: 20px;">
        <el-col :span="6">
          <el-card shadow="hover" :body-style="{ padding: '20px' }">
            <el-statistic title="总投稿数" :value="overview.total">
              <template #suffix>
                <span style="font-size: 14px; color: #909399;">篇</span>
              </template>
            </el-statistic>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover" :body-style="{ padding: '20px' }">
            <el-statistic title="待处理" :value="overview.pending">
              <template #suffix>
                <span style="font-size: 14px; color: #e6a23c;">篇</span>
              </template>
            </el-statistic>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover" :body-style="{ padding: '20px' }">
            <el-statistic title="已完成" :value="overview.completed">
              <template #suffix>
                <span style="font-size: 14px; color: #67c23a;">篇</span>
              </template>
            </el-statistic>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover" :body-style="{ padding: '20px' }">
            <el-statistic title="已发布" :value="overview.published">
              <template #suffix>
                <span style="font-size: 14px; color: #409eff;">篇</span>
              </template>
            </el-statistic>
          </el-card>
        </el-col>
      </el-row>

      <!-- 快速入口 -->
      <el-row :gutter="20" style="margin-top: 20px;">
        <el-col :span="6">
          <el-card shadow="hover" class="quick-link" @click="scrollTo('trends')">
            <div class="quick-link-content">
              <el-icon :size="32" color="#409eff"><TrendCharts /></el-icon>
              <div class="quick-link-text">
                <div class="quick-link-title">投稿趋势</div>
                <div class="quick-link-desc">查看每日投稿统计</div>
              </div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover" class="quick-link" @click="scrollTo('editors')">
            <div class="quick-link-content">
              <el-icon :size="32" color="#67c23a"><User /></el-icon>
              <div class="quick-link-text">
                <div class="quick-link-title">采编统计</div>
                <div class="quick-link-desc">采编投稿排行（姓名/邮箱）</div>
              </div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover" class="quick-link" @click="scrollTo('copy-editors')">
            <div class="quick-link-content">
              <el-icon :size="32" color="#909399"><EditPen /></el-icon>
              <div class="quick-link-text">
                <div class="quick-link-title">文编工作量</div>
                <div class="quick-link-desc">按发布人统计发布量</div>
              </div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover" class="quick-link" @click="scrollTo('sites')">
            <div class="quick-link-content">
              <el-icon :size="32" color="#e6a23c"><Monitor /></el-icon>
              <div class="quick-link-text">
                <div class="quick-link-title">站点统计</div>
                <div class="quick-link-desc">查看发布成功率</div>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </el-card>

    <!-- 投稿趋势 -->
    <el-card id="trends" style="margin-top: 20px;">
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

    <!-- 采编投稿统计（采编=来稿邮箱，显示名=后台姓名映射，无映射显示邮箱） -->
    <el-card id="editors" style="margin-top: 20px;">
      <template #header>
        <span>采编投稿统计</span>
      </template>
      <el-table :data="editors" stripe>
        <el-table-column prop="editor" label="采编" width="200" />
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

    <!-- 文编工作量统计（按发布人统计发布量，时间同 14:01～次日14:00 规则） -->
    <el-card id="copy-editors" style="margin-top: 20px;">
      <template #header>
        <span>文编工作量统计</span>
      </template>
      <el-table :data="copyEditors" stripe>
        <el-table-column prop="copy_editor" label="文编" width="180" />
        <el-table-column prop="published" label="发布量" width="120" />
      </el-table>
    </el-card>

    <!-- 媒体类型统计 -->
    <el-card style="margin-top: 20px;">
      <template #header>
        <span>媒体类型统计</span>
      </template>
      <el-table :data="media" stripe>
        <el-table-column prop="media_type" label="媒体" width="150">
          <template #default="{ row }">
            {{ getMediaTypeLabel(row.media_type) }}
          </template>
        </el-table-column>
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
    <el-card id="sites" style="margin-top: 20px;">
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
        <el-table-column prop="source" label="来源类型" width="150">
          <template #default="{ row }">
            {{ getSourceLabel(row.source) }}
          </template>
        </el-table-column>
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
import { TrendCharts, User, Monitor, EditPen } from '@element-plus/icons-vue'

const dateRange = ref([])
const overview = ref({ total: 0, pending: 0, completed: 0, published: 0 })
const trends = ref([])
const editors = ref([])
const copyEditors = ref([])
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

    // 加载文编工作量统计
    const copyEditorsRes = await fetch(`/api/analytics/copy-editors${queryString}`, { headers })
    if (!copyEditorsRes.ok) throw new Error('加载文编工作量统计失败')
    copyEditors.value = await copyEditorsRes.json()

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

const formatDate = (date) => {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

const setToday = () => {
  const today = new Date()
  dateRange.value = [formatDate(today), formatDate(today)]
  loadData()
}

const setYesterday = () => {
  const yesterday = new Date()
  yesterday.setDate(yesterday.getDate() - 1)
  dateRange.value = [formatDate(yesterday), formatDate(yesterday)]
  loadData()
}

const setLast7Days = () => {
  const today = new Date()
  const last7Days = new Date()
  last7Days.setDate(last7Days.getDate() - 6)
  dateRange.value = [formatDate(last7Days), formatDate(today)]
  loadData()
}

const setThisMonth = () => {
  const today = new Date()
  const firstDay = new Date(today.getFullYear(), today.getMonth(), 1)
  dateRange.value = [formatDate(firstDay), formatDate(today)]
  loadData()
}

const scrollTo = (id) => {
  const element = document.getElementById(id)
  if (element) {
    element.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
}

// 内容来源中文标签（与 AuditView 一致）
const getSourceLabel = (source) => {
  if (source == null || source === '') return '—'
  const labels = {
    weixin: '微信公众号',
    meipian: '美篇',
    doc: 'Word文档',
    docx: 'Word文档',
    video: '视频',
    archive: '压缩包',
    other_url: '其他链接',
    large_attachment: '超大附件',
    text: '纯文本'
  }
  return labels[source] || source
}

// 媒体类型中文标签（含与来源一致的 other_url 等）
const getMediaTypeLabel = (mediaType) => {
  if (mediaType == null || mediaType === '') return '—'
  const labels = {
    rongyao: '荣耀',
    shidai: '时代',
    zhengxian: '政贤',
    zhengqi: '政气',
    toutiao: '头条',
    other_url: '其他链接',
    weixin: '微信公众号',
    meipian: '美篇',
    doc: 'Word文档',
    docx: 'Word文档',
    text: '纯文本'
  }
  return labels[mediaType] || mediaType
}

onMounted(() => {
  // 默认显示今天
  setToday()
})
</script>

<style scoped>
.analytics-container {
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

.quick-link {
  cursor: pointer;
  transition: all 0.3s;
}

.quick-link:hover {
  transform: translateY(-4px);
}

.quick-link-content {
  display: flex;
  align-items: center;
  gap: 16px;
}

.quick-link-text {
  flex: 1;
}

.quick-link-title {
  font-size: 16px;
  font-weight: 500;
  color: #303133;
  margin-bottom: 4px;
}

.quick-link-desc {
  font-size: 12px;
  color: #909399;
}
</style>
