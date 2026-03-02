#!/bin/bash

# 验证编辑用户首次登录强制完善流程修复
# 使用方法: bash backend/scripts/verify_editor_profile_complete.sh

echo "=== 验证编辑用户首次登录强制完善流程修复 ==="
echo ""

# 1. 检查数据库中编辑用户的状态
echo "1. 数据库中编辑用户的must_change_password状态："
docker exec rongyao-ai_db_1 psql -U postgres -d glory_audit -c "
SELECT id, username, role, display_name, must_change_password FROM users WHERE role = 'editor' ORDER BY created_at DESC;
"
echo ""

# 2. 检查是否有已完善的编辑用户
echo "2. 已完善的编辑用户（有display_name且至少一条文编映射）："
docker exec rongyao-ai_db_1 psql -U postgres -d glory_audit -c "
SELECT u.id, u.username, u.display_name,
  (SELECT COUNT(*) FROM copy_editor_site_mappings WHERE user_id = u.id) as mapping_count
FROM users u
WHERE u.role = 'editor'
  AND u.display_name IS NOT NULL
  AND TRIM(u.display_name) != ''
  AND EXISTS (SELECT 1 FROM copy_editor_site_mappings WHERE user_id = u.id)
ORDER BY u.id DESC;
"
echo ""

# 3. 检查未完善的编辑用户
echo "3. 未完善的编辑用户（缺少display_name或文编映射）："
docker exec rongyao-ai_db_1 psql -U postgres -d glory_audit -c "
SELECT u.id, u.username, u.display_name, 
  (SELECT COUNT(*) FROM copy_editor_site_mappings WHERE user_id = u.id) as mapping_count
FROM users u
WHERE u.role = 'editor'
  AND (u.display_name IS NULL OR TRIM(u.display_name) = '' 
       OR NOT EXISTS (SELECT 1 FROM copy_editor_site_mappings WHERE user_id = u.id))
ORDER BY u.created_at DESC;
"
echo ""

echo "=== 验证完成 ==="
echo ""
echo "修复验证说明："
echo "- 新建的编辑用户should have must_change_password = true (t)"
echo "- 首次登录时会 check response.user.must_change_password 直接跳转到完善页"
echo "- 如果用户已改密、填显示名、有文编映射，则complete=true，不需强制完善"
echo ""
echo "测试步骤："
echo "1. 管理员创建一个新编辑用户（不填display_name和文编映射）"
echo "2. 使用该用户首次登录"
echo "3. 应该自动跳转到 /profile-complete 完善页"
echo "4. 完成三个步骤后，应该能成功进入系统"
