<template>
  <div class="editor-detail-container">
    <el-card class="header-card">
      <el-page-header @back="goBack" title="返回" />
      <h2>采编详细工作量</h2>
      <p v-if="detail" class="summary-line">{{ detail.editor }} · 时间范围：{{ startDate }} 至 {{ endDate }}</p>
    </el-card>

    <template v-if="loading">
      <el-skeleton :rows="5" animated />
    </template>
    <template v-else-if="detail">
      <el-row :gutter="20">
        <el-col :span="6">
          <el-card shadow="hover" :body-style="{ padding: '16px' }">
            <el-statistic title="投稿数" :value="detail.total" />
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover" :body-style="{ padding: '16px' }">
            <el-statistic title="待处理" :value="detail.pending" />
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover" :body-style="{ padding: '16px' }">
            <el-statistic title="已完成" :value="detail.completed" />
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover" :body-style="{ padding: '16px' }">
            <el-statistic title="已发布" :value="detail.published" />
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="20" style="margin-top: 20px;">
        <el-col :span="12">
          <el-card header="按媒体站点" shadow="hover">
            <el-table :data="detail.by_media_type" stripe>
              <el-table-column prop="site_name" label="站点" min-width="140">
                <template #default="{ row }">{{ row.site_name || getMediaLabel(row.media_type) }}</template>
              </el-table-column>
              <el-table-column prop="count" label="数量" width="100" />
            </el-table>
            <el-empty v-if="!detail.by_media_type?.length" description="暂无" />
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card header="按合作方式" shadow="hover">
            <el-table :data="detail.by_cooperation_type" stripe>
              <el-table-column prop="cooperation_type" label="合作方式" width="120">
                <template #default="{ row }">{{ row.cooperation_type === 'free' ? '投' : row.cooperation_type === 'partner' ? '合' : row.cooperation_type }}</template>
              </el-table-column>
              <el-table-column prop="count" label="数量" width="100" />
            </el-table>
            <el-empty v-if="!detail.by_cooperation_type?.length" description="暂无" />
          </el-card>
        </el-col>
      </el-row>
    </template>
    <el-empty v-else-if="!loading" description="未选择采编或时间范围" />
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

const route = useRoute()
const router = useRouter()
const detail = ref(null)
const loading = ref(false)

const startDate = computed(() => route.query.start_date || '')
const endDate = computed(() => route.query.end_date || '')

const getMediaLabel = (v) => {
  const labels = { rongyao: '荣耀', shidai: '时代', zhengxian: '政贤', zhengqi: '政气', toutiao: '头条' }
  return labels[v] || v || '—'
}

const goBack = () => router.push({ path: '/editor-workload' })

const loadDetail = async () => {
  const email_from = route.query.email_from
  const start_date = route.query.start_date
  const end_date = route.query.end_date
  if (!email_from || !start_date || !end_date) {
    return
  }
  loading.value = true
  try {
    const token = localStorage.getItem('access_token')
    const params = new URLSearchParams({ email_from, start_date, end_date })
    const res = await fetch(`/api/analytics/editor-workload-detail?${params}`, {
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }
    })
    if (res.ok) detail.value = await res.json()
    else ElMessage.error('加载失败')
  } catch (e) {
    console.error(e)
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => loadDetail())
</script>

<style scoped>
.editor-detail-container {
  padding: 20px;
}

.header-card h2 {
  margin: 12px 0 0;
}

.summary-line {
  margin: 8px 0 0;
  color: #909399;
  font-size: 14px;
}
</style>
