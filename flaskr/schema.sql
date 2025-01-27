-- 创建 interactions 表
CREATE TABLE x_interactions
(
    interaction_id      VARCHAR(64) PRIMARY KEY,
    media_account      VARCHAR(255) NOT NULL,
    user_id            VARCHAR(64) NOT NULL,
    username           VARCHAR(255) NOT NULL,
    avatar_url         VARCHAR(255),
    interaction_type   VARCHAR(20) NOT NULL,
    interaction_content TEXT,
    interaction_time   TIMESTAMP NOT NULL,
    post_id            VARCHAR(64) NOT NULL,
    post_time          TIMESTAMP NOT NULL,
    nostr_published    BOOLEAN NOT NULL DEFAULT FALSE,
    nostr_event_id     VARCHAR(64),
    INDEX idx_media_account (media_account),
    INDEX idx_user_id (user_id)
);

-- Create api_keys table
CREATE TABLE api_keys (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    api_key         VARCHAR(64) UNIQUE NOT NULL,
    api_secret      VARCHAR(64) NOT NULL,
    api_name        VARCHAR(128) NOT NULL,
    is_admin        BOOLEAN NOT NULL DEFAULT FALSE,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at      TIMESTAMP NULL,
    last_used_at    TIMESTAMP NULL,
    INDEX idx_api_key (api_key)
);

-- Insert the test admin API key
INSERT INTO api_keys (
    api_key,
    api_secret,
    api_name,
    is_admin,
    is_active,
    created_at,
    expires_at
) VALUES (
    'admin_5ff1c7a75e9f4e1d8f3c3c3c3c3c3c3c',  -- 测试用的固定admin API key
    'admin_secret_8a4c7b3e2f1d9g6h5j8k7l4m1n3p2q9r',  -- 测试用的固定admin API secret
    'admin',
    TRUE,
    TRUE,
    CURRENT_TIMESTAMP,
    NULL  -- 永不过期
);

-- Insert the test normal API key
INSERT INTO api_keys (
    api_key,
    api_secret,
    api_name,
    is_admin,
    is_active,
    created_at,
    expires_at
) VALUES (
    'normal_5ff1c7a75e9f4e1d8f3c3c3c3c3c3c3c',  -- 测试用的固定normal API key
    'normal_secret_9b5d8c4a3e2f1g7h6j9k8l5m2n4p3q0r',  -- 测试用的固定normal API secret
    'normal',
    FALSE,
    TRUE,
    CURRENT_TIMESTAMP,
    NULL  -- 永不过期
);