# Bug：编辑用户首次登录强制完善流程未生效

**状态**：未解决  
**创建**：2026-03  
**相关需求**：角色为「编辑人员」的用户首次登录时，强制完成：1）修改密码；2）填写显示名；3）至少一条文编署名映射；完成前只能访问完善页。

---

## 1. 预期行为

- 新建的**编辑用户**首次登录成功后：
  - 应被重定向到 `/profile-complete` 完善页；
  - 完成改密、显示名、文编署名映射前，不能进入系统其他页面（路由守卫拦截）。
- 管理员不受影响；已有编辑（已完善过）正常进入系统。

---

## 2. 实际行为

- 新建编辑用户首次登录后**未**跳转到完善页，直接进入首页/目标页，强制完善流程未生效。

---

## 3. 复现步骤

1. 管理员在「用户管理」中新建一名**编辑**用户（用户名、初始密码、角色=编辑）。
2. 退出管理员账号，使用该编辑账号首次登录。
3. **预期**：登录成功后自动跳转到「完善资料」页（改密、显示名、文编署名映射）。  
   **实际**：未跳转，直接进入系统。

---

## 4. 相关代码位置

| 环节 | 文件 | 说明 |
|------|------|------|
| 登录后是否跳转 | `frontend/src/views/LoginView.vue` | 登录成功后若 `response.user?.role === 'editor'` 且 `response.user?.must_change_password === true` 则 `router.replace('/profile-complete')`；否则再请求 `getProfileCompleteStatus()` 按结果跳转。 |
| 路由守卫 | `frontend/src/router/index.js` | `beforeEach` 中已登录且非完善页时请求 `getProfileCompleteStatus()`，若 `complete === false` 则重定向到 `/profile-complete`。 |
| 完善页 | `frontend/src/views/ProfileCompleteView.vue` | 三步：改密、显示名、文编署名映射。 |
| 后端完善状态 | `backend/app/api/auth.py` | `GET /auth/profile-complete-status`，根据 `current_user.must_change_password`、`display_name`、文编映射条数返回 `complete`、`missing_steps`。 |
| 登录返回用户信息 | `backend/app/api/auth.py` | 登录接口返回 `TokenResponse`，其中 `user=UserSchema.model_validate(user)`，需包含 `must_change_password`。 |
| 用户模型 | `backend/app/models/user.py` | `User` 表含 `must_change_password` 列（Boolean，默认 true）。 |
| 创建用户 | `backend/app/services/auth_service.py` | `create_user` 中编辑角色设置 `must_change_password=(role == "editor")`。 |
| 用户 schema | `backend/app/schemas/auth.py` | `User` 响应含 `must_change_password: bool = True`。 |

---

## 5. 已做过的修复尝试（均未解决问题）

- **数据库**：执行 `add_must_change_password_to_users.sql` 增加 `must_change_password` 列；执行 `fix_editor_must_change_password.sql` 将「未填显示名的编辑」的 `must_change_password` 设回 `true`（已更新 3 条）。
- **前端**：在 `LoginView.vue` 中优先根据登录返回的 `response.user?.must_change_password === true` 直接跳转完善页，减少对二次接口的依赖。
- **前端构建**：无缓存重建 frontend 镜像并重新创建 frontend 容器，确保线上为最新前端逻辑。
- **结果**：用户反馈「一顿操作，我要的功能还是没有实现」。

---

## 6. 可能原因与待排查项

1. **登录接口返回的 `user` 是否包含 `must_change_password`**  
   - 浏览器开发者工具 → Network → 登录请求的响应 JSON 中 `user` 是否有 `must_change_password` 且为 `true`。  
   - 若缺失或为 `false`，需查：后端 `UserSchema.model_validate(user)` 是否从 ORM 正确带出该字段；该编辑用户在 DB 中 `must_change_password` 是否为 `true`。

2. **前端是否真的跑的是新构建**  
   - 确认访问的前端地址对应的容器/镜像是否为本次无缓存构建的版本（例如看 `LoginView` 里是否有「编辑人员首次登录未完善则强制进入完善页」及对 `must_change_password` 的判断）。  
   - 是否存在 CDN/浏览器强缓存导致仍加载旧 JS。

3. **路由守卫与登录时序**  
   - 登录成功后先 `setToken`、`setUserInfo`，再根据 `response.user` 或 `getProfileCompleteStatus()` 决定是否跳转。若 `getProfileCompleteStatus()` 被调用但失败（网络/401/超时），当前实现里 catch 后不跳转，可能放行到首页。  
   - 若登录响应里 `must_change_password` 未正确为 `true`，则不会在 LoginView 里直接跳转，只依赖守卫；若守卫请求失败也会放行。

4. **后端当前用户与 DB 一致性**  
   - `get_profile_complete_status` 依赖 `get_current_user` 从 DB 重新查出的用户。确认该用户记录在 DB 中 `must_change_password`、`display_name` 以及文编映射条数是否符合「未完善」的预期。

5. **新建编辑的创建时机与迁移顺序**  
   - 若先执行了 `UPDATE users SET must_change_password = false` 的迁移，再创建该编辑，则新用户应为 `true`（INSERT 默认或显式设置）。  
   - 若该编辑是在迁移前创建，迁移会把其置为 `false`；已通过 `fix_editor_must_change_password.sql` 按「未填显示名」补救，若编辑已有显示名则不会被该脚本更新，需单独检查或扩展补救条件。

---

## 7. 建议的验证与修复方向

1. **立刻可做的验证**  
   - 登录接口响应：抓包或 Network 看登录返回的 `user.must_change_password`、`user.role`。  
   - 直接请求：登录后在控制台请求 `GET /api/auth/profile-complete-status`（带 Authorization），看返回的 `complete`、`missing_steps`。  
   - 数据库：对该编辑用户执行 `SELECT id, username, role, display_name, must_change_password FROM users WHERE role = 'editor';` 核对 `must_change_password` 与显示名。

2. **若登录响应缺少或错误 `must_change_password`**  
   - 检查 `backend` 是否已加载最新代码（含 `User` 模型与 `UserSchema` 的 `must_change_password`）；  
   - 确认登录接口返回的 `user` 来自 DB 查出的完整 `User` 对象（含该列），且 Pydantic 未过滤掉该字段。

3. **若前端未拿到或未使用最新逻辑**  
   - 确认部署的 frontend 镜像/构建产物包含上述 LoginView 与 router 逻辑；  
   - 必要时清理浏览器缓存或使用无痕窗口、不同 BASE_URL 验证。

4. **增强健壮性**  
   - 在 LoginView 中：编辑角色下若 `getProfileCompleteStatus()` 失败，可考虑仍按「未完善」处理并跳转完善页（或至少打日志/上报），避免静默放行。  
   - 在路由守卫中：对编辑角色且接口失败时的策略可再议（例如失败时重定向到完善页或提示重新登录）。

---

## 8. 环境与版本（供排查参考）

- 前端：Vue + Vite，部署为 Docker 镜像（nginx  serving 静态资源）。
- 后端：FastAPI，Docker 挂载 `./backend`。
- 数据库：PostgreSQL，`users` 表含 `must_change_password`，已执行相关迁移与补救 SQL。

若后续定位到根因或完成修复，建议在本文档补充「原因说明」与「修复方案」并更新状态为已解决。
