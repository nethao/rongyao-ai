<template>
  <div class="profile-view">
    <el-page-header @back="$router.back()">
      <template #content>
        <span class="page-title">个人中心</span>
      </template>
    </el-page-header>

    <el-card class="profile-card" style="margin-top: 20px">
      <template #header>
        <span>基本信息</span>
      </template>
      <el-descriptions :column="1" border>
        <el-descriptions-item label="用户名">{{ profile.user?.username }}</el-descriptions-item>
        <el-descriptions-item label="显示名（认领/登录）">{{ profile.user?.display_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="角色">{{ profile.user?.role === 'admin' ? '管理员' : '编辑人员' }}</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <el-card class="profile-card" style="margin-top: 20px">
      <template #header>
        <span>文编署名映射</span>
        <el-button type="primary" size="small" style="float: right" @click="openAddMapping">添加</el-button>
      </template>
      <el-alert
        v-if="isFirst"
        title="请完善您在各个站点下的文编署名，发布文章时将自动署名「文编」"
        type="warning"
        :closable="false"
        show-icon
        style="margin-bottom: 16px"
      />
      <el-table :data="profile.copy_editor_mappings" v-loading="loading" stripe border>
        <el-table-column label="站点" width="220">
          <template #default="{ row }">
            {{ row.site_name || '-' }}
            <span style="color: #909399; font-size: 12px; margin-left: 6px">(ID: {{ row.site_id }})</span>
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
    </el-card>

    <el-card class="profile-card" style="margin-top: 20px">
      <template #header>
        <span>修改密码</span>
      </template>
      <el-form :model="pwdForm" :rules="pwdRules" ref="pwdFormRef" label-width="100px" style="max-width: 400px">
        <el-form-item label="旧密码" prop="old_password">
          <el-input v-model="pwdForm.old_password" type="password" show-password placeholder="当前密码" />
        </el-form-item>
        <el-form-item label="新密码" prop="new_password">
          <el-input v-model="pwdForm.new_password" type="password" show-password placeholder="至少6位" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="submitPassword" :loading="savingPwd">保存密码</el-button>
        </el-form-item>
      </el-form>
    </el-card>

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
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import request from '../api/request'
import {
  getMyProfile,
  listCopyEditorMappings,
  createCopyEditorMapping,
  updateCopyEditorMapping,
  deleteCopyEditorMapping,
  changeMyPassword
} from '../api/nameMappings'

const route = useRoute()
const isFirst = computed(() => route.query.first === '1')
const loading = ref(false)
const profile = ref({ user: null, copy_editor_mappings: [] })
const sites = ref([])
const showMappingDialog = ref(false)
const savingMap = ref(false)
const editingMappingId = ref(null)
const mappingForm = ref({ site_id: null, site_name: '', display_name: '' })
const pwdForm = ref({ old_password: '', new_password: '' })
const pwdFormRef = ref(null)
const savingPwd = ref(false)
const pwdRules = {
  old_password: [{ required: true, message: '请输入旧密码', trigger: 'blur' }],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '至少6位', trigger: 'blur' }
  ]
}

const loadProfile = async () => {
  loading.value = true
  try {
    profile.value = await getMyProfile()
  } catch (e) {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
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
      await updateCopyEditorMapping(editingMappingId.value, { display_name: mappingForm.value.display_name.trim() })
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
    loadProfile()
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
    loadProfile()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '删除失败')
  }
}

const submitPassword = async () => {
  if (!pwdFormRef.value) return
  await pwdFormRef.value.validate(async (valid) => {
    if (!valid) return
    savingPwd.value = true
    try {
      await changeMyPassword({ old_password: pwdForm.value.old_password, new_password: pwdForm.value.new_password })
      ElMessage.success('密码已修改')
      pwdForm.value = { old_password: '', new_password: '' }
    } catch (e) {
      ElMessage.error(e.response?.data?.detail || '修改失败')
    } finally {
      savingPwd.value = false
    }
  })
}

onMounted(() => {
  loadProfile()
  loadSites()
})
</script>

<style scoped>
.profile-view {
  padding: 0 20px 20px;
}
.page-title {
  font-size: 18px;
  font-weight: 600;
}
</style>
