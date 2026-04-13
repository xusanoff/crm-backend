from flask              import Blueprint, request
from flask_jwt_extended import create_access_token, get_jwt_identity
from flask_bcrypt       import check_password_hash
from models.user        import User
from utils.utils        import get_response
from utils.decorators   import role_required

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


# ══════════════════════════════════════════════════════════════════════════════
# LOGIN
# ══════════════════════════════════════════════════════════════════════════════

@auth_bp.route("/login", methods=["POST"])
def login():
    data     = request.get_json()
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return get_response("username and password are required", None, 400), 400

    user = User.query.filter_by(username=username).first()
    if not user:
        return get_response("User not found", None, 404), 404

    if not check_password_hash(user.password, password):
        return get_response("Invalid password", None, 401), 401

    access_token = create_access_token(identity=str(user.id))
    return get_response("Login successful", {
        "access_token": access_token,
        "user":         User.to_dict(user)
    }, 200), 200


# ══════════════════════════════════════════════════════════════════════════════
# ME — hozirgi foydalanuvchi
# ══════════════════════════════════════════════════════════════════════════════

@auth_bp.route("/me", methods=["GET"])
@role_required(["ADMIN", "MANAGER", "OPERATOR"])
def me():
    user_id = int(get_jwt_identity())
    user    = User.query.filter_by(id=user_id).first()
    return get_response("Current user", User.to_dict(user), 200), 200
