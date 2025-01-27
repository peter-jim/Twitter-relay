from datetime import datetime, timedelta, timezone
from flask import Blueprint, request, current_app
from flaskr.utils import require_api_key, response_bad_request, response_internal_server_error
from .models import ApiKey
from .extensions import db
from sqlalchemy import delete, select

bp = Blueprint('admin', __name__, url_prefix="/admin")

@bp.route("/api-keys", methods=["GET"])
@require_api_key(admin_required=True)   # admin api key is required
def list_api_keys():
    """List all API keys"""
    keys = db.session.execute(select(ApiKey)).scalars().all()
    return {
        "api_keys": [
            {
                "id": key.id,
                "api_name": key.api_name,
                "is_active": key.is_active,
                "created_at": key.created_at.isoformat(),
                "expires_at": key.expires_at.isoformat() if key.expires_at else None,
                "last_used_at": key.last_used_at.isoformat() if key.last_used_at else None
            }
            for key in keys
        ]
    }

@bp.route("/api-keys", methods=["POST"])
@require_api_key(admin_required=True)   # admin api key is required
def create_api_key():
    """Create a new API key"""
    req = request.json
    name = req.get("name")
    days_valid = req.get("days_valid")  # Optional expiration in days
    
    if not name:
        return response_bad_request("Name is required")
    
    # generate api key and secret
    api_key, api_secret = ApiKey.generate_credentials()
    
    api_key_obj = ApiKey(
        api_key=api_key,
        api_secret=api_secret,
        api_name=name,
        expires_at=datetime.now(timezone.utc) + timedelta(days=days_valid) if days_valid else None
    )
    
    try:
        db.session.add(api_key_obj)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to create API key: {str(e)}")
        return response_internal_server_error()
    
    return {
        "status": "success",
        "message": "API key created successfully",
        "api_key": {
            "id": api_key_obj.id,
            "api_key": api_key_obj.api_key,
            "api_secret": api_key_obj.api_secret,
            "api_name": api_key_obj.api_name,
            "expires_at": api_key_obj.expires_at.isoformat() if api_key_obj.expires_at else None
        }
    }

@bp.route("/api-keys/<int:key_id>", methods=["PUT"])
@require_api_key(admin_required=True)   # admin api key is required
def update_api_key(key_id: int):
    """Update API key status"""
    req = request.json
    is_active = req.get("is_active")
    
    if is_active is None:
        return response_bad_request("is_active is required")
    
    try:
        api_key = db.session.execute(
            select(ApiKey).where(ApiKey.id == key_id)
        ).scalar_one()
        
        api_key.is_active = is_active
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to update API key: {str(e)}")
        return response_internal_server_error()
    
    return {
        "status": "success",
        "message": "API key updated successfully"
    }

@bp.route("/api-keys/<int:key_id>", methods=["DELETE"])
@require_api_key(admin_required=True)   # admin api key is required
def delete_api_key(key_id: int):
    """Delete an API key"""
    try:
        db.session.execute(
            delete(ApiKey).where(ApiKey.id == key_id)
        )
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to delete API key: {str(e)}")
        return response_internal_server_error()
    
    return {
        "status": "success",
        "message": "API key deleted successfully"
    }