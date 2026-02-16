-- 回滚wp_author_id字段
ALTER TABLE users DROP COLUMN IF EXISTS wp_author_id;
