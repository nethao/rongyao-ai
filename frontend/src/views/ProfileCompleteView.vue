<template>
  <div class="profile-complete-container">
    <el-card class="complete-card">
      <template #header>
        <div class="card-header">
          <h2>首次登录请完善信息</h2>
          <p class="tip">编辑人员须完成以下三项后才能使用系统</p>
        </div>
      </template>

      <el-steps :active="activeStep" finish-status="success" align-center class="steps">
        <el-step title="修改密码" />
        <el-step title="填写显示名" />
        <el-step title="文编署名映射" />
      </el-steps>

      <!-- 1. 修改密码 -->
      <div v-show="activeStep === 0" class="step-block">
        <el-form ref="pwdFormRef" :model="pwdForm" :rules="pwdRules" label-width="100px" style="max-width: 400px">
          <el-form-item label="当前密码" prop="old_password">
            <el-input v-model="pwdForm.old_password" type="password" show-password placeholder="当前密码" />
          </el-form-item>
          <el-form-item label="新密码" prop="new_password">
            <el-input v-model="pwdForm.new_password" type="password" show-password placeholder="至少6位" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="submitPassword" :loading="savingPwd">保存密码</el-button>
          </el-form-item>
        </el-form>
      </div>

      <!-- 2. 填写显示名 -->
      <div v-show="activeStep === 1" class="step-block">
        <el-form label-width="100px" style="max-width: 400px">
          <el-form-item label="显示名" required>
            <el-input v-model="displayName" placeholder="用于认领与署名显示" maxlength="50" show-word-limit />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="saveDisplayName" :loading="savingName">保存显示名</el-button>
          </el-form-item>
        </el-form>
      </div>

      <!-- 3. 文编署名映射 -->
      <div v-show="activeStep === 2" class="step-block">
        <el-alert
          title="请至少添加一条文编署名映射，发布文章时将自动署名「文编」"
          type="info"
          :closable="false"
          show-icon
          style="margin-bottom: 16px"
        />
        <el-button type="primary" size="small" @click="openAddMapping" style="margin-bottom: 12px">添加文编署名</el-button>
        <el-table :data="profile.copy_editor_mappings" stripe border style="width: 100%">
          <el-table-column label="站点" width="220">
            <template #default="{ row }">
              {{ row.site_name || '-' }}
              <span style="color: #909399; font-size: 12px">(ID: {{ row.site_id }})</span>
            </template>
          </el-table-column>
          <el-table-column prop="display_name" label="文编署名" width="140" />
          <el-table-column label="操作" width="140">
            <template #default="{ row }">
              <el-button type="primary" link size="small" @click="editMapping(row)">编辑</el-button>
              <el-button type="danger" link size="small" @click="removeMapping(row.id)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <el-dialog v-model="showMappingDialog" :title="editingMappingId ? '编辑文编署名' : '添加文编署名'" width="420px">
        <el-form :model="mappingForm" label-width="100px">
          <el-form-item v-if="!editingMappingId" label="站点">
            <el-select v-model="mappingForm.site_id" placeholder="选择站点" style="width:100%">
              <el-option v-for="s in sites" :key="s.id" :label="s.name" :value="s.id" />
            </el-select>
          </el-form-item>
          <el-form-item v-else label="站点">
            <el-input :value="mappingForm.site_name" disabled />
          </el-form-item>
          <el-form-item label="文编署名">
            <el-input v-model="mappingForm.display_name" placeholder="在该站点下显示的名称" />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="showMappingDialog = false">取消</el-button>
          <el-button type="primary" @click="submitMapping" :loading="savingMap">确定</el-button>
        </template>
      </el-dialog>

      <div class="footer-actions">
        <el-button v-if="activeStep > 0" @click="activeStep--">上一步</el-button>
        <el-button v-if="activeStep < 2" type="primary" @click="activeStep++">下一步</el-button>
        <el-button
          v-if="activeStep === 2"
          type="success"
          :disabled="!allComplete"
          :loading="checking"
          @click="handleComplete"
        >
          完成并进入系统
        </el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import request from '../api/request'
import { getProfileCompleteStatus } from '../api/auth'
import {
  getMyProfile,
  updateMyProfile,
  createCopyEditorMapping,
  updateCopyEditorMapping,
  deleteCopyEditorMapping,
  changeMyPassword
} from '../api/nameMappings'

const router = useRouter()
const profile = ref({ user: null, copy_editor_mappings: [] })
const sites = ref([])
const activeStep = ref(0)
const displayName = ref('')
const pwdForm = ref({ old_password: '', new_password: '' })
const pwdFormRef = ref(null)
const savingPwd = ref(false)
const savingName = ref(false)
const savingMap = ref(false)
const editingMappingId = ref(null)
const showMappingDialog = ref(false)
const mappingForm = ref({ site_id: null, site_name: '', display_name: '' })
const checking = ref(false)

const pwdRules = {
  old_password: [{ required: true, message: '请输入当前密码', trigger: 'blur' }],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '至少6位', trigger: 'blur' }
  ]
}

const allComplete = computed(() => {
  const u = profile.value.user
  if (!u) return false
  const pwdOk = !u.must_change_password
  const nameOk = !!(u.display_name && String(u.display_name).trim())
  const mappingOk = (profile.value.copy_editor_mappings || []).length >= 1
  return pwdOk && nameOk && mappingOk
})

const loadProfile = async () => {
  try {
    profile.value = await getMyProfile()
    displayName.value = (profile.value.user?.display_name || '').trim()
  } catch (e) {
    ElMessage.error('加载失败')
  }
}

const loadSites = async () => {
  try {
    const data = await request.get('/wordpress-sites')
    sites.value = data.sites || []
  } catch (e) {
    console.error('加载站点失败', e)
  }
}

const submitPassword = async () => {
  if (!pwdFormRef.value) return
  await pwdFormRef.value.validate(async (valid) => {
    if (!valid) return
    savingPwd.value = true
    try {
      await changeMyPassword({
        old_password: pwdForm.value.old_password,
        new_password: pwdForm.value.new_password
      })
      ElMessage.success('密码已修改')
      pwdForm.value = { old_password: '', new_password: '' }
      await loadProfile()
    } catch (e) {
      ElMessage.error(e.response?.data?.detail || '修改失败')
    } finally {
      savingPwd.value = false
    }
  })
}

const saveDisplayName = async () => {
  const name = (displayName.value || '').trim()
  if (!name) {
    ElMessage.warning('请填写显示名')
    return
  }
  savingName.value = true
  try {
    await updateMyProfile({ display_name: name })
    ElMessage.success('保存成功')
    await loadProfile()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally {
    savingName.value = false
  }
}

const openAddMapping = () => {
  editingMappingId.value = null
  mappingForm.value = { site_id: null, site_name: '', display_name: '' }
  showMappingDialog.value = true
}

const editMapping = (row) => {
  editingMappingId.value = row.id
  mappingForm.value = { site_id: row.site_id, site_name: row.site_name, display_name: row.display_name }
  showMappingDialog.value = true
}

const submitMapping = async () => {
  if (!mappingForm.value.display_name?.trim()) {
    ElMessage.warning('请填写文编署名')
    return
  }
  if (!editingMappingId.value && !mappingForm.value.site_id) {
    ElMessage.warning('请选择站点')
    return
  }
  savingMap.value = true
  try {
    if (editingMappingId.value) {
      await updateCopyEditorMapping(editingMappingId.value, {
        display_name: mappingForm.value.display_name.trim()
      })
      ElMessage.success('保存成功')
    } else {
      await createCopyEditorMapping({
        user_id: profile.value.user.id,
        site_id: mappingForm.value.site_id,
        display_name: mappingForm.value.display_name.trim()
      })
      ElMessage.success('添加成功')
    }
    showMappingDialog.value = false
    await loadProfile()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  } finally {
    savingMap.value = false
  }
}

const removeMapping = async (id) => {
  try {
    await deleteCopyEditorMapping(id)
    ElMessage.success('已删除')
    await loadProfile()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '删除失败')
  }
}

const handleComplete = async () => {
  if (!allComplete.value) return
  checking.value = true
  try {
    const res = await getProfileCompleteStatus()
    if (res.complete) {
      ElMessage.success('已完善，进入系统')
      router.replace('/submissions')
    } else {
      ElMessage.warning('请完成全部三项后再进入')
      await loadProfile()
    }
  } catch (e) {
    ElMessage.error('验证失败')
  } finally {
    checking.value = false
  }
}

onMounted(() => {
  loadProfile()
  loadSites()
})
</script>

<style scoped>
.profile-complete-container {
  min-height: 100vh;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 40px 20px;
  background: #f5f7fa;
}
.complete-card {
  width: 100%;
  max-width: 640px;
}
.card-header h2 {
  margin: 0 0 8px 0;
  font-size: 20px;
}
.card-header .tip {
  margin: 0;
  color: #909399;
  font-size: 14px;
}
.steps {
  margin-bottom: 32px;
}
.step-block {
  min-height: 200px;
  margin-bottom: 24px;
}
.footer-actions {
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid #ebeef5;
  display: flex;
  gap: 12px;
  justify-content: center;
}
</style>
