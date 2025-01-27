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
    api_name,
    is_active,
    is_admin,
    created_at,
    expires_at
) VALUES (
    'admin_5ff1c7a75e9f4e1d8f3c3c3c3c3c3c3c',  -- A fixed admin API key for testing
    'admin',
    TRUE,
    TRUE,
    CURRENT_TIMESTAMP,
    NULL  -- Never expires
);

-- Insert the test normal API key
INSERT INTO api_keys (
    api_key,
    api_name,
    is_active,
    is_admin,
    created_at,
    expires_at
) VALUES (
    'normal_5ff1c7a75e9f4e1d8f3c3c3c3c3c3c3c',  -- A fixed normal API key for testing
    'normal',
    TRUE,
    FALSE,
    CURRENT_TIMESTAMP,
    NULL  -- Never expires
);