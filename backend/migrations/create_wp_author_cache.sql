-- 创建WordPress作者缓存表
CREATE TABLE IF NOT EXISTS wp_author_cache (
    id SERIAL PRIMARY KEY,
    system_username VARCHAR(50) NOT NULL,
    site_id INTEGER NOT NULL REFERENCES wordpress_sites(id) ON DELETE CASCADE,
    wp_user_id INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(system_username, site_id)
);

CREATE INDEX IF NOT EXISTS idx_wp_author_cache_lookup ON wp_author_cache(system_username, site_id);

COMMENT ON TABLE wp_author_cache IS 'WordPress作者ID缓存，避免重复API查询';
COMMENT ON COLUMN wp_author_cache.system_username IS '系统用户名';
COMMENT ON COLUMN wp_author_cache.site_id IS 'WordPress站点ID';
COMMENT ON COLUMN wp_author_cache.wp_user_id IS 'WordPress站点的用户ID';
