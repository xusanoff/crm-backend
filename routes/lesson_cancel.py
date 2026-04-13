"""
Darsni bekor qilish va surish uchun routelar.
Bu fayl `courses_groups.py` ga qo'shib yoki alohida blueprint sifatida ishlatilishi mumkin.
Bu yerda alohida blueprint sifatida yozilgan — app.py ga ro'yxatdan o'tkazish kifoya.
"""

from datetime                     import date
from flask                        import Blueprint, request
from models                       import db
from models.group                 import Group
from models.lesson                import Lesson
from utils.utils                  import get_response
from utils.decorators             import role_required
from utils.reschedule_helper      import cancel_and_reschedule

lesson_bp = Blueprint("lesson", __name__, url_prefix="/api/lessons")


# ══════════════════════════════════════════════════════════════════════════════
# DARS BEKOR QILISH + AVTOMATIK SURISH
# ══════════════════════════════════════════════════════════════════════════════

@lesson_bp.route("/cancel", methods=["POST"])
@role_required(["ADMIN", "MANAGER"])
def lesson_cancel():
    """
    Guruh uchun ma'lum sanani bekor qilib, keyingi bo'sh ish kuniga suradi.

    Body:
    {
        "group_id":    3,
        "cancel_date": "2025-03-05",
        "reason":      "Bayram"        ← ixtiyoriy
    }

    Javob:
    {
        "cancelled_lesson":   { ...lesson... },
        "rescheduled_lesson": { ...lesson... } | null,
        "warning":            null | "..."
    }
    """
    data        = request.get_json()
    group_id    = data.get("group_id")
    cancel_date = data.get("cancel_date")
    reason      = data.get("reason")

    if not group_id or not cancel_date:
        return get_response("group_id and cancel_date are required", None, 400), 400

    group = Group.query.filter_by(id=group_id).first()
    if not group:
        return get_response("Group not found", None, 404), 404

    try:
        c_date = date.fromisoformat(cancel_date)
    except ValueError:
        return get_response("Invalid cancel_date format. Use YYYY-MM-DD", None, 400), 400

    result, error = cancel_and_reschedule(group, c_date, reason)
    if error:
        return get_response(error, None, 404), 404

    return get_response("Lesson cancelled and rescheduled", result, 200), 200


# ══════════════════════════════════════════════════════════════════════════════
# GURUH DARSLARI RO'YXATI — filter bilan
# ══════════════════════════════════════════════════════════════════════════════

@lesson_bp.route("/group/<int:group_id>", methods=["GET"])
@role_required(["ADMIN", "MANAGER", "OPERATOR"])
def lessons_by_group(group_id):
    """
    Guruhning barcha darslarini qaytaradi.
    Ixtiyoriy query params:
      ?show_cancelled=true   — bekor qilinganlar ham ko'rinsin (default: hammasi)
      ?only_rescheduled=true — faqat surilgan darslar
    """
    group = Group.query.filter_by(id=group_id).first()
    if not group:
        return get_response("Group not found", None, 404), 404

    show_cancelled    = request.args.get("show_cancelled", "true").lower() == "true"
    only_rescheduled  = request.args.get("only_rescheduled", "false").lower() == "true"

    query = Lesson.query.filter_by(group_id=group_id)

    if not show_cancelled:
        query = query.filter_by(is_cancelled=False)

    if only_rescheduled:
        query = query.filter_by(is_rescheduled=True)

    lessons = query.order_by(Lesson.lesson_date.asc()).all()
    result  = [Lesson.to_dict(l) for l in lessons]
    return get_response(f"Lessons for group #{group_id}", result, 200), 200


# ══════════════════════════════════════════════════════════════════════════════
# BEKOR QILISHNI QAYTARISH (undo cancel)
# ══════════════════════════════════════════════════════════════════════════════

@lesson_bp.route("/<int:lesson_id>/restore", methods=["PATCH"])
@role_required(["ADMIN", "MANAGER"])
def lesson_restore(lesson_id):
    """
    Bekor qilingan darsni qayta faollashtirish.
    Agar bu darsning surma nusxasi (rescheduled) mavjud bo'lsa,
    o'sha ham o'chiriladi (chunki endi kerak emas).
    """
    lesson = Lesson.query.filter_by(id=lesson_id).first()
    if not lesson:
        return get_response("Lesson not found", None, 404), 404

    if not lesson.is_cancelled:
        return get_response("Lesson is not cancelled", None, 400), 400

    # Surilgan nusxani topib o'chirish
    rescheduled = Lesson.query.filter_by(
        group_id      = lesson.group_id,
        original_date = lesson.lesson_date,
        is_rescheduled = True
    ).first()

    if rescheduled:
        db.session.delete(rescheduled)

    lesson.is_cancelled  = False
    lesson.cancel_reason = None
    db.session.commit()

    return get_response("Lesson restored", Lesson.to_dict(lesson), 200), 200


# ══════════════════════════════════════════════════════════════════════════════
# DARSNI QO'LDA BOSHQA KUNGA O'TKAZISH
# ══════════════════════════════════════════════════════════════════════════════

@lesson_bp.route("/<int:lesson_id>/move", methods=["PATCH"])
@role_required(["ADMIN", "MANAGER"])
def lesson_move(lesson_id):
    """
    Darsni qo'lda tanlangan sanaga o'tkazish (avtomatik emas).

    Body:
    {
        "new_date": "2025-03-10",
        "reason":   "O'qituvchi kasal"
    }
    """
    lesson = Lesson.query.filter_by(id=lesson_id).first()
    if not lesson:
        return get_response("Lesson not found", None, 404), 404

    data     = request.get_json()
    new_date = data.get("new_date")
    reason   = data.get("reason")

    if not new_date:
        return get_response("new_date is required", None, 400), 400

    try:
        n_date = date.fromisoformat(new_date)
    except ValueError:
        return get_response("Invalid new_date format. Use YYYY-MM-DD", None, 400), 400

    if n_date.weekday() == 6:
        return get_response("Cannot move lesson to Sunday", None, 400), 400

    group = Group.query.filter_by(id=lesson.group_id).first()
    if n_date > group.end_date:
        return get_response("new_date exceeds group end_date", None, 400), 400

    # Shu sana uchun allaqachon dars bormi?
    conflict = Lesson.query.filter_by(
        group_id    = lesson.group_id,
        lesson_date = n_date,
        is_cancelled = False
    ).first()
    if conflict:
        return get_response(
            f"{n_date} sanasida bu guruhda allaqachon faol dars mavjud", None, 400
        ), 400

    # Eski sanani bekor qilish, yangi sanaga o'tkazish
    old_date            = lesson.lesson_date
    lesson.is_cancelled   = True
    lesson.cancel_reason  = reason or "Qo'lda surildi"

    new_lesson = Lesson(
        group_id       = lesson.group_id,
        lesson_date    = n_date,
        lesson_time    = lesson.lesson_time,
        is_rescheduled = True,
        original_date  = old_date,
    )
    db.session.add(new_lesson)
    db.session.commit()

    return get_response("Lesson moved", {
        "cancelled_lesson":   Lesson.to_dict(lesson),
        "rescheduled_lesson": Lesson.to_dict(new_lesson),
    }, 200), 200
