from flask              import Blueprint, request
from flask_jwt_extended import get_jwt_identity
from models             import db
from models.user        import User
from utils.utils        import get_response
from utils.decorators   import role_required

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")

VALID_ROLES = {"ADMIN", "MANAGER", "OPERATOR"}


# ══════════════════════════════════════════════════════════════════════════════
# FOYDALANUVCHILAR (faqat ADMIN)
# ══════════════════════════════════════════════════════════════════════════════

@admin_bp.route("/users", methods=["GET"])
@role_required(["ADMIN"])
def user_list():
    users  = User.query.order_by(User.created_at.desc()).all()
    result = [User.to_dict(u) for u in users]
    return get_response("User List", result, 200), 200


@admin_bp.route("/users", methods=["POST"])
@role_required(["ADMIN"])
def user_create():
    data      = request.get_json()
    full_name = data.get("full_name")
    username  = data.get("username")
    password  = data.get("password")
    role      = data.get("role", "").upper()

    if not full_name or not username or not password or not role:
        return get_response("full_name, username, password, role are required", None, 400), 400

    if role not in VALID_ROLES:
        return get_response(f"Invalid role. Valid: {VALID_ROLES}", None, 400), 400

    if User.query.filter_by(username=username).first():
        return get_response("Username already exists", None, 400), 400

    new_user = User(
        full_name = full_name,
        username  = username,
        password  = password,
        role      = role
    )
    db.session.add(new_user)
    db.session.commit()
    return get_response("User successfully created", User.to_dict(new_user), 200), 200


@admin_bp.route("/users/<int:user_id>", methods=["GET"])
@role_required(["ADMIN"])
def user_get(user_id):
    user = User.query.filter_by(id=user_id).first()
    if not user:
        return get_response("User not found", None, 404), 404
    return get_response("User found", User.to_dict(user), 200), 200


@admin_bp.route("/users/<int:user_id>", methods=["PATCH"])
@role_required(["ADMIN"])
def user_update(user_id):
    user = User.query.filter_by(id=user_id).first()
    if not user:
        return get_response("User not found", None, 404), 404

    data = request.get_json()

    if data.get("full_name"):
        user.full_name = data["full_name"]

    if data.get("username"):
        existing = User.query.filter_by(username=data["username"]).first()
        if existing and existing.id != user_id:
            return get_response("Username already taken", None, 400), 400
        user.username = data["username"]

    if data.get("role"):
        role = data["role"].upper()
        if role not in VALID_ROLES:
            return get_response(f"Invalid role. Valid: {VALID_ROLES}", None, 400), 400
        user.role = role

    if data.get("password"):
        from flask_bcrypt import generate_password_hash
        user.password = generate_password_hash(data["password"]).decode("utf-8")

    db.session.commit()
    return get_response("User successfully updated", User.to_dict(user), 200), 200


@admin_bp.route("/users/<int:user_id>", methods=["DELETE"])
@role_required(["ADMIN"])
def user_delete(user_id):
    current_id = int(get_jwt_identity())
    if current_id == user_id:
        return get_response("You cannot delete yourself", None, 400), 400

    user = User.query.filter_by(id=user_id).first()
    if not user:
        return get_response("User not found", None, 404), 404

    db.session.delete(user)
    db.session.commit()
    return get_response("User successfully deleted", None, 200), 200
