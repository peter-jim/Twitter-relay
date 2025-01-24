-- 创建 interactions 表
CREATE TABLE x_interactions
(
    interaction_id      VARCHAR(80) PRIMARY KEY,
    media_account       VARCHAR(80)  NOT NULL,
    user_id             VARCHAR(80)  NOT NULL,
    username            VARCHAR(100) NOT NULL,
    avatar_url          VARCHAR(255),
    interaction_type    VARCHAR(255)  NOT NULL,
    interaction_content TEXT,
    interaction_time    TIMESTAMP    NOT NULL,
    post_id             VARCHAR(80)  NOT NULL,
    post_time           TIMESTAMP    NOT NULL,
    INDEX               idx_media_account (media_account), -- 为 media_account 添加索引
    INDEX               idx_user_id (user_id)              -- 为 user_id 添加索引
);