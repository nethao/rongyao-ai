# 阶段5：审核分发后台 - 实现说明

## 已完成功能

### 5.1 投稿列表界面 ✅
- **SubmissionsView.vue**: 投稿列表页面
  - 分页显示所有投稿
  - 状态筛选（待处理、处理中、已完成、失败）
  - 关键词搜索
  - 状态标签显示
  - 查看详情对话框
  - 触发AI转换功能
  - 跳转到草稿审核页面

### 5.2 双栏对比界面 ✅
- **AuditView.vue**: 审核页面
  - 左右双栏布局
  - 左栏：原始内容（只读）
  - 右栏：AI转换内容（可编辑）
  - 文本差异高亮显示
  - 实时编辑功能

### 5.3 内容编辑功能 ✅
- 富文本编辑器集成（使用Element Plus的textarea）
- 自动保存功能（3秒延迟）
- 保存状态提示（已保存/未保存）
- 页面离开前提示（防止丢失未保存的修改）

### 5.4 版本管理功能 ✅
- 版本历史查询
- 版本列表显示
- 版本详情查看
- 版本恢复功能
- 版本号自动递增

### 5.5 恢复原文功能 ✅
- 恢复到AI原始版本（版本1）
- 恢复确认对话框
- 恢复后界面自动刷新
- 操作日志记录（通过版本系统）

## 后端API实现

### 新增API端点

#### 投稿管理 (`/submissions`)
- `GET /submissions/` - 获取投稿列表（支持分页、筛选、搜索）
- `GET /submissions/{id}` - 获取投稿详情
- `POST /submissions/{id}/transform` - 触发AI转换任务

#### 草稿管理 (`/drafts`)
- `GET /drafts/{id}` - 获取草稿详情（包含原文）
- `PUT /drafts/{id}` - 更新草稿内容（创建新版本）
- `GET /drafts/{id}/versions` - 获取版本历史
- `POST /drafts/{id}/restore` - 恢复到指定版本
- `POST /drafts/{id}/restore-ai` - 恢复到AI原始版本

### 数据模型

#### Pydantic Schemas
- `SubmissionSchema` - 投稿响应模型
- `DraftSchema` - 草稿响应模型
- `DraftDetailSchema` - 草稿详情模型（包含原文）
- `DraftVersionSchema` - 版本模型

## 前端组件结构

```
frontend/src/
├── api/
│   ├── submission.js      # 投稿API客户端
│   └── draft.js           # 草稿API客户端
├── components/
│   └── Layout.vue         # 布局组件（导航栏）
├── utils/
│   └── diff.js            # 文本差异计算工具
├── views/
│   ├── SubmissionsView.vue  # 投稿列表页面
│   └── AuditView.vue        # 审核页面
└── router/
    └── index.js           # 路由配置
```

## 技术特点

### 1. 响应式设计
- 使用Vue 3 Composition API
- 响应式数据绑定
- 自动UI更新

### 2. 用户体验优化
- 自动保存（防止数据丢失）
- 加载状态提示
- 操作确认对话框
- 友好的错误提示

### 3. 性能优化
- 分页加载（避免一次加载大量数据）
- 懒加载路由组件
- 防抖处理（自动保存）

### 4. 安全性
- JWT令牌认证
- 路由守卫（权限控制）
- 页面离开前确认

## 使用说明

### 启动前端开发服务器
```bash
cd frontend
npm install
npm run dev
```

### 访问页面
- 登录页面: http://localhost:5173/login
- 投稿列表: http://localhost:5173/submissions
- 审核页面: http://localhost:5173/audit/{draftId}

### 工作流程
1. 登录系统
2. 在投稿列表查看所有投稿
3. 对于"待处理"的投稿，点击"开始转换"触发AI转换
4. 转换完成后，点击"查看草稿"进入审核页面
5. 在审核页面对比原文和AI转换内容
6. 编辑右栏内容（自动保存）
7. 查看版本历史，必要时恢复到历史版本
8. 点击"恢复AI版本"可以重置到AI转换的原始版本
9. 编辑完成后，点击"发布"（阶段6实现）

## 待实现功能（后续阶段）

- 阶段6：WordPress发布功能
- 阶段7：数据清理与维护
- 阶段8：系统监控与日志
- 阶段9：测试
- 阶段10：部署与文档

## 注意事项

1. **草稿ID获取**: 前端通过投稿的`drafts`数组获取第一个草稿的ID
2. **版本管理**: 每次保存都会创建新版本，版本1是AI转换的原始版本
3. **自动保存**: 编辑内容后3秒自动保存，避免频繁请求
4. **并发编辑**: 当前实现使用页面离开提示，未来可以添加WebSocket实现实时锁定

## 技术栈

- **前端框架**: Vue 3 + Vite
- **UI组件库**: Element Plus
- **状态管理**: Pinia
- **路由**: Vue Router 4
- **HTTP客户端**: Axios
- **后端框架**: FastAPI
- **数据库**: PostgreSQL
- **ORM**: SQLAlchemy 2.0 (async)
