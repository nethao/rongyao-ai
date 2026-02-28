-- 重复稿件记录表（C 方案：不改动 submissions 表）
-- 用于记录被跳过的重复邮件 或 被新稿替换的旧投稿
CREATE TABLE IF NOT EXISTS duplicate_logs (
    id SERIAL PRIMARY KEY,
    -- 邮件元数据（不抓取内容，仅记录）
    email_subject VARCHAR(255) NOT NULL,
    email_from VARCHAR(255),
    email_date TIMESTAMPTZ,
    cooperation_type VARCHAR(20),
    media_type VARCHAR(20),
    source_unit VARCHAR(255),
    title VARCHAR(500),
    -- 去重类型：skipped=跳过未处理, superseded=被新稿替换
    duplicate_type VARCHAR(20) NOT NULL,
    -- 有效稿 ID（skipped 时指已存在的稿；superseded 时指新创建的稿）
    effective_submission_id INTEGER,
    -- 被替换的投稿 ID（仅 superseded 时有值）
    superseded_submission_id INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_duplicate_logs_effective ON duplicate_logs(effective_submission_id);
CREATE INDEX IF NOT EXISTS idx_duplicate_logs_superseded ON duplicate_logs(superseded_submission_id);
CREATE INDEX IF NOT EXISTS idx_duplicate_logs_created ON duplicate_logs(created_at);
