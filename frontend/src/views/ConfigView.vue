<template>
  <div class="config-view">
    <el-page-header @back="$router.back()">
      <template #content>
        <span class="page-title">系统配置</span>
      </template>
    </el-page-header>
    
    <el-tabs v-model="activeTab" style="margin-top: 20px">
      <!-- AI配置（阿里云百炼） -->
      <el-tab-pane label="AI配置" name="openai">
        <el-card>
          <el-alert title="阿里云百炼（通义千问）" type="info" :closable="false" style="margin-bottom: 20px">
            登录 <a href="https://bailian.console.aliyun.com/" target="_blank">阿里云百炼控制台</a> 获取 API Key
          </el-alert>
          
          <el-form :model="openaiForm" label-width="150px">
            <el-form-item label="API Key">
              <el-input v-model="openaiForm.api_key" type="password" show-password placeholder="sk-..."></el-input>
            </el-form-item>
            <el-form-item label="模型">
              <el-select v-model="openaiForm.model" placeholder="选择模型">
                <el-option label="通义千问-Plus（推荐）" value="qwen-plus"></el-option>
                <el-option label="通义千问-Turbo（速度快）" value="qwen-turbo"></el-option>
                <el-option label="通义千问-Max（效果最好）" value="qwen-max"></el-option>
                <el-option label="通义千问-Long（长文本）" value="qwen-long"></el-option>
              </el-select>
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
            <div>
              <el-button type="info" @click="testAllConnections" :loading="testingAll" style="margin-right: 8px;">批量测试连接</el-button>
              <el-button type="primary" @click="showAddSite = true" icon="Plus">添加站点</el-button>
            </div>
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

      <!-- 采编映射：邮箱 -> 采编姓名（责编署名） -->
      <el-tab-pane label="采编映射" name="editors">
        <el-card>
          <el-alert title="邮箱或邮箱前缀对应采编姓名，发布文章时自动署名「责编」" type="info" :closable="false" style="margin-bottom: 20px" />
          <el-button type="primary" @click="showAddEditor = true" style="margin-bottom: 12px">添加映射</el-button>
          <el-table :data="editorMappings" v-loading="loadingEditors" stripe border>
            <el-table-column prop="email" label="邮箱/前缀" width="200" />
            <el-table-column prop="display_name" label="采编姓名" width="120" />
            <el-table-column label="操作" width="150">
              <template #default="{ row }">
                <el-button type="primary" link size="small" @click="editEditorMapping(row)">编辑</el-button>
                <el-button type="danger" link size="small" @click="removeEditorMapping(row.id)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>

      <!-- 文编映射：用户在各站点下的署名 -->
      <el-tab-pane label="文编映射" name="copyEditors">
        <el-card>
          <el-alert title="编辑人员在不同站点下的署名，发布时自动署名「文编」" type="info" :closable="false" style="margin-bottom: 20px" />
          <el-button type="primary" @click="showAddCopyEditor = true" style="margin-bottom: 12px">添加映射</el-button>
          <el-table :data="copyEditorMappings" v-loading="loadingCopyEditors" stripe border>
            <el-table-column prop="user_id" label="用户ID" width="90" />
            <el-table-column prop="site_name" label="站点" width="140" />
            <el-table-column prop="display_name" label="文编署名" width="120" />
            <el-table-column label="操作" width="150">
              <template #default="{ row }">
                <el-button type="primary" link size="small" @click="editCopyEditorMapping(row)">编辑</el-button>
                <el-button type="danger" link size="small" @click="removeCopyEditorMapping(row.id)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>

      <!-- 媒体与站点映射 -->
      <el-tab-pane label="媒体映射" name="media">
        <el-card>
          <el-alert title="配置媒体类型与WordPress站点的对应关系" type="info" :closable="false" style="margin-bottom: 20px">
            邮件中解析的"媒体"类型将自动映射到对应的WordPress站点
          </el-alert>
          
          <el-table :data="mediaMappings" v-loading="loadingMappings" stripe border>
            <el-table-column label="媒体类型" width="150">
              <template #default="{ row }">
                <el-tag>{{ getMediaTypeName(row.media_type) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="对应站点" min-width="200">
              <template #default="{ row }">
                <el-select 
                  v-model="row.site_id" 
                  placeholder="选择站点"
                  @change="updateMapping(row.media_type, row.site_id)"
                  style="width: 100%"
                >
                  <el-option 
                    v-for="site in wpSites.filter(s => s.active)" 
                    :key="site.id" 
                    :label="site.name" 
                    :value="site.id"
                  />
                </el-select>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="100" align="center">
              <template #default="{ row }">
                <el-button 
                  type="danger" 
                  size="small" 
                  @click="deleteMapping(row.media_type)"
                  v-if="row.site_id"
                >
                  清除
                </el-button>
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

    <!-- 采编映射 添加/编辑 -->
    <el-dialog v-model="showAddEditor" title="添加采编映射" width="420px" @open="loadEditorEmailOptions">
      <el-form :model="editorForm" label-width="100px">
        <el-form-item label="邮箱/前缀">
          <el-select
            v-model="editorForm.email"
            filterable
            allow-create
            default-first-option
            placeholder="选择历史或输入新邮箱/前缀"
            style="width: 100%"
          >
            <el-option v-for="opt in editorEmailOptions" :key="opt" :label="opt" :value="opt" />
          </el-select>
        </el-form-item>
        <el-form-item label="采编姓名">
          <el-input v-model="editorForm.display_name" placeholder="责编署名" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddEditor = false">取消</el-button>
        <el-button type="primary" @click="submitEditorMapping" :loading="saving">确定</el-button>
      </template>
    </el-dialog>
    <el-dialog v-model="showEditEditor" title="编辑采编映射" width="420px">
      <el-form :model="editorForm" label-width="100px">
        <el-form-item label="邮箱/前缀">
          <el-input v-model="editorForm.email" disabled />
        </el-form-item>
        <el-form-item label="采编姓名">
          <el-input v-model="editorForm.display_name" placeholder="责编署名" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditEditor = false">取消</el-button>
        <el-button type="primary" @click="updateEditorMappingSubmit" :loading="saving">保存</el-button>
      </template>
    </el-dialog>

    <!-- 文编映射 添加 -->
    <el-dialog v-model="showAddCopyEditor" title="添加文编映射" width="420px">
      <el-form :model="copyEditorForm" label-width="100px">
        <el-form-item label="用户">
          <el-select v-model="copyEditorForm.user_id" placeholder="选择用户" style="width:100%" filterable>
            <el-option v-for="u in usersList" :key="u.id" :label="u.username + (u.display_name ? ' (' + u.display_name + ')' : '')" :value="u.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="站点">
          <el-select v-model="copyEditorForm.site_id" placeholder="选择站点" style="width:100%">
            <el-option v-for="s in wpSites" :key="s.id" :label="s.name" :value="s.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="文编署名">
          <el-input v-model="copyEditorForm.display_name" placeholder="该站点下显示的名称" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddCopyEditor = false">取消</el-button>
        <el-button type="primary" @click="submitCopyEditorMapping" :loading="saving">确定</el-button>
      </template>
    </el-dialog>
    <el-dialog v-model="showEditCopyEditor" title="编辑文编映射" width="420px">
      <el-form :model="copyEditorForm" label-width="100px">
        <el-form-item label="站点">
          <el-input :value="copyEditorForm.site_name" disabled />
        </el-form-item>
        <el-form-item label="文编署名">
          <el-input v-model="copyEditorForm.display_name" placeholder="该站点下显示的名称" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditCopyEditor = false">取消</el-button>
        <el-button type="primary" @click="updateCopyEditorMappingSubmit" :loading="saving">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import request from '../api/request'
import { getMediaMappings, updateMediaMapping, deleteMediaMapping } from '../api/mediaMapping'
import {
  listEditorMappings,
  getEditorEmailOptions,
  createEditorMapping,
  updateEditorMapping,
  deleteEditorMapping,
  listCopyEditorMappings,
  createCopyEditorMapping,
  updateCopyEditorMapping,
  deleteCopyEditorMapping
} from '../api/nameMappings'
import { getUsers } from '../api/user'

const activeTab = ref('openai')
const saving = ref(false)
const verifying = ref(false)
const loadingSites = ref(false)
const loadingMappings = ref(false)
const testing = ref(0)
const testingAll = ref(false)
const showAddSite = ref(false)
const showEditSite = ref(false)
const DASHSCOPE_BASE_URL = 'https://dashscope.aliyuncs.com/compatible-mode/v1'
const openaiForm = ref({ api_key: '', model: 'qwen-plus' })
const ossForm = ref({ access_key_id: '', access_key_secret: '', endpoint: '', bucket_name: '' })
const imapForm = ref({ host: '', port: '993', user: '', password: '', use_ssl: true })
const wpSites = ref([])
const mediaMappings = ref([
  { media_type: 'rongyao', site_id: null },
  { media_type: 'shidai', site_id: null },
  { media_type: 'zhengxian', site_id: null },
  { media_type: 'zhengqi', site_id: null },
  { media_type: 'toutiao', site_id: null }
])
const newSite = ref({ name: '', url: '', api_username: '', api_password: '' })
const editingSite = ref({ id: 0, name: '', url: '', api_username: '', api_password: '' })
const loadingEditors = ref(false)
const loadingCopyEditors = ref(false)
const editorMappings = ref([])
const editorEmailOptions = ref([])
const copyEditorMappings = ref([])
const usersList = ref([])
const showAddEditor = ref(false)
const showEditEditor = ref(false)
const editorForm = ref({ id: null, email: '', display_name: '' })
const showAddCopyEditor = ref(false)
const showEditCopyEditor = ref(false)
const copyEditorForm = ref({ id: null, user_id: null, site_id: null, site_name: '', display_name: '' })

const loadConfigs = async () => {
  try {
    const data = await request.get('/config/')
    const configs = data.configs || {}
    openaiForm.value.api_key = configs.OPENAI_API_KEY || ''
    openaiForm.value.model = configs.OPENAI_MODEL || 'qwen-plus'
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
    await request.put('/config/', { key: 'OPENAI_BASE_URL', value: DASHSCOPE_BASE_URL, encrypted: false })
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

const testAllConnections = async () => {
  testingAll.value = true
  try {
    const data = await request.post('/wordpress-sites/test-all?active_only=true')
    const results = data.results || []
    const ok = results.filter(r => r.valid).length
    const fail = results.filter(r => !r.valid).length
    if (fail === 0) {
      ElMessage.success(`全部 ${ok} 个站点连接成功`)
    } else {
      const details = results.map(r => `${r.name}: ${r.valid ? '成功' : r.message || '失败'}`).join('；')
      ElMessage.warning(`${ok} 成功，${fail} 失败。${details}`)
    }
  } catch (error) {
    ElMessage.error('批量测试失败')
  } finally {
    testingAll.value = false
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

// 媒体映射相关方法
const getMediaTypeName = (type) => {
  const names = {
    'rongyao': '荣耀网',
    'shidai': '时代网',
    'zhengxian': '争先网',
    'zhengqi': '政企网',
    'toutiao': '今日头条'
  }
  return names[type] || type
}

const loadEditorMappings = async () => {
  loadingEditors.value = true
  try {
    editorMappings.value = await listEditorMappings()
  } catch (e) {
    ElMessage.error('加载采编映射失败')
  } finally {
    loadingEditors.value = false
  }
}

const loadEditorEmailOptions = async () => {
  try {
    editorEmailOptions.value = await getEditorEmailOptions()
  } catch (e) {
    editorEmailOptions.value = []
  }
}

const loadCopyEditorMappings = async () => {
  loadingCopyEditors.value = true
  try {
    copyEditorMappings.value = await listCopyEditorMappings()
  } catch (e) {
    ElMessage.error('加载文编映射失败')
  } finally {
    loadingCopyEditors.value = false
  }
}

const submitEditorMapping = async () => {
  if (!editorForm.value.email?.trim() || !editorForm.value.display_name?.trim()) {
    ElMessage.warning('请填写邮箱和采编姓名')
    return
  }
  saving.value = true
  try {
    await createEditorMapping({ email: editorForm.value.email.trim(), display_name: editorForm.value.display_name.trim() })
    ElMessage.success('添加成功')
    showAddEditor.value = false
    editorForm.value = { id: null, email: '', display_name: '' }
    loadEditorMappings()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '添加失败')
  } finally {
    saving.value = false
  }
}

const editEditorMapping = (row) => {
  editorForm.value = { id: row.id, email: row.email, display_name: row.display_name }
  showEditEditor.value = true
}

const updateEditorMappingSubmit = async () => {
  if (!editorForm.value.display_name?.trim()) {
    ElMessage.warning('请填写采编姓名')
    return
  }
  saving.value = true
  try {
    await updateEditorMapping(editorForm.value.id, { display_name: editorForm.value.display_name.trim() })
    ElMessage.success('保存成功')
    showEditEditor.value = false
    loadEditorMappings()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

const removeEditorMapping = async (id) => {
  try {
    await deleteEditorMapping(id)
    ElMessage.success('已删除')
    loadEditorMappings()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '删除失败')
  }
}

const submitCopyEditorMapping = async () => {
  if (!copyEditorForm.value.user_id || !copyEditorForm.value.site_id || !copyEditorForm.value.display_name?.trim()) {
    ElMessage.warning('请选择用户、站点并填写文编署名')
    return
  }
  saving.value = true
  try {
    await createCopyEditorMapping({
      user_id: copyEditorForm.value.user_id,
      site_id: copyEditorForm.value.site_id,
      display_name: copyEditorForm.value.display_name.trim()
    })
    ElMessage.success('添加成功')
    showAddCopyEditor.value = false
    copyEditorForm.value = { id: null, user_id: null, site_id: null, site_name: '', display_name: '' }
    loadCopyEditorMappings()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '添加失败')
  } finally {
    saving.value = false
  }
}

const editCopyEditorMapping = (row) => {
  copyEditorForm.value = { id: row.id, user_id: row.user_id, site_id: row.site_id, site_name: row.site_name || '', display_name: row.display_name }
  showEditCopyEditor.value = true
}

const updateCopyEditorMappingSubmit = async () => {
  if (!copyEditorForm.value.display_name?.trim()) {
    ElMessage.warning('请填写文编署名')
    return
  }
  saving.value = true
  try {
    await updateCopyEditorMapping(copyEditorForm.value.id, { display_name: copyEditorForm.value.display_name.trim() })
    ElMessage.success('保存成功')
    showEditCopyEditor.value = false
    loadCopyEditorMappings()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

const removeCopyEditorMapping = async (id) => {
  try {
    await deleteCopyEditorMapping(id)
    ElMessage.success('已删除')
    loadCopyEditorMappings()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '删除失败')
  }
}

const loadMediaMappings = async () => {
  loadingMappings.value = true
  try {
    const data = await getMediaMappings()
    // 合并数据库中的映射到默认列表
    mediaMappings.value.forEach(m => {
      const found = data.find(d => d.media_type === m.media_type)
      if (found) {
        m.site_id = found.site_id
      }
    })
  } catch (error) {
    ElMessage.error('加载媒体映射失败')
  } finally {
    loadingMappings.value = false
  }
}

const updateMapping = async (mediaType, siteId) => {
  try {
    await updateMediaMapping(mediaType, siteId)
    ElMessage.success('映射已更新')
  } catch (error) {
    ElMessage.error('更新失败')
  }
}

const deleteMapping = async (mediaType) => {
  try {
    await deleteMediaMapping(mediaType)
    const mapping = mediaMappings.value.find(m => m.media_type === mediaType)
    if (mapping) {
      mapping.site_id = null
    }
    ElMessage.success('映射已清除')
  } catch (error) {
    ElMessage.error('清除失败')
  }
}

const loadUsers = async () => {
  try {
    const res = await getUsers({ page: 1, size: 500 })
    usersList.value = res.items || []
  } catch (e) {
    console.error('加载用户列表失败', e)
  }
}

onMounted(() => {
  loadConfigs()
  loadWPSites()
  loadMediaMappings()
  loadEditorMappings()
  loadCopyEditorMappings()
  loadUsers()
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
