from functools import wraps
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from utils.utils import get_response
from models.user import User


def role_required(roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            user_id = int(get_jwt_identity())
            user    = User.query.filter_by(id=user_id).first()

            if not user:
                return get_response("User not found", None, 404), 404

            if user.role not in roles:
                return get_response("Permission denied", None, 403), 403

            return fn(*args, **kwargs)
        return wrapper
    return decorator
