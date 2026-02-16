# 数据分析功能开发问题记录

## 问题1：Token认证失败 (401 Unauthorized)

**时间**：2026-02-17 04:22

**现象**：
```
GET /api/analytics/overview 401 Unauthorized
```

**原因**：
前端使用错误的localStorage key获取token
```javascript
// 错误
const getToken = () => localStorage.getItem('token')

// 正确
const getToken = () => localStorage.getItem('access_token')
```

**解决方案**：
修改前端代码使用正确的token key `access_token`

**文件**：`frontend/src/views/AnalyticsView.vue`

---

## 问题2：SQL日期参数类型错误 (500 Internal Server Error)

**时间**：2026-02-17 04:38 - 04:43

**现象**：
```
sqlalchemy.exc.DBAPIError: invalid input for query argument $1: '2026-02-17' 
('str' object has no attribute 'toordinal')
```

**原因**：
PostgreSQL的asyncpg驱动要求日期参数必须是Python的`date`对象，不能是字符串。

**尝试的方案**：
1. ❌ 使用`DATE(created_at)`函数 - 参数仍是字符串
2. ❌ 使用`created_at::date`语法 - SQL参数绑定中`::`被误解析
3. ❌ 使用`CAST(created_at AS DATE)`但参数仍是字符串 - 类型不匹配

**最终解决方案**：
在Python后端将字符串转换为date对象
```python
from datetime import datetime, date

# 转换字符串为date对象
if start_date:
    params["start_date"] = datetime.strptime(start_date, "%Y-%m-%d").date()
if end_date:
    params["end_date"] = datetime.strptime(end_date, "%Y-%m-%d").date()
```

**SQL查询**：
```sql
WHERE CAST(created_at AS DATE) >= :start_date
```

**文件**：`backend/app/api/analytics.py`

**关键点**：
- asyncpg驱动对类型要求严格
- 字符串参数无法自动转换为date类型
- 必须在Python层面转换类型

---

## 经验总结

### 1. PostgreSQL asyncpg驱动类型要求
- 日期参数必须是`datetime.date`对象
- 时间参数必须是`datetime.datetime`对象
- 不能依赖数据库自动类型转换

### 2. SQL参数绑定注意事项
- 避免在SQL中使用`::`类型转换语法（与参数绑定冲突）
- 使用`CAST(column AS TYPE)`函数
- 类型转换在Python层面完成

### 3. 前端token管理
- 统一使用`access_token`作为localStorage key
- 检查其他页面的实现方式保持一致

### 4. 调试技巧
- 查看后端日志：`docker-compose logs --tail=100 backend`
- 直接测试SQL：`docker-compose exec db psql -U postgres -d glory_audit`
- 检查参数类型：查看SQLAlchemy错误信息中的`[parameters]`部分

---

## 相关提交

- `5a4fcda` - fix: 修复数据分析页面token传递问题
- `cfbab3b` - fix: 修复数据分析日期参数类型错误，使用DATE()函数比较
- `3d1edae` - fix: 使用PostgreSQL类型转换::date修复日期参数问题
- `674462b` - fix: 使用CAST函数替代::语法避免SQL参数冲突
- `b069658` - fix: 将日期字符串转换为date对象传递给SQL ✅ 最终方案

---

## 预防措施

1. **类型检查**：在API层面添加参数类型验证
2. **单元测试**：为日期查询添加测试用例
3. **文档说明**：在代码注释中说明asyncpg的类型要求
4. **统一规范**：制定前端token管理规范
