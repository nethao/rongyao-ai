-- 添加用户的WordPress作者ID字段
ALTER TABLE users ADD COLUMN IF NOT EXISTS wp_author_id INTEGER;

COMMENT ON COLUMN users.wp_author_id IS 'WordPress站点的作者ID，用于发布文章时指定作者';
