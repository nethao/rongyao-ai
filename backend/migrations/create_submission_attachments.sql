-- 提交附件表：用于记录Word/视频/压缩包等OSS文件
CREATE TABLE IF NOT EXISTS submission_attachments (
    id SERIAL PRIMARY KEY,
    submission_id INTEGER NOT NULL REFERENCES submissions(id) ON DELETE CASCADE,
    attachment_type VARCHAR(20) NOT NULL,
    oss_url VARCHAR(500) NOT NULL,
    oss_key VARCHAR(500) NOT NULL,
    original_filename VARCHAR(255),
    file_size INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_submission_attachments_submission_id
ON submission_attachments(submission_id);

CREATE INDEX IF NOT EXISTS idx_submission_attachments_created_at
ON submission_attachments(created_at);
