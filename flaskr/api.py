from datetime import datetime, timezone
from flask import request, Blueprint, current_app
from sqlalchemy import  func
from sqlalchemy.pool.impl import exc
from .extensions import db
from sqlalchemy.sql.expression import select
from .models import Interaction
from .services.scheduler import add_xsync_once_task, add_xsync_task, remove_xsync_task, DataCollector
from .utils import require_api_key, validate_update_frequency, response_media_not_found, response_internal_server_error, \
    response_bad_request

bp = Blueprint('api', __name__, url_prefix="/api")

@bp.route("/ping", methods=['GET'])
def ping():
    """Simple ping endpoint to verify API is responsive"""
    return {"status": "success", "message": "pong"}


@bp.route("/health", methods=['GET'])
def health():
    """Health check endpoint that verifies critical system components"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "components": {
            "database": "healthy",
            "api": "healthy"
        }
    }

    # Check database connection
    try:
        # Perform a simple database query
        db.session.execute(select(1)).scalar()
    except Exception as e:
        current_app.logger.error(f"Database health check failed: {str(e)}")
        health_status["status"] = "unhealthy"
        health_status["components"]["database"] = "unhealthy"

    # Return 200 if healthy, 503 if unhealthy
    status_code = 200 if health_status["status"] == "healthy" else 503

    return health_status, status_code


@bp.route("/interaction/<media_account>", methods=['GET'])
def get_interactions(media_account: str):
    try:
         # Get pagination parameters and username from request args
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        username =  request.args.get('username', None)

        start_time = request.args.get("start_time", None)
        if start_time:
            try:
                datetime.fromisoformat(start_time)
            except ValueError:
                return response_bad_request("Invalid start time format, require YYYY-MM-DDTHH:mm:ssZ format")

            if not start_time.endswith("Z"):
                return response_bad_request("Invalid start time format, require YYYY-MM-DDTHH:mm:ssZ format")

        end_time = request.args.get("end_time", None)
        if end_time:
            try:
                datetime.fromisoformat(end_time)
            except ValueError:
                return response_bad_request("Invalid start time format, require YYYY-MM-DDTHH:mm:ssZ format")

            if not end_time.endswith("Z"):
                return response_bad_request("Invalid start time format, require YYYY-MM-DDTHH:mm:ssZ format")

        current_app.logger.error(f"Database health check failed: {start_time}, {end_time}")

        # Validate pagination parameters
        if page < 1:
            return response_bad_request("Page number must be greater than 0")
        if per_page < 1 or per_page > 100:
            return response_bad_request("Items per page must be between 1 and 100")

        # basic query
        query = select(Interaction).where(Interaction.media_account == media_account)

        if username:
            query = query.where(Interaction.username == username)

        if start_time:
            query = query.where(Interaction.interaction_time >= start_time)

        if end_time:
            query = query.where(Interaction.interaction_time <= end_time)

        result = db.session.execute(
            query
            .order_by(Interaction.interaction_time.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )

        # total count basic query
        count_query = select(func.count()).select_from(Interaction).where(Interaction.media_account == media_account)
        if username:
            count_query = count_query.where(Interaction.username == username)

        if start_time:
            query = query.where(Interaction.interaction_time >= start_time)

        if end_time:
            query = query.where(Interaction.interaction_time <= end_time)

        # Get total count for pagination info
        total_count = db.session.execute(count_query).scalar()
        if not total_count:
            current_app.logger.warning("unexpected! total count cannot be None.")
            total_count = 0

        # Calculate pagination metadata
        total_pages = (total_count + per_page - 1) // per_page
        has_next = page < total_pages
        has_prev = page > 1

        interactions = result.scalars().all()
    except Exception as e:
        current_app.logger.error(f"Failed to get interactions: {str(e)}")
        return response_internal_server_error()

    return {
        "media_account": media_account,
        "username": username,
        "pagination": {
            "current_page": page,
            "per_page": per_page,
            "total_items": total_count,
            "total_pages": total_pages,
            "has_next": has_next,
            "has_prev": has_prev
        },
        "interactions": [
            {
                "interaction_id": interaction.interaction_id,
                "user_id": interaction.user_id,
                "username": interaction.username,
                "avatar_url": interaction.avatar_url,
                "interaction_type": interaction.interaction_type,
                "interaction_content": interaction.interaction_content,
                "interaction_time": interaction.interaction_time.isoformat(),  # Convert to ISO format
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
                func.count().label('count')  # Aggregate count
            )
            .where(Interaction.user_id == user_id)  # Filter by user ID
            .group_by(Interaction.interaction_type)  # Group by interaction type
        )

        interaction_summary = {
            "reply": 0,
            "quote": 0,
            "retweet": 0,
            "mention": 0
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
            elif  interaction_type == "mention":
                interaction_summary["mention"] = count

        total_interactions = sum(interaction_summary.values())
    except Exception as e:
        current_app.logger.error(f"Failed to get interaction count: {str(e)}")
        return response_internal_server_error()

    return {
        "user_id": user_id,
        "total_interactions": total_interactions,
        "interaction_summary": interaction_summary
    }


@bp.route("/accounts", methods=["POST", "PUT", "DELETE"])
@require_api_key
def manage_accounts():
    req = request.json
    if not req:
        return response_bad_request("Request body is required")

    try:
        media_account = req["media_account"]
    except  KeyError:
        return response_bad_request("media_account field is required")

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
    # Validate start_time and update_frequency
    try:
        if not start_time.endswith("Z"):
            return response_bad_request("Invalid start time format, require YYYY-MM-DDTHH:mm:ssZ format")
        start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        # Ensure it's UTC
        if start_dt.tzinfo != timezone.utc:
            start_dt = start_dt.replace(tzinfo=timezone.utc)
    except ValueError as e:
        current_app.logger.error(f"Invalid start time: {start_time}: {str(e)}")
        return response_bad_request("Invalid start time format, require YYYY-MM-DDTHH:mm:ssZ format")

    if start_dt >= datetime.now(tz=timezone.utc):
        current_app.logger.error(f"Invalid start time: {start_time}")
        return response_bad_request("Start time must be before update frequency")

    try:
        frequency_value, frequency_unit = validate_update_frequency(update_frequency)
    except ValueError as e:
        current_app.logger.error(f"Invalid update frequency: {str(e)}")
        return response_bad_request(str(e))

    if request.method in ["POST", "PUT"]:
        try:
            # Validate media account before adding tasks
            dc = DataCollector.default(media_account)
            # Try to get some data to verify the account exists and is accessible
            dc.validate_media_account()

            add_xsync_task(media_account, frequency_unit, frequency_value, start_dt)
            add_xsync_once_task(media_account, start_dt)  # Add a one-time initialization task to execute immediately
        except Exception as e:
            return response_media_not_found(str(e))
        return {
            "status": "success",
            "message": "Media account sync task updated successfully"
        }


@bp.route("/person", methods=["POST"])
@require_api_key
def manage_person():
    req = request.json
    current_app.logger.debug(f"req: {req}")
    if not req:
        current_app.logger.error("no request body")
        return response_bad_request("Request body is required")

    try:
        media_account = req["media_account"]
        username = req["username"]
        start_time = req.get("start_time")
        if start_time:
            try:
                datetime.fromisoformat(start_time)
            except ValueError:
                return response_bad_request("Invalid start time format, require YYYY-MM-DDTHH:mm:ssZ format")

            if not start_time.endswith("Z"):
                return response_bad_request("Invalid start time format, require YYYY-MM-DDTHH:mm:ssZ format")

    except  KeyError as e:
        current_app.logger.error(f"Failed to get media account or username: {str(e)}")
        return response_bad_request("media_account and username field is required")

    try:
        dc = DataCollector.default(media_account)
        interactions_data = dc.get_user_recent_interactions(username, start_time)


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
                merged_interactions.append(new_interaction)  # Use to_dict method to format time
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
                "interaction_time": interaction.interaction_time.isoformat(),  # Convert to ISO format
                "post_id": interaction.post_id,
                "post_time": interaction.post_time.isoformat() if interaction.post_time else None,
            }
            for interaction in merged_interactions
        ]
    }
