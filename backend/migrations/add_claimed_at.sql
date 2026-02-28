-- 认领时间：记录稿件被认领的时刻
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS claimed_at TIMESTAMPTZ;
