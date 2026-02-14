<template>
  <div class="config-view">
    <el-page-header @back="$router.back()">
      <template #content>
        <span class="page-title">系统配置</span>
      </template>
    </el-page-header>
    
    <el-tabs v-model="activeTab" style="margin-top: 20px">
      <!-- AI配置 -->
      <el-tab-pane label="AI配置" name="openai">
        <el-card>
          <el-alert title="快速配置" type="info" :closable="false" style="margin-bottom: 20px">
            <el-button size="small" @click="useAliyunPreset">阿里云百炼</el-button>
            <el-button size="small" @click="useMinimaxPreset">MiniMax</el-button>
            <el-button size="small" @click="useOpenRouterPreset">OpenRouter</el-button>
            <el-button size="small" @click="useOpenAIPreset">OpenAI</el-button>
          </el-alert>
          
          <el-form :model="openaiForm" label-width="150px">
            <el-form-item label="API Key">
              <el-input v-model="openaiForm.api_key" type="password" show-password placeholder="sk-..."></el-input>
            </el-form-item>
            <el-form-item label="API端点">
              <el-input v-model="openaiForm.base_url" placeholder="留空使用默认OpenAI端点"></el-input>
              <div style="color: #909399; font-size: 12px; margin-top: 5px;">
                完整URL，例如：https://dashscope.aliyuncs.com/compatible-mode/v1
              </div>
            </el-form-item>
            <el-form-item label="模型">
              <el-select v-model="openaiForm.model" placeholder="选择模型" filterable allow-create>
                <el-option-group label="阿里云百炼">
                  <el-option label="通义千问-Turbo (推荐)" value="qwen-turbo"></el-option>
                  <el-option label="通义千问-Plus" value="qwen-plus"></el-option>
                  <el-option label="通义千问-Max" value="qwen-max"></el-option>
                  <el-option label="通义千问-Long" value="qwen-long"></el-option>
                </el-option-group>
                <el-option-group label="OpenRouter">
                  <el-option label="Llama 3.3 70B (免费)" value="meta-llama/llama-3.3-70b-instruct:free"></el-option>
                  <el-option label="Gemini 2.0 Flash (免费)" value="google/gemini-2.0-flash-exp:free"></el-option>
                  <el-option label="Mistral Small (免费)" value="mistralai/mistral-small-3.1:free"></el-option>
                </el-option-group>
                <el-option-group label="OpenAI">
                  <el-option label="GPT-4" value="gpt-4"></el-option>
                  <el-option label="GPT-3.5 Turbo" value="gpt-3.5-turbo"></el-option>
                </el-option-group>
                <el-option-group label="MiniMax">
                  <el-option label="MiniMax-Text-01" value="MiniMax-Text-01"></el-option>
                </el-option-group>
              </el-select>
              <div style="color: #909399; font-size: 12px; margin-top: 5px;">
                推荐：阿里云百炼通义千问-Turbo（性价比高）
              </div>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="saveOpenAI" :loading="saving">保存配置</el-button>
              <el-button @click="verifyOpenAI" :loading="verifying">验证配置</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>

      <!-- 阿里云OSS配置 -->
      <el-tab-pane label="阿里云OSS" name="oss">
        <el-card>
          <el-form :model="ossForm" label-width="150px">
            <el-form-item label="Access Key ID">
              <el-input v-model="ossForm.access_key_id" placeholder="LTAI..."></el-input>
            </el-form-item>
            <el-form-item label="Access Key Secret">
              <el-input v-model="ossForm.access_key_secret" type="password" show-password></el-input>
            </el-form-item>
            <el-form-item label="Endpoint">
              <el-input v-model="ossForm.endpoint" placeholder="oss-cn-hangzhou.aliyuncs.com"></el-input>
            </el-form-item>
            <el-form-item label="Bucket Name">
              <el-input v-model="ossForm.bucket_name" placeholder="my-bucket"></el-input>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="saveOSS" :loading="saving">保存配置</el-button>
              <el-button @click="verifyOSS" :loading="verifying">验证配置</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>

      <!-- 邮箱配置 -->
      <el-tab-pane label="邮箱配置" name="imap">
        <el-card>
          <el-form :model="imapForm" label-width="120px">
            <el-form-item label="IMAP服务器">
              <el-input v-model="imapForm.host" placeholder="imap.example.com"></el-input>
            </el-form-item>
            <el-form-item label="端口">
              <el-input v-model="imapForm.port" placeholder="993"></el-input>
            </el-form-item>
            <el-form-item label="邮箱账号">
              <el-input v-model="imapForm.user" placeholder="user@example.com"></el-input>
            </el-form-item>
            <el-form-item label="密码">
              <el-input v-model="imapForm.password" type="password" show-password></el-input>
            </el-form-item>
            <el-form-item label="使用SSL">
              <el-switch v-model="imapForm.use_ssl"></el-switch>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="saveIMAP" :loading="saving">保存配置</el-button>
              <el-button @click="verifyIMAP" :loading="verifying">验证配置</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>

      <!-- WordPress站点 -->
      <el-tab-pane label="WordPress站点" name="wordpress">
        <el-card>
          <div style="margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center;">
            <div>
              <el-tag type="success">共 {{ wpSites.length }} 个站点</el-tag>
            </div>
            <el-button type="primary" @click="showAddSite = true" icon="Plus">添加站点</el-button>
          </div>
          <el-table :data="wpSites" v-loading="loadingSites" stripe border>
            <el-table-column prop="id" label="ID" width="60"></el-table-column>
            <el-table-column prop="name" label="站点名称" width="150"></el-table-column>
            <el-table-column prop="url" label="URL" min-width="180"></el-table-column>
            <el-table-column prop="api_username" label="用户名" width="100"></el-table-column>
            <el-table-column label="状态" width="80" align="center">
              <template #default="{ row }">
                <el-tag :type="row.active ? 'success' : 'danger'" size="small">
                  {{ row.active ? '激活' : '禁用' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="200" align="center" fixed="right">
              <template #default="{ row }">
                <el-button type="primary" size="small" @click="testConnection(row)" :loading="testing === row.id">测试</el-button>
                <el-button type="warning" size="small" @click="editSite(row)">编辑</el-button>
                <el-button type="danger" size="small" @click="deleteSite(row.id)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <!-- 添加WordPress站点对话框 -->
    <el-dialog v-model="showAddSite" title="添加WordPress站点" width="500px">
      <el-form :model="newSite" label-width="120px">
        <el-form-item label="站点名称">
          <el-input v-model="newSite.name" placeholder="例如：荣耀测试"></el-input>
        </el-form-item>
        <el-form-item label="站点URL">
          <el-input v-model="newSite.url" placeholder="http://a.com"></el-input>
        </el-form-item>
        <el-form-item label="用户名">
          <el-input v-model="newSite.api_username" placeholder="admin"></el-input>
        </el-form-item>
        <el-form-item label="应用程序密码">
          <el-input v-model="newSite.api_password" type="password" show-password placeholder="xxxx xxxx xxxx xxxx"></el-input>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddSite = false">取消</el-button>
        <el-button type="primary" @click="addSite" :loading="saving">添加</el-button>
      </template>
    </el-dialog>

    <!-- 编辑WordPress站点对话框 -->
    <el-dialog v-model="showEditSite" title="编辑WordPress站点" width="500px">
      <el-form :model="editingSite" label-width="120px">
        <el-form-item label="站点名称">
          <el-input v-model="editingSite.name" placeholder="例如：荣耀测试"></el-input>
        </el-form-item>
        <el-form-item label="站点URL">
          <el-input v-model="editingSite.url" placeholder="http://a.com"></el-input>
        </el-form-item>
        <el-form-item label="用户名">
          <el-input v-model="editingSite.api_username" placeholder="admin"></el-input>
        </el-form-item>
        <el-form-item label="应用程序密码">
          <el-input v-model="editingSite.api_password" type="password" show-password placeholder="留空则不修改"></el-input>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditSite = false">取消</el-button>
        <el-button type="primary" @click="updateSite" :loading="saving">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import request from '../api/request'

const activeTab = ref('openai')
const saving = ref(false)
const verifying = ref(false)
const loadingSites = ref(false)
const testing = ref(0)
const showAddSite = ref(false)
const showEditSite = ref(false)
const showModelHelp = ref(false)

const openaiForm = ref({ api_key: '', base_url: '', model: 'gpt-4' })
const ossForm = ref({ access_key_id: '', access_key_secret: '', endpoint: '', bucket_name: '' })
const imapForm = ref({ host: '', port: '993', user: '', password: '', use_ssl: true })
const wpSites = ref([])
const newSite = ref({ name: '', url: '', api_username: '', api_password: '' })
const editingSite = ref({ id: 0, name: '', url: '', api_username: '', api_password: '' })

const loadConfigs = async () => {
  try {
    const data = await request.get('/config/')
    const configs = data.configs || {}
    openaiForm.value.api_key = configs.OPENAI_API_KEY || ''
    openaiForm.value.base_url = configs.OPENAI_BASE_URL || ''
    openaiForm.value.model = configs.OPENAI_MODEL || 'gpt-4'
    ossForm.value.access_key_id = configs.OSS_ACCESS_KEY_ID || ''
    ossForm.value.endpoint = configs.OSS_ENDPOINT || ''
    ossForm.value.bucket_name = configs.OSS_BUCKET_NAME || ''
    imapForm.value.host = configs.IMAP_HOST || ''
    imapForm.value.port = configs.IMAP_PORT || '993'
    imapForm.value.user = configs.IMAP_USER || ''
    imapForm.value.use_ssl = configs.IMAP_USE_SSL !== 'false'
  } catch (error) {
    console.error('加载配置失败:', error)
    ElMessage.error('加载配置失败')
  }
}

const loadWPSites = async () => {
  loadingSites.value = true
  try {
    const data = await request.get('/wordpress-sites')
    wpSites.value = data.sites || []
  } catch (error) {
    console.error('加载站点失败:', error)
    ElMessage.error('加载站点失败')
  } finally {
    loadingSites.value = false
  }
}

const saveOpenAI = async () => {
  saving.value = true
  try {
    await request.put('/config/', { key: 'OPENAI_API_KEY', value: openaiForm.value.api_key, encrypted: true })
    if (openaiForm.value.base_url) {
      await request.put('/config/', { key: 'OPENAI_BASE_URL', value: openaiForm.value.base_url, encrypted: false })
    }
    await request.put('/config/', { key: 'OPENAI_MODEL', value: openaiForm.value.model, encrypted: false })
    ElMessage.success('保存成功')
  } catch (error) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

const verifyOpenAI = async () => {
  verifying.value = true
  try {
    const data = await request.post('/config/verify/llm')
    ElMessage[data.valid ? 'success' : 'error'](data.message)
  } catch (error) {
    ElMessage.error('验证失败')
  } finally {
    verifying.value = false
  }
}

const saveOSS = async () => {
  saving.value = true
  try {
    await request.put('/config/', { key: 'OSS_ACCESS_KEY_ID', value: ossForm.value.access_key_id, encrypted: true })
    await request.put('/config/', { key: 'OSS_ACCESS_KEY_SECRET', value: ossForm.value.access_key_secret, encrypted: true })
    await request.put('/config/', { key: 'OSS_ENDPOINT', value: ossForm.value.endpoint, encrypted: false })
    await request.put('/config/', { key: 'OSS_BUCKET_NAME', value: ossForm.value.bucket_name, encrypted: false })
    ElMessage.success('保存成功')
  } catch (error) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

const verifyOSS = async () => {
  verifying.value = true
  try {
    const data = await request.post('/config/verify/oss')
    ElMessage[data.valid ? 'success' : 'error'](data.message)
  } catch (error) {
    ElMessage.error('验证失败')
  } finally {
    verifying.value = false
  }
}

const saveIMAP = async () => {
  saving.value = true
  try {
    await request.put('/config/', { key: 'IMAP_HOST', value: imapForm.value.host, encrypted: false })
    await request.put('/config/', { key: 'IMAP_PORT', value: imapForm.value.port, encrypted: false })
    await request.put('/config/', { key: 'IMAP_USER', value: imapForm.value.user, encrypted: false })
    await request.put('/config/', { key: 'IMAP_PASSWORD', value: imapForm.value.password, encrypted: true })
    await request.put('/config/', { key: 'IMAP_USE_SSL', value: imapForm.value.use_ssl.toString(), encrypted: false })
    ElMessage.success('保存成功')
  } catch (error) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

const verifyIMAP = async () => {
  verifying.value = true
  try {
    const data = await request.post('/config/verify/imap')
    ElMessage[data.valid ? 'success' : 'error'](data.message)
  } catch (error) {
    ElMessage.error('验证失败')
  } finally {
    verifying.value = false
  }
}

// 预设配置
const useAliyunPreset = () => {
  openaiForm.value.base_url = 'https://dashscope.aliyuncs.com/compatible-mode/v1'
  openaiForm.value.model = 'qwen-turbo'
  ElMessage.success('已应用阿里云百炼预设配置（推荐）')
}

const useMinimaxPreset = () => {
  openaiForm.value.base_url = 'https://api.minimaxi.com/v1'
  openaiForm.value.model = 'MiniMax-Text-01'
  ElMessage.success('已应用MiniMax预设配置')
}

const useOpenRouterPreset = () => {
  openaiForm.value.base_url = 'https://openrouter.ai/api/v1'
  openaiForm.value.model = 'meta-llama/llama-3.3-70b-instruct:free'
  ElMessage.success('已应用OpenRouter预设配置（免费）')
}

const useOpenAIPreset = () => {
  openaiForm.value.base_url = ''
  openaiForm.value.model = 'gpt-4'
  ElMessage.success('已应用OpenAI官方预设配置')
}

const addSite = async () => {
  saving.value = true
  try {
    await request.post('/wordpress-sites', newSite.value)
    ElMessage.success('添加成功')
    showAddSite.value = false
    newSite.value = { name: '', url: '', api_username: '', api_password: '' }
    loadWPSites()
  } catch (error) {
    ElMessage.error('添加失败')
  } finally {
    saving.value = false
  }
}

const editSite = (site) => {
  editingSite.value = {
    id: site.id,
    name: site.name,
    url: site.url,
    api_username: site.api_username,
    api_password: ''
  }
  showEditSite.value = true
}

const updateSite = async () => {
  saving.value = true
  try {
    const updateData = {
      name: editingSite.value.name,
      url: editingSite.value.url,
      api_username: editingSite.value.api_username
    }
    if (editingSite.value.api_password) {
      updateData.api_password = editingSite.value.api_password
    }
    await request.put(`/wordpress-sites/${editingSite.value.id}`, updateData)
    ElMessage.success('更新成功')
    showEditSite.value = false
    loadWPSites()
  } catch (error) {
    ElMessage.error('更新失败')
  } finally {
    saving.value = false
  }
}

const testConnection = async (site) => {
  testing.value = site.id
  try {
    const data = await request.post(`/wordpress-sites/${site.id}/test`)
    if (data.valid) {
      ElMessage.success(data.message || '连接成功')
    } else {
      ElMessage.error(data.message || '连接失败')
    }
  } catch (error) {
    ElMessage.error('测试连接失败')
  } finally {
    testing.value = 0
  }
}

const deleteSite = async (id) => {
  try {
    await request.delete(`/wordpress-sites/${id}`)
    ElMessage.success('删除成功')
    loadWPSites()
  } catch (error) {
    ElMessage.error('删除失败')
  }
}

onMounted(() => {
  loadConfigs()
  loadWPSites()
})
</script>

<style scoped>
.config-view {
  padding: 20px;
}

.page-title {
  font-size: 18px;
  font-weight: 500;
}
</style>
