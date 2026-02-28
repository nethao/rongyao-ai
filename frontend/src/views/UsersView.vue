<template>
  <div class="users-view">
    <el-card class="header-card">
      <div class="header-content">
        <h2>用户管理</h2>
        <el-button type="primary" @click="openAddDialog">
          <el-icon><Plus /></el-icon>
          新增用户
        </el-button>
      </div>
    </el-card>

    <el-card class="table-card">
      <el-table
        v-loading="loading"
        :data="users"
        row-key="id"
        style="width: 100%"
      >
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="username" label="用户名" min-width="120" />
        <el-table-column prop="display_name" label="显示名（认领标签）" min-width="100" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.display_name || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="角色" width="100">
          <template #default="{ row }">
            <el-tag :type="row.role === 'admin' ? 'danger' : 'primary'" size="small">
              {{ row.role === 'admin' ? '管理员' : '编辑人员' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="备注" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.id === currentUserId" type="info" size="small">当前用户</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="openEditDialog(row)">
              编辑角色
            </el-button>
            <el-button type="warning" link size="small" @click="openResetPwdDialog(row)">
              重置密码
            </el-button>
            <el-button
              type="danger"
              link
              size="small"
              :disabled="row.id === currentUserId"
              @click="handleDelete(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-container">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="loadUsers"
          @current-change="loadUsers"
        />
      </div>
    </el-card>

    <!-- 新增用户 -->
    <el-dialog
      v-model="addDialogVisible"
      title="新增用户"
      width="420px"
      :close-on-click-modal="false"
      @closed="resetAddForm"
    >
      <el-form ref="addFormRef" :model="addForm" :rules="addRules" label-width="80px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="addForm.username" placeholder="登录用户名" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="addForm.password" type="password" show-password placeholder="至少6位" />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-select v-model="addForm.role" placeholder="选择角色" style="width: 100%">
            <el-option label="管理员" value="admin" />
            <el-option label="编辑人员" value="editor" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="addSubmitting" @click="submitAdd">确定</el-button>
      </template>
    </el-dialog>

    <!-- 编辑角色 -->
    <el-dialog
      v-model="editDialogVisible"
      title="编辑角色"
      width="380px"
      :close-on-click-modal="false"
    >
      <el-form ref="editFormRef" :model="editForm" :rules="editRules" label-width="100px">
        <el-form-item label="用户名">
          <el-input v-model="editForm.username" disabled />
        </el-form-item>
        <el-form-item label="显示名（认领标签）">
          <el-input v-model="editForm.display_name" placeholder="中文姓名，认领时显示；留空则用用户名" clearable />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-select v-model="editForm.role" placeholder="选择角色" style="width: 100%">
            <el-option label="管理员" value="admin" />
            <el-option label="编辑人员" value="editor" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="editSubmitting" @click="submitEdit">保存</el-button>
      </template>
    </el-dialog>

    <!-- 重置密码 -->
    <el-dialog
      v-model="resetPwdDialogVisible"
      title="重置密码"
      width="380px"
      :close-on-click-modal="false"
      @closed="resetPwdForm.new_password = ''"
    >
      <p style="margin-bottom: 12px;">为用户 <strong>{{ resetPwdTarget?.username }}</strong> 设置新密码：</p>
      <el-form ref="resetPwdFormRef" :model="resetPwdForm" :rules="resetPwdRules" label-width="80px">
        <el-form-item label="新密码" prop="new_password">
          <el-input v-model="resetPwdForm.new_password" type="password" show-password placeholder="至少6位" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="resetPwdDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="resetPwdSubmitting" @click="submitResetPwd">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { getUsers, createUser, updateUser, deleteUser, resetUserPassword } from '../api/user'
import { getUserInfo } from '../utils/auth'

const loading = ref(false)
const users = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)

const currentUserId = computed(() => {
  const u = getUserInfo()
  return u?.id ?? null
})

function formatDate(val) {
  if (!val) return '-'
  const d = new Date(val)
  return d.toLocaleString('zh-CN')
}

const loadUsers = async () => {
  loading.value = true
  try {
    const res = await getUsers({ page: currentPage.value, size: pageSize.value })
    users.value = res.items
    total.value = res.total
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '加载用户列表失败')
  } finally {
    loading.value = false
  }
}

onMounted(loadUsers)

// 新增
const addDialogVisible = ref(false)
const addSubmitting = ref(false)
const addFormRef = ref(null)
const addForm = ref({ username: '', password: '', role: 'editor' })
const addRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少6位', trigger: 'blur' }
  ],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }]
}

function openAddDialog() {
  addForm.value = { username: '', password: '', role: 'editor' }
  addDialogVisible.value = true
}

function resetAddForm() {
  addForm.value = { username: '', password: '', role: 'editor' }
}

const submitAdd = async () => {
  if (!addFormRef.value) return
  await addFormRef.value.validate(async (valid) => {
    if (!valid) return
    addSubmitting.value = true
    try {
      await createUser(addForm.value)
      ElMessage.success('用户已创建')
      addDialogVisible.value = false
      loadUsers()
    } catch (e) {
      ElMessage.error(e.response?.data?.detail || '创建失败')
    } finally {
      addSubmitting.value = false
    }
  })
}

// 编辑
const editDialogVisible = ref(false)
const editSubmitting = ref(false)
const editFormRef = ref(null)
const editForm = ref({ id: null, username: '', display_name: '', role: 'editor' })
const editRules = {
  role: [{ required: true, message: '请选择角色', trigger: 'change' }]
}

function openEditDialog(row) {
  editForm.value = {
    id: row.id,
    username: row.username,
    display_name: row.display_name || '',
    role: row.role
  }
  editDialogVisible.value = true
}

const submitEdit = async () => {
  if (!editFormRef.value) return
  await editFormRef.value.validate(async (valid) => {
    if (!valid) return
    editSubmitting.value = true
    try {
      await updateUser(editForm.value.id, {
        role: editForm.value.role,
        display_name: editForm.value.display_name || null
      })
      ElMessage.success('已保存')
      editDialogVisible.value = false
      loadUsers()
    } catch (e) {
      ElMessage.error(e.response?.data?.detail || '保存失败')
    } finally {
      editSubmitting.value = false
    }
  })
}

// 重置密码
const resetPwdDialogVisible = ref(false)
const resetPwdSubmitting = ref(false)
const resetPwdTarget = ref(null)
const resetPwdFormRef = ref(null)
const resetPwdForm = ref({ new_password: '' })
const resetPwdRules = {
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码至少6位', trigger: 'blur' }
  ]
}

function openResetPwdDialog(row) {
  resetPwdTarget.value = row
  resetPwdForm.value = { new_password: '' }
  resetPwdDialogVisible.value = true
}

const submitResetPwd = async () => {
  if (!resetPwdFormRef.value || !resetPwdTarget.value) return
  await resetPwdFormRef.value.validate(async (valid) => {
    if (!valid) return
    resetPwdSubmitting.value = true
    try {
      await resetUserPassword(resetPwdTarget.value.id, { new_password: resetPwdForm.value.new_password })
      ElMessage.success('密码已重置')
      resetPwdDialogVisible.value = false
    } catch (e) {
      ElMessage.error(e.response?.data?.detail || '重置失败')
    } finally {
      resetPwdSubmitting.value = false
    }
  })
}

// 删除
const handleDelete = async (row) => {
  if (row.id === currentUserId.value) {
    ElMessage.warning('不能删除当前登录用户')
    return
  }
  try {
    await ElMessageBox.confirm(
      `确定要删除用户「${row.username}」吗？删除后该用户将无法登录。`,
      '确认删除',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
    )
    await deleteUser(row.id)
    ElMessage.success('已删除')
    loadUsers()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(e.response?.data?.detail || '删除失败')
    }
  }
}
</script>

<style scoped>
.users-view {
  padding: 20px;
}

.header-card {
  margin-bottom: 20px;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-content h2 {
  margin: 0;
  font-size: 18px;
}

.table-card {
  min-height: 400px;
}

.pagination-container {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
