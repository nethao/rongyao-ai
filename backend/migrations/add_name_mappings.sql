-- 采编名称映射：邮箱 -> 采编姓名（责编署名）
CREATE TABLE IF NOT EXISTS editor_name_mappings (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    display_name VARCHAR(100) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_editor_name_mappings_email ON editor_name_mappings(email);

-- 文编站点映射：用户在不同站点下的署名
CREATE TABLE IF NOT EXISTS copy_editor_site_mappings (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    site_id INTEGER NOT NULL REFERENCES wordpress_sites(id) ON DELETE CASCADE,
    display_name VARCHAR(100) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, site_id)
);
CREATE INDEX IF NOT EXISTS idx_copy_editor_site_user ON copy_editor_site_mappings(user_id);
CREATE INDEX IF NOT EXISTS idx_copy_editor_site_site ON copy_editor_site_mappings(site_id);
