from datetime               import date
from flask                  import Blueprint, request
from models                 import db
from models.cource          import Course
from models.group           import Group
from models.lesson          import Lesson
from models.teacher         import Teacher
from utils.utils            import get_response
from utils.decorators       import role_required
from utils.lesson_generator import generate_lessons_for_group

course_bp = Blueprint("course", __name__, url_prefix="/api/courses")
group_bp  = Blueprint("group",  __name__, url_prefix="/api/groups")

VALID_SCHEDULES = {"odd", "even"}


# ══════════════════════════════════════════════════════════════════════════════
# KURS CRUD
# ══════════════════════════════════════════════════════════════════════════════

@course_bp.route("", methods=["GET"])
@role_required(["ADMIN", "MANAGER", "OPERATOR"])
def course_list():
    courses = Course.query.all()
    result  = [Course.to_dict(c) for c in courses]
    return get_response("Course List", result, 200), 200


@course_bp.route("", methods=["POST"])
@role_required(["ADMIN"])
def course_create():
    """
    Body example:
    {
        "name": "Python kursi",
        "price": 1200000,
        "duration_months": 3
    }
    Jami narx = price * duration_months = 3,600,000 so'm
    """
    data             = request.get_json()
    name             = data.get("name")
    price            = data.get("price")
    duration_months  = data.get("duration_months", 1)

    if not name or price is None:
        return get_response("name and price are required", None, 400), 400

    try:
        duration_months = int(duration_months)
        if duration_months < 1:
            raise ValueError
    except (ValueError, TypeError):
        return get_response("duration_months must be a positive integer", None, 400), 400

    new_course = Course(
        name            = name,
        price           = float(price),
        duration_months = duration_months,
    )
    db.session.add(new_course)
    db.session.commit()
    return get_response("Course successfully created", Course.to_dict(new_course), 200), 200


@course_bp.route("/<int:course_id>", methods=["GET"])
@role_required(["ADMIN", "MANAGER", "OPERATOR"])
def course_get(course_id):
    course = Course.query.filter_by(id=course_id).first()
    if not course:
        return get_response("Course not found", None, 404), 404
    return get_response("Course found", Course.to_dict(course), 200), 200


@course_bp.route("/<int:course_id>", methods=["PATCH"])
@role_required(["ADMIN"])
def course_update(course_id):
    course = Course.query.filter_by(id=course_id).first()
    if not course:
        return get_response("Course not found", None, 404), 404

    data = request.get_json()
    if data.get("name"):
        course.name = data["name"]
    if data.get("price") is not None:
        course.price = float(data["price"])
    if data.get("duration_months") is not None:
        try:
            dm = int(data["duration_months"])
            if dm < 1:
                raise ValueError
            course.duration_months = dm
        except (ValueError, TypeError):
            return get_response("duration_months must be a positive integer", None, 400), 400

    db.session.commit()
    return get_response("Course successfully updated", Course.to_dict(course), 200), 200


@course_bp.route("/<int:course_id>", methods=["DELETE"])
@role_required(["ADMIN"])
def course_delete(course_id):
    course = Course.query.filter_by(id=course_id).first()
    if not course:
        return get_response("Course not found", None, 404), 404

    db.session.delete(course)
    db.session.commit()
    return get_response("Course successfully deleted", None, 200), 200


# ══════════════════════════════════════════════════════════════════════════════
# GURUH CRUD  +  avtomatik dars yaratish
# ══════════════════════════════════════════════════════════════════════════════

@group_bp.route("", methods=["GET"])
@role_required(["ADMIN", "MANAGER", "OPERATOR"])
def group_list():
    groups = Group.query.all()
    result = [Group.to_dict(g) for g in groups]
    return get_response("Group List", result, 200), 200


@group_bp.route("", methods=["POST"])
@role_required(["ADMIN"])
def group_create():
    """
    Guruh yaratilganda:
    1. start_date kiritiladi (end_date kerak emas — kurs duration_months dan hisoblanadi)
    2. start_date dan end_date gacha barcha dars kunlari avtomatik Lesson jadvaliga qo'shiladi

    Body example:
    {
        "name":          "Python-1",
        "course_id":     1,
        "teacher_name":  "Alisher",
        "start_date":    "2025-02-03",
        "schedule_type": "odd",
        "lesson_time":   "10:00:00"
    }
    """
    data          = request.get_json()
    name          = data.get("name")
    course_id     = data.get("course_id")
    teacher_name  = data.get("teacher_name")
    teacher_id    = data.get("teacher_id")
    schedule_type = (data.get("schedule_type") or "").lower()
    lesson_time   = data.get("lesson_time")
    start_date_str = data.get("start_date")

    if not all([name, course_id, schedule_type, lesson_time]):
        return get_response(
            "name, course_id, schedule_type, lesson_time are required",
            None, 400
        ), 400

    if not teacher_id and not teacher_name:
        return get_response(
            "teacher_id yoki teacher_name kiritish majburiy",
            None, 400
        ), 400

    if schedule_type not in VALID_SCHEDULES:
        return get_response(f"Invalid schedule_type. Valid: {VALID_SCHEDULES}", None, 400), 400

    course = Course.query.filter_by(id=course_id).first()
    if not course:
        return get_response("Course not found", None, 404), 404

    # teacher_id tekshirish
    if teacher_id:
        teacher = Teacher.query.filter_by(id=teacher_id).first()
        if not teacher:
            return get_response("O'qituvchi topilmadi", None, 404), 404
        teacher_name = teacher.full_name  # fallback uchun

    # start_date parse
    start_date = None
    if start_date_str:
        try:
            start_date = date.fromisoformat(start_date_str)
        except ValueError:
            return get_response("Invalid start_date format. Use YYYY-MM-DD", None, 400), 400

    new_group = Group(
        name          = name,
        course_id     = course_id,
        teacher_name  = teacher_name,
        teacher_id    = teacher_id,
        schedule_type = schedule_type,
        lesson_time   = lesson_time,
        start_date    = start_date,
    )
    db.session.add(new_group)
    db.session.commit()

    # Avtomatik darslarni yaratish
    lesson_count = generate_lessons_for_group(new_group)

    group_data = Group.to_dict(new_group)
    group_data["message"] = (
        f"Kurs {course.duration_months} oy davom etadi. "
        f"Tugash: {new_group.end_date}. "
        f"{lesson_count} ta dars yaratildi."
    )

    return get_response(
        f"Group successfully created ({lesson_count} lessons generated)",
        group_data,
        200
    ), 200


@group_bp.route("/<int:group_id>", methods=["GET"])
@role_required(["ADMIN", "MANAGER", "OPERATOR"])
def group_get(group_id):
    group = Group.query.filter_by(id=group_id).first()
    if not group:
        return get_response("Group not found", None, 404), 404
    return get_response("Group found", Group.to_dict(group), 200), 200


@group_bp.route("/<int:group_id>", methods=["PATCH"])
@role_required(["ADMIN"])
def group_update(group_id):
    """
    Agar start_date yoki schedule_type o'zgarsa, yangi darslar avtomatik qo'shiladi.
    """
    group = Group.query.filter_by(id=group_id).first()
    if not group:
        return get_response("Group not found", None, 404), 404

    data = request.get_json()

    if data.get("name"):
        group.name = data["name"]
    if data.get("teacher_name"):
        group.teacher_name = data["teacher_name"]
    if data.get("teacher_id") is not None:
        t_id = data["teacher_id"]
        if t_id:
            teacher = Teacher.query.filter_by(id=t_id).first()
            if not teacher:
                return get_response("O'qituvchi topilmadi", None, 404), 404
            group.teacher_id   = t_id
            group.teacher_name = teacher.full_name
        else:
            group.teacher_id = None
    if data.get("lesson_time"):
        group.lesson_time = data["lesson_time"]

    schedule_changed = False

    if data.get("schedule_type"):
        schedule_type = data["schedule_type"].lower()
        if schedule_type not in VALID_SCHEDULES:
            return get_response(f"Invalid schedule_type. Valid: {VALID_SCHEDULES}", None, 400), 400
        group.schedule_type = schedule_type
        schedule_changed    = True

    if "start_date" in data:
        if data["start_date"]:
            try:
                group.start_date = date.fromisoformat(data["start_date"])
            except ValueError:
                return get_response("Invalid start_date format. Use YYYY-MM-DD", None, 400), 400
        else:
            group.start_date = None
        schedule_changed = True

    db.session.commit()

    lesson_count = 0
    if schedule_changed:
        lesson_count = generate_lessons_for_group(group)

    return get_response(
        f"Group successfully updated ({lesson_count} new lessons generated)" if lesson_count
        else "Group successfully updated",
        Group.to_dict(group),
        200
    ), 200


@group_bp.route("/<int:group_id>", methods=["DELETE"])
@role_required(["ADMIN"])
def group_delete(group_id):
    group = Group.query.filter_by(id=group_id).first()
    if not group:
        return get_response("Group not found", None, 404), 404

    Lesson.query.filter_by(group_id=group_id).delete()
    db.session.delete(group)
    db.session.commit()
    return get_response("Group and its lessons successfully deleted", None, 200), 200


@group_bp.route("/<int:group_id>/generate-lessons", methods=["POST"])
@role_required(["ADMIN"])
def group_generate_lessons(group_id):
    group = Group.query.filter_by(id=group_id).first()
    if not group:
        return get_response("Group not found", None, 404), 404

    count = generate_lessons_for_group(group)
    return get_response(f"{count} new lessons generated", None, 200), 200


@group_bp.route("/<int:group_id>/info", methods=["GET"])
@role_required(["ADMIN", "MANAGER", "OPERATOR"])
def group_info(group_id):
    """
    Guruh haqida to'liq ma'lumot: qachon boshlanadi, qachon tugaydi,
    necha oy davom etadi, rejalashtirilgan darslar soni.
    """
    group = Group.query.filter_by(id=group_id).first()
    if not group:
        return get_response("Group not found", None, 404), 404

    lesson_count = Lesson.query.filter_by(group_id=group_id).count()

    info = {
        **Group.to_dict(group),
        "total_lessons_scheduled": lesson_count,
        "info": (
            f"'{group.name}' guruhi {group.start_date} da boshlanib, "
            f"{group.end_date} da tugaydi. "
            f"Jami {group.duration_months} oy, {lesson_count} ta dars."
        )
    }
    return get_response("Group Info", info, 200), 200