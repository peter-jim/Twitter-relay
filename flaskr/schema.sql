-- 创建 interactions 表
CREATE TABLE x_interactions (
    interaction_id VARCHAR(80) PRIMARY KEY,
    media_account VARCHAR(80) NOT NULL,
    user_id VARCHAR(80) NOT NULL,
    username VARCHAR(100) NOT NULL,
    avatar_url VARCHAR(255),
    interaction_type VARCHAR(20) NOT NULL,
    interaction_content TEXT,
    interaction_time TIMESTAMP NOT NULL,
    post_id VARCHAR(80) NOT NULL,
    post_time TIMESTAMP NOT NULL
);