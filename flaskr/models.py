from datetime import datetime

from sqlalchemy import Boolean, String, Text, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from flaskr import db


class Interaction(db.Model):
    __tablename__ = 'x_interactions'  # 定义表名

    interaction_id: Mapped[str] = mapped_column(String(64), primary_key=True)  # 主键
    media_account: Mapped[str] = mapped_column(String(255), nullable=False, index=True)  # 媒体账户
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # 用户ID
    username: Mapped[str] = mapped_column(String(255), nullable=False)  # 用户名
    avatar_url: Mapped[str] = mapped_column(String(255), nullable=True)  # 头像URL
    interaction_type: Mapped[str] = mapped_column(String(20), nullable=False)  # 互动类型
    interaction_content: Mapped[str] = mapped_column(Text, nullable=True)  # 互动内容（可选，对于评论）
    interaction_time: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False)  # 互动时间
    post_id: Mapped[str] = mapped_column(String(64), nullable=False)  # 帖子ID，用于关联
    post_time: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False)  # 帖子发布时间
    nostr_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)  # 是否已发布到nostr
    nostr_event_id: Mapped[str] = mapped_column(String(64), nullable=True)  # nostr事件ID
