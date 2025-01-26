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