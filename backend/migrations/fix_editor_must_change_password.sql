-- 补救：若在 add_must_change_password 迁移之后创建了编辑用户，
-- 迁移里的 UPDATE 会误把该用户设为 false。将「未完善资料的编辑」重新设为须改密。
-- 执行: psql -U <user> -d <db> -f backend/migrations/fix_editor_must_change_password.sql
UPDATE users
SET must_change_password = true
WHERE role = 'editor'
  AND (display_name IS NULL OR trim(COALESCE(display_name, '')) = '');
