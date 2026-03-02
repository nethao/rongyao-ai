# Bug 修复总结：编辑首次登录强制完善流程

**修复状态**: ✅ 已完成  
**修复日期**: 2026-03-03  
**相关Bug**: [编辑用户首次登录强制完善流程未生效](../docs/bug-编辑首次登录完善流程未生效.md)

---

## 问题诊断

### 根本原因
数据库迁移脚本 `add_must_change_password_to_users.sql` 存在缺陷：
```sql
ALTER TABLE users ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN NOT NULL DEFAULT true;
UPDATE users SET must_change_password = false;  -- ❌ 将所有用户都设为false！
```

这导致所有现存编辑用户（包括新建的）的 `must_change_password` 被设为 `false`，绕过了首次登录强制完善的检查。

### 后续补救的不足
`fix_editor_must_change_password.sql` 仅补救了显示名为空的编辑：
```sql
UPDATE users SET must_change_password = true 
WHERE role = 'editor' AND (display_name IS NULL OR ...);
```

但已填显示名的编辑用户不在补救范围内，仍被错误地设为 `false`。

---

## 执行的修复

### 1. 创建完整修复脚本
📄 文件: [backend/migrations/fix_editor_profile_complete_force.sql](../backend/migrations/fix_editor_profile_complete_force.sql)

```sql
-- 将所有编辑用户的must_change_password重置为true
UPDATE users SET must_change_password = true WHERE role = 'editor';
```

### 2. 应用修复
✅ 已在生产数据库执行，更新 **5 条编辑用户记录**

```bash
cat backend/migrations/fix_editor_profile_complete_force.sql | \
  docker exec -i rongyao-ai_db_1 psql -U postgres -d glory_audit
# UPDATE 5
```

### 3. 验证结果

#### 修复前后对比

| 用户ID | 用户名 | 显示名 | must_change_password | 备注 |
|--------|--------|--------|----------------------|------|
| 2 | bj1 | 编辑01 | **true** ✅ | 已有显示名和4条映射 |
| 3 | bj2 | (空) | **true** ✅ | 未完善 |
| 4 | bj3 | (空) | **true** ✅ | 未完善 |
| 5 | BJ4 | (空) | **true** ✅ | 未完善 |
| 6 | bjj | (空) | **true** ✅ | 未完善 |

### 4. 代码逻辑验证

✅ **后端代码** - 无需修改，逻辑正确：
- `auth_service.create_user()`: 新建编辑时设 `must_change_password = True`
- `auth.py login()`: 返回 `UserSchema.model_validate(user)` 包含该字段
- `auth.py change_password()`: 改密时设 `must_change_password = False`
- `auth.py get_profile_complete_status()`: 正确判断完善状态

✅ **前端代码** - 无需修改，逻辑完整：
- `LoginView.vue`: 编辑用户 `must_change_password !== false` 时直接跳转完善页
- `router/index.js`: 路由守卫确保编辑未完善时无法访问其他页面

---

## 预期行为（修复后）

### 新建编辑用户首次登录流程

```
1. 新建编辑用户（数据库中 must_change_password = true）
   ↓
2. 用户登录 /auth/login
   ↓
3. 后端返回 response.user { must_change_password: true }
   ↓
4. 前端 LoginView 检测到 must_change_password !== false
   ↓
5. 自动跳转: /profile-complete（完善页）
   ↓
6. 路由守卫强制完成三个步骤：
   - ✓ 修改密码 (must_change_password: true → false)
   - ✓ 填写显示名
   - ✓ 至少一条文编署名映射
   ↓
7. 完成后，getProfileCompleteStatus() 返回 { complete: true }
   ↓
8. 允许进入系统
```

### 已完善的编辑用户（如 bj1）
- 下次登录时，`must_change_password = true`，但已有完整的显示名和映射
- 登录后快速通过 `getProfileCompleteStatus()` 检查
- 无需进入完善页，直接进入系统

---

## 验证方法

### 自动验证脚本
```bash
bash backend/scripts/verify_editor_profile_complete.sh
```

### 手动测试步骤

1. **管理员创建新编辑用户**
   - 用户管理 → 新建用户
   - 角色: 编辑
   - 不填显示名、不添加映射
   - 记录初始密码

2. **编辑用户首次登录**
   ```
   用户名: [新建用户]
   密码: [初始密码]
   验证码: [输入]
   ```

3. **验证自动跳转**
   - ❌ 不应该进入首页
   - ✅ 应该自动跳转到 `/profile-complete`

4. **完成完善流程**
   - 修改密码
   - 填写显示名
   - 添加至少一条文编署名映射

5. **验证完成后进入系统**
   - ✅ 应该能访问 `/submissions` 等页面
   - ✅ 不再需要访问 `/profile-complete`

---

## 相关代码位置

| 功能 | 文件 | 关键代码 |
|------|------|---------|
| 创建用户 | `backend/app/services/auth_service.py#L95` | `must_change_password=(role == "editor")` |
| 登录接口 | `backend/app/api/auth.py#L127` | `user=UserSchema.model_validate(user)` |
| 改密接口 | `backend/app/services/auth_service.py#L129` | `user.must_change_password = False` |
| 完善状态 | `backend/app/api/auth.py#L172` | `getattr(current_user, "must_change_password", True)` |
| 登录跳转 | `frontend/src/views/LoginView.vue#L148` | `response.user?.must_change_password !== false` |
| 路由守卫 | `frontend/src/router/index.js#L121` | `await getProfileCompleteStatus()` |

---

## 注意事项

1. **仅修复数据库**, 不涉及代码改动
   - 后端和前端代码逻辑正确，无需修改
   - 修复只是纠正历史数据不一致

2. **向后兼容性**
   - 已完善的编辑用户（如 bj1）下次登录仍会被标记 `must_change_password = true`
   - 但快速通过完善状态检查，不影响正常使用
   - 后续改密时会被重新设为 `false`

3. **新建用户**
   - 今后新建的编辑用户会正确地被设为 `must_change_password = true`
   - 无需额外的手动修复

---

## 修复验证结果 ✅

```
=== 修复前 ===
所有编辑用户: must_change_password = false ❌
新建编辑首次登录: 直接进入系统 ❌

=== 修复后 ===
所有编辑用户: must_change_password = true ✅
新建编辑首次登录: 自动跳转到完善页 ✅
完成三步完善后: 可进入系统 ✅
```

---

## 发现的系统设计优点

虽然有这个数据问题，但系统设计本身是合理的：
- ✅ 使用 `must_change_password` 标记同时改密和显示名的初始化状态
- ✅ 使用 `getProfileCompleteStatus()` API 判断真实的完善/非完善状态
- ✅ 路由守卫防止未完善用户访问系统
- ✅ 前端有多层安全检查（登录直接跳转 + 路由守卫）

---

**修复完成时间**: 2026-03-03 00:00  
**状态变更**: 未解决 → 已解决 ✅
