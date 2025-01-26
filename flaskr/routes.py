from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import tweepy
from flask import request, Blueprint, current_app
from sqlalchemy import func
from .extensions import db
from sqlalchemy.sql.expression import select
from .models import Interaction
from .services.scheduler import add_xsync_once_task, add_xsync_task, remove_xsync_task, DataCollector
from .utils import validate_update_frequency, response_media_not_found, response_internal_server_error, \
    response_bad_request

bp = Blueprint('api', __name__, url_prefix="/api")


@bp.route("/interaction/<media_account>", methods=['GET'])
def get_interactions(media_account: str):
    try:
        result = db.session.execute(
            select(Interaction).where(Interaction.media_account == media_account)
        )
        interactions = result.scalars().all()
    except Exception:
        return response_internal_server_error()

    return {
        "media_account": media_account,
        "interactions": [
            {
                "interaction_id": interaction.interaction_id,
                "user_id": interaction.user_id,
                "username": interaction.username,
                "avatar_url": interaction.avatar_url,
                "interaction_type": interaction.interaction_type,
                "interaction_content": interaction.interaction_content,
                "interaction_time": interaction.interaction_time.isoformat(),  # 转换为 ISO 格式
                "post_id": interaction.post_id,
                "post_time": interaction.post_time.isoformat(),
            }
            for interaction in interactions
        ]
    }


@bp.route("/user/interactions/<user_id>", methods=["GET"])
def get_interaction_count(user_id: str):
    try:
        result = db.session.execute(
            select(
                Interaction.interaction_type,
                func.count().label('count')  # 聚合计数
            )
            .where(Interaction.user_id == user_id)  # 根据用户ID过滤
            .group_by(Interaction.interaction_type)  # 按互动类型分组
        )

        interaction_summary = {
            "reply": 0,
            "quote": 0,
            "retweet": 0
        }

        for row in result.fetchall():
            interaction_type = row.interaction_type
            count = row.count
            if interaction_type == "reply":
                interaction_summary["reply"] = count
            elif interaction_type == "quote":
                interaction_summary["quote"] = count
            elif interaction_type == "retweet":
                interaction_summary["retweet"] = count

        total_interactions = sum(interaction_summary.values())
    except Exception:
        return response_internal_server_error()

    return {
        "user_id": user_id,
        "total_interactions": total_interactions,
        "interaction_summary": interaction_summary
    }


@bp.route("/accounts", methods=["POST", "PUT", "DELETE"])
def manage_accounts():
    req = request.json
    media_account = req["media_account"]

    if request.method == "DELETE":
        try:
            remove_xsync_task(media_account)
        except ValueError as e:
            current_app.logger.error(f"Failed to remove xdata for {media_account}: {str(e)}")
            return {"status": "error", "message": str(e)}, 400
        return {
            "status": "success",
            "message": "Media account sync task deleted successfully"
        }

    start_time = req["start_time"]
    update_frequency = req["update_frequency"]
    # 校验 start_time 和 update_frequency
    try:
        start_dt = datetime.fromisoformat(start_time)
    except ValueError as e:
        current_app.logger.error(f"Invalid start time: {start_time}: {str(e)}")
        return response_bad_request("Invalid start time format, require ISO 8601 format")

    if start_dt >= datetime.now(tz=timezone.utc):
        current_app.logger.error(f"Invalid start time: {start_time}")
        return response_bad_request("Start time must be before update frequency")

    try:
        frequency_value, frequency_unit = validate_update_frequency(update_frequency)
    except ValueError as e:
        current_app.logger.error(f"Invalid update frequency: {str(e)}")
        return response_bad_request(str(e))

    if request.method in ["POST", "PUT"]:
        # 之后使用定时任务按照update_frequency周期进行采集，定时任务先开起来，初始化采集会很耗时
        try:
            add_xsync_task(media_account, frequency_unit, frequency_value)

            # 添加一次性的初始化任务，立即执行
            add_xsync_once_task(media_account, start_dt)

            # fetch_and_store_xdata(media_account, start_dt)
        except Exception as e:
            return response_media_not_found(str(e))
        return {
            "status": "success",
            "message": "Media account sync task updated successfully"
        }


@bp.route("/person", methods=["POST"])
def get_interactions_by_user():
    req = request.json
    media_account = req["media_account"]
    username = req["username"]
    try:
        dc = DataCollector.default(media_account)
        interactions_data = dc.get_user_recent_interactions(username)


    except Exception as e:
        current_app.logger.error(f"Failed to get user recent interactions: {str(e)}")
        return response_media_not_found(str(e))

    merged_interactions = []
    for interaction_data in interactions_data:
        interaction = Interaction(**interaction_data)
        try:
            db.session.merge(interaction)
            db.session.commit()

            result = db.session.execute(
                select(Interaction).where(Interaction.interaction_id == interaction.interaction_id))
            new_interaction = result.scalar()

            if new_interaction:
                merged_interactions.append(new_interaction)  # 使用 to_dict 方法格式化时间
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Failed to add interaction: {str(e)}")
            continue

    return {
        "media_account": media_account,
        "interactions": [
            {
                "interaction_id": interaction.interaction_id,
                "user_id": interaction.user_id,
                "username": interaction.username,
                "avatar_url": interaction.avatar_url,
                "interaction_type": interaction.interaction_type,
                "interaction_content": interaction.interaction_content,
                "interaction_time": interaction.interaction_time.isoformat(),  # 转换为 ISO 格式
                "post_id": interaction.post_id,
                "post_time": interaction.post_time.isoformat(),
            }
            for interaction in merged_interactions
        ]
    }
