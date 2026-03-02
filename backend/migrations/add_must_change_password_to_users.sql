-- 编辑人员首次登录强制改密、填写显示名、文编署名映射
ALTER TABLE users ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN NOT NULL DEFAULT true;
-- 已有用户不强制（仅新创建的编辑需完善）
UPDATE users SET must_change_password = false;
