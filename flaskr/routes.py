from concurrent.futures.thread import ThreadPoolExecutor
from datetime import datetime, timezone
from flask import request, Blueprint, current_app
from sqlalchemy import func
from .extensions import db
from sqlalchemy.sql.expression import select
from .models import Interaction
from .services.scheduler import add_xsync_task, remove_xsync_task, fetch_and_store_xdata
from .utils import validate_update_frequency

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
    # todo校验 start_time 和 update_frequency
    try:
        start_dt = datetime.fromisoformat(start_time)
    except ValueError as e:
        current_app.logger.error(f"Invalid start time: {start_time}: {str(e)}")
        return {"status": "error", "message": "Invalid start time format, require ISO 8601 format"}, 400

    if start_dt >= datetime.now(tz=timezone.utc):
        current_app.logger.error(f"Invalid start time: {start_time}")
        return {"status": "error", "message": "Start time must be before update frequency"}, 400

    try:
        frequency_value, frequency_unit = validate_update_frequency(update_frequency)
    except ValueError as e:
        current_app.logger.error(f"Invalid update frequency: {str(e)}")
        return {"status": "error", "message": str(e)}, 400

    if request.method in ["POST", "PUT"]:
        # 之后使用定时任务按照update_frequency周期进行采集，定时任务先开起来，初始化采集会很耗时
        try:
            add_xsync_task(media_account, frequency_unit, frequency_value)

            fetch_and_store_xdata(media_account, start_dt)

            # 后台处理 不好用
            # executor: ThreadPoolExecutor = current_app.extensions.get("executor")
            # executor.submit(fetch_and_store_xdata, media_account, start_dt)
            # current_app.logger.info(f"Task submitted to thread pool for media_account: {media_account}")
        except Exception as e:
            if str(e) == "Media account not found":
                current_app.logger.error(f"Media account not found: {media_account}")
                return {"status": "error", "message": str(e)}, 400
            else:
                current_app.logger.error(f"Failed to fetch xdata or add sync task: {str(e)}")
                return {"status": "error", "message": "Internal Server Error"}, 500
        return {
            "status": "success",
            "message": "Media account sync task updated successfully"
        }

