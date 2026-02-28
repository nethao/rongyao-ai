-- 投稿认领：编辑人员认领后打上标签
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS claimed_by_user_id INTEGER REFERENCES users(id);

-- 用户显示名（中文姓名）：认领标签优先用此，无则用 username
ALTER TABLE users ADD COLUMN IF NOT EXISTS display_name VARCHAR(50);

CREATE INDEX IF NOT EXISTS idx_submissions_claimed_by ON submissions(claimed_by_user_id);
