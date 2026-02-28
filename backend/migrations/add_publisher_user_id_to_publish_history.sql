-- 文编工作量统计：记录每条发布记录的操作人
ALTER TABLE publish_history
ADD COLUMN IF NOT EXISTS publisher_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_publish_history_publisher_user_id ON publish_history(publisher_user_id);
