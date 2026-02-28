<template>
  <div class="copy-editor-detail-container">
    <el-card class="header-card">
      <el-page-header @back="goBack" title="返回" />
      <h2>文编详细工作量</h2>
      <p v-if="detail" class="summary-line">{{ detail.copy_editor }} · 时间范围：{{ startDate }} 至 {{ endDate }}</p>
    </el-card>

    <template v-if="loading">
      <el-skeleton :rows="5" animated />
    </template>
    <template v-else-if="detail">
      <el-card shadow="hover" style="margin-bottom: 20px;">
        <el-statistic title="总发布量" :value="detail.total_published" />
      </el-card>

      <el-card header="按发布站点" shadow="hover">
        <el-table :data="detail.by_site" stripe>
          <el-table-column prop="site_name" label="站点" min-width="160" />
          <el-table-column prop="published" label="发布量" width="120" />
        </el-table>
        <el-empty v-if="!detail.by_site?.length" description="暂无" />
      </el-card>
    </template>
    <el-empty v-else-if="!loading" description="未选择文编或时间范围" />
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

const goBack = () => router.push({ path: '/copy-editor-workload' })

const loadDetail = async () => {
  const publisher_user_id = route.query.publisher_user_id
  const start_date = route.query.start_date
  const end_date = route.query.end_date
  if (publisher_user_id == null || publisher_user_id === '' || !start_date || !end_date) {
    return
  }
  loading.value = true
  try {
    const token = localStorage.getItem('access_token')
    const params = new URLSearchParams({ publisher_user_id, start_date, end_date })
    const res = await fetch(`/api/analytics/copy-editor-workload-detail?${params}`, {
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
.copy-editor-detail-container {
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
