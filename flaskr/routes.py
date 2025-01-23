from flask import request, Blueprint
from sqlalchemy import func

from .extensions import db
from sqlalchemy.sql.expression import select

from .models import Interaction

bp = Blueprint('api', __name__, url_prefix="/api")


@bp.route("/interaction/<media_account>", methods=['GET'])
def get_interactions(media_account: str):
    result = db.session.execute(
        select(Interaction).where(Interaction.media_account == media_account)
    )

    interactions = result.scalars().all()

    return {
        "media_account": media_account,
        "interactions": [
            {
                "interaction_id": interaction.interaction_id,
                "user_id": interaction.user_id,
                "username": interaction.username,
                "avatar_url": interaction.avatar_url if interaction.avatar_url else "",
                "interaction_type": interaction.interaction_type,
                "interaction_content": interaction.interaction_content if interaction.interaction_type == "comment" else None,
                "interaction_time": interaction.interaction_time.isoformat()  # 转换为 ISO 格式
            }
            for interaction in interactions
        ]
    }


@bp.route("/user/interactions/<user_id>", methods=["GET"])
def get_interaction_count(user_id: str):
    result = db.session.execute(
        select(
            Interaction.interaction_type,
            func.count().label('count')  # 聚合计数
        )
        .where(Interaction.user_id == user_id)  # 根据用户ID过滤
        .group_by(Interaction.interaction_type)  # 按互动类型分组
    )

    interaction_summary = {
        "comments": 0,
        "likes": 0,
        "retweets": 0
    }

    for row in result.fetchall():
        interaction_type = row.interaction_type
        count = row.count
        if interaction_type == "comment":
            interaction_summary["comments"] = count
        elif interaction_type == "like":
            interaction_summary["likes"] = count
        elif interaction_type == "retweet":
            interaction_summary["retweets"] = count

    total_interactions = sum(interaction_summary.values())

    return {
        "user_id": user_id,
        "total_interactions": total_interactions,
        "interaction_summary": interaction_summary
    }


@bp.route("/accounts", methods=["POST", "PUT", "DELETE"])
def manage_accounts():
    req = request.json
    media_account = req["media_account"]
    start_time = req["start_time"]
    end_time = req["end_time"]
    update_frequency = req["update_frequency"]
    expiration_time = req["expiration_time"]
    # flaskr.logger.info(
    #     f"media_account: {media_account}, start_time: {start_time}, end_time: {end_time}, update_frequency: {update_frequency}, expiration_time: {expiration_time}")
    return {
        "status": "success",
        "message": "Account added/updated/deleted successfully"
    }
