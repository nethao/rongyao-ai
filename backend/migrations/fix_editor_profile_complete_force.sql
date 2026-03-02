-- 修复编辑用户首次登录强制完善问题
-- 问题：现有的编辑用户的must_change_password被错误地设为false
-- 修复：将所有编辑用户（无论是否填了display_name）的must_change_password重置为true
--       每个编辑用户首次登录时必须完成：1) 改密 2) 显示名 3) 文编署名映射

UPDATE users
SET must_change_password = true
WHERE role = 'editor';

-- 验证修复结果
-- SELECT id, username, role, display_name, must_change_password 
-- FROM users 
-- WHERE role = 'editor'
-- ORDER BY created_at DESC;
