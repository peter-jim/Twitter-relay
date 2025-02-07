from datetime import datetime
from functools import partial, wraps
from idlelib.rpc import request_queue

from flask import request, current_app
from .models import ApiKey
from datetime import datetime, timezone
from sqlalchemy import select
from .extensions import db

def validate_update_frequency(update_frequency: str) -> tuple[int, str]:
    try:
        # Split the string, extract the number and unit
        parts = update_frequency.split()
        if len(parts) != 2:
            raise ValueError("update_frequency must be in the format '<number> <unit>' (e.g., '1 minute').")

        value = int(parts[0])  # Extract the number
        unit = parts[1].lower()  # Extract the unit and convert to lowercase

        # Validate the unit is valid
        valid_units = ['second', 'seconds', 'minute', 'minutes', 'hour', 'hours', 'day', 'days', 'week', 'weeks']
        if unit not in valid_units:
            raise ValueError(f"Invalid unit: {unit}. Supported units are: {valid_units}.")

        # Validate the value is a positive integer
        if value <= 0:
            raise ValueError(f"Invalid value: {value}. Value must be a positive integer.")

        return value, unit
    except ValueError as e:
        raise ValueError(f"Invalid update_frequency: {update_frequency}. {str(e)}")


def datetime_as_db_format(time_str: str) -> datetime:
    return datetime.fromisoformat(time_str.replace("Z", "+00:00"))


def response_media_not_found(e: str):
    if e == "Media account not found":
        # current_app.logger.error(f"Media account not found: {media_account}")
        return {"status": "error", "message": e}, 400
    else:
        # current_app.logger.error(f"Failed to fetch xdata or add sync task: {str(e)}")
        return response_internal_server_error()


def response_internal_server_error():
    return {"status": "error", "message": "Internal Server Error"}, 500


def response_bad_request(msg: str):
    return {"status": "error", "message": msg}, 400


def require_api_key(f=None, *, admin_required=False):
    if f is None:
        return partial(require_api_key, admin_required=admin_required)
        
    @wraps(f)
    def wrapper(*args, **kwargs):
        # get api key, signature, timestamp
        api_key = request.headers.get('X-API-Key')
        signature = request.headers.get('X-Signature')
        timestamp = request.headers.get('X-Timestamp')
        
        if not api_key or not signature or not timestamp:
            return {
                "status": "error",
                "message": "Missing API key, signature or timestamp"
            }, 401
            
        try:
            # check timestamp
            try:
                req_time = int(timestamp)
                current_time = int(datetime.now(timezone.utc).timestamp())
                # allow 5 minutes time difference
                if abs(current_time - req_time) > 300:
                    return {
                        "status": "error",
                        "message": "Request expired"
                    }, 401
            except ValueError:
                return {
                    "status": "error",
                    "message": "Invalid timestamp"
                }, 401
            
            # get api key record
            key = db.session.execute(
                select(ApiKey).where(ApiKey.api_key == api_key)
            ).scalar_one()
            
            if not key.is_valid():
                return {
                    "status": "error",
                    "message": "Invalid or expired API key"
                }, 401
            
            # construct message for hmac verification
            message = f"{request.method}{request.path}{timestamp}"
            if request.is_json:
                message += request.get_data(as_text=True) or "{}"

            # check hmac signature
            if not key.verify_hmac(signature, message):
                return {
                    "status": "error",
                    "message": "Invalid signature"
                }, 401
            
            if admin_required and not key.is_admin:
                return {
                    "status": "error",
                    "message": "Admin privileges required"
                }, 403
                
            # Update last used timestamp
            key.last_used_at = datetime.now(timezone.utc)
            db.session.commit()
            
        except Exception as e:
            current_app.logger.error(f"API key validation failed: {str(e)}")
            return {
                "status": "error",
                "message": "Invalid API key"
            }, 401
            
        return f(*args, **kwargs)
    return wrapper