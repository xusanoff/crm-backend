from flask              import Blueprint, request
from flask_jwt_extended import get_jwt_identity
from models             import db
from models.user        import User
from models.lesson      import Lesson
from models.attendance  import Attendance
from models.ernollmert  import Enrollment
from models.payment     import Payment, Debt, MonthlyDebt
from models.student     import Student
from models.group       import Group
from utils.utils        import get_response
from utils.decorators   import role_required

manager_bp = Blueprint("manager", __name__, url_prefix="/api/manager")

VALID_ATTENDANCE_STATUSES = {"keldi", "kelmadi", "kechikdi"}


# ══════════════════════════════════════════════════════════════════════════════
# DAVOMAT — guruhlar ro'yxati va belgilash
# ══════════════════════════════════════════════════════════════════════════════

@manager_bp.route("/groups", methods=["GET"])
@role_required(["ADMIN", "MANAGER", "OPERATOR"])
def groups_for_attendance():
    """
    Davomat bo'limi uchun: barcha guruhlar ro'yxati.
    Frontend bu endpointni chaqirib ekranda guruhlarni ko'rsatadi.
    """
    groups = Group.query.all()
    result = []
    for g in groups:
        result.append({
            "id":           g.id,
            "name":         g.name,
            "course_name":  g.course.name if g.course else None,
            "teacher_name": g.teacher_name,
            "start_date":   str(g.start_date),
            "end_date":     str(g.end_date) if g.end_date else None,
            "schedule_type": g.schedule_type,
            "lesson_time":  str(g.lesson_time),
        })
    return get_response("Groups List", result, 200), 200


@manager_bp.route("/groups/<int:group_id>/students", methods=["GET"])
@role_required(["ADMIN", "MANAGER", "OPERATOR"])
def group_students(group_id):
    """
    Tanlangan guruhda aktiv o'qiydigan o'quvchilar ro'yxati.
    Davomat belgilash uchun ishlatiladi.
    """
    group = Group.query.filter_by(id=group_id).first()
    if not group:
        return get_response("Group not found", None, 404), 404

    enrollments = Enrollment.query.filter_by(
        group_id=group_id, status="active"
    ).all()

    students = []
    for e in enrollments:
        s = Student.query.filter_by(id=e.student_id).first()
        if s:
            students.append({
                "enrollment_id": e.id,
                "student_id":    s.id,
                "full_name":     s.full_name,
                "phone_number":  s.phone_number,
            })

    return get_response(
        f"Students in group '{group.name}'",
        {"group": {"id": group.id, "name": group.name}, "students": students},
        200
    ), 200


@manager_bp.route("/groups/<int:group_id>/lessons", methods=["GET"])
@role_required(["ADMIN", "MANAGER", "OPERATOR"])
def group_lessons(group_id):
    """
    Guruhning darslar ro'yxati. ?date=YYYY-MM-DD orqali filterlash mumkin.
    """
    group = Group.query.filter_by(id=group_id).first()
    if not group:
        return get_response("Group not found", None, 404), 404

    query = Lesson.query.filter_by(group_id=group_id)

    date_filter = request.args.get("date")
    if date_filter:
        from datetime import date as dt_date
        try:
            d = dt_date.fromisoformat(date_filter)
            query = query.filter_by(lesson_date=d)
        except ValueError:
            return get_response("Invalid date format. Use YYYY-MM-DD", None, 400), 400

    lessons = query.order_by(Lesson.lesson_date.asc()).all()
    result  = [Lesson.to_dict(l) for l in lessons]
    return get_response("Lessons List", result, 200), 200


@manager_bp.route("/attendance", methods=["GET"])
@role_required(["ADMIN", "MANAGER", "OPERATOR"])
def attendance_list():
    """
    Ixtiyoriy filter: ?lesson_id=X  yoki  ?student_id=Y  yoki  ?group_id=Z
    """
    lesson_id  = request.args.get("lesson_id",  type=int)
    student_id = request.args.get("student_id", type=int)
    group_id   = request.args.get("group_id",   type=int)

    query = Attendance.query

    if lesson_id:
        query = query.filter_by(lesson_id=lesson_id)
    if student_id:
        query = query.filter_by(student_id=student_id)
    if group_id:
        # Guruh darslarini topib, shu darslardagi davomatni olish
        lesson_ids = [
            l.id for l in Lesson.query.filter_by(group_id=group_id).all()
        ]
        if lesson_ids:
            query = query.filter(Attendance.lesson_id.in_(lesson_ids))
        else:
            return get_response("Attendance List", [], 200), 200

    records = query.all()

    # O'quvchi ismi ham qaytariladi
    result = []
    for a in records:
        student = Student.query.filter_by(id=a.student_id).first()
        result.append({
            **Attendance.to_dict(a),
            "student_name": student.full_name if student else None,
        })

    return get_response("Attendance List", result, 200), 200


@manager_bp.route("/attendance", methods=["POST"])
@role_required(["ADMIN", "MANAGER", "OPERATOR"])
def attendance_mark():
    """
    Bitta dars uchun bir yoki bir nechta o'quvchining davomatini belgilash.

    Body:
    {
        "lesson_id": 5,
        "records": [
            {"student_id": 1, "status": "keldi"},
            {"student_id": 2, "status": "kelmadi"},
            {"student_id": 3, "status": "kechikdi"}
        ]
    }

    Status qiymatlari: "keldi" | "kelmadi" | "kechikdi"
    """
    data      = request.get_json()
    lesson_id = data.get("lesson_id")
    records   = data.get("records")

    if not lesson_id or not records:
        return get_response("lesson_id and records are required", None, 400), 400

    lesson = Lesson.query.filter_by(id=lesson_id).first()
    if not lesson:
        return get_response("Lesson not found", None, 404), 404

    # Shu darsda o'qiydigan studentlar (faqat active enrollment)
    enrolled_ids = {
        e.student_id
        for e in Enrollment.query.filter_by(group_id=lesson.group_id, status="active").all()
    }

    saved  = []
    errors = []

    for rec in records:
        student_id = rec.get("student_id")
        status     = (rec.get("status") or "").lower()

        if status not in VALID_ATTENDANCE_STATUSES:
            errors.append({
                "student_id": student_id,
                "error": f"invalid status: '{status}'. Valid: {list(VALID_ATTENDANCE_STATUSES)}"
            })
            continue

        if student_id not in enrolled_ids:
            errors.append({
                "student_id": student_id,
                "error": "student not enrolled in this group"
            })
            continue

        # Mavjudligini tekshir — update yoki create
        existing = Attendance.query.filter_by(
            lesson_id=lesson_id, student_id=student_id
        ).first()

        if existing:
            existing.status = status
            student = Student.query.filter_by(id=student_id).first()
            saved.append({
                **Attendance.to_dict(existing),
                "student_name": student.full_name if student else None,
            })
        else:
            new_att = Attendance(
                lesson_id  = lesson_id,
                student_id = student_id,
                status     = status
            )
            db.session.add(new_att)
            db.session.flush()
            student = Student.query.filter_by(id=student_id).first()
            saved.append({
                **Attendance.to_dict(new_att),
                "student_name": student.full_name if student else None,
            })

    db.session.commit()
    return get_response("Attendance marked", {"saved": saved, "errors": errors}, 200), 200


@manager_bp.route("/attendance/<int:att_id>", methods=["PATCH"])
@role_required(["ADMIN", "MANAGER", "OPERATOR"])
def attendance_update(att_id):
    att = Attendance.query.filter_by(id=att_id).first()
    if not att:
        return get_response("Attendance record not found", None, 404), 404

    data   = request.get_json()
    status = (data.get("status") or "").lower()

    if status not in VALID_ATTENDANCE_STATUSES:
        return get_response(
            f"Invalid status. Valid: {list(VALID_ATTENDANCE_STATUSES)}", None, 400
        ), 400

    att.status = status
    db.session.commit()
    return get_response("Attendance updated", Attendance.to_dict(att), 200), 200


@manager_bp.route("/attendance/<int:att_id>", methods=["DELETE"])
@role_required(["ADMIN", "MANAGER", "OPERATOR"])
def attendance_delete(att_id):
    att = Attendance.query.filter_by(id=att_id).first()
    if not att:
        return get_response("Attendance record not found", None, 404), 404

    db.session.delete(att)
    db.session.commit()
    return get_response("Attendance record deleted", None, 200), 200


# ══════════════════════════════════════════════════════════════════════════════
# DARS RO'YXATI
# ══════════════════════════════════════════════════════════════════════════════

@manager_bp.route("/lessons", methods=["GET"])
@role_required(["ADMIN", "MANAGER"])
def lesson_list():
    """
    ?group_id=X  — majburiy emas, bo'lmasa hammasi
    """
    group_id = request.args.get("group_id", type=int)
    query    = Lesson.query
    if group_id:
        query = query.filter_by(group_id=group_id)
    lessons = query.order_by(Lesson.lesson_date.asc()).all()
    result  = [Lesson.to_dict(l) for l in lessons]
    return get_response("Lesson List", result, 200), 200


@manager_bp.route("/lessons/<int:lesson_id>", methods=["GET"])
@role_required(["ADMIN", "MANAGER"])
def lesson_get(lesson_id):
    lesson = Lesson.query.filter_by(id=lesson_id).first()
    if not lesson:
        return get_response("Lesson not found", None, 404), 404

    # Shu dars uchun davomatni ham birga qaytarish
    attendances = Attendance.query.filter_by(lesson_id=lesson_id).all()
    att_result  = []
    for a in attendances:
        student = Student.query.filter_by(id=a.student_id).first()
        att_result.append({
            **Attendance.to_dict(a),
            "student_name": student.full_name if student else None,
        })

    result = {
        **Lesson.to_dict(lesson),
        "attendance": att_result
    }
    return get_response("Lesson found", result, 200), 200


# ══════════════════════════════════════════════════════════════════════════════
# TO'LOV — boshqarish
# ══════════════════════════════════════════════════════════════════════════════

@manager_bp.route("/payments/student/<int:student_id>", methods=["GET"])
@role_required(["ADMIN", "MANAGER"])
def payments_by_student(student_id):
    student = Student.query.filter_by(id=student_id).first()
    if not student:
        return get_response("Student not found", None, 404), 404

    payments = Payment.query.filter_by(student_id=student_id)\
                            .order_by(Payment.payment_date.desc()).all()

    # Qarz holati ham
    debts = Debt.query.filter_by(student_id=student_id).all()
    total_debt      = sum(d.total_amount   for d in debts)
    total_paid      = sum(d.paid_amount    for d in debts)
    total_remaining = sum(d.remaining_debt for d in debts)

    result = {
        "student":         Student.to_dict(student),
        "payments":        [Payment.to_dict(p) for p in payments],
        "total_debt":      total_debt,
        "total_paid":      total_paid,
        "total_remaining": total_remaining,
    }
    return get_response(f"Payments for student #{student_id}", result, 200), 200


@manager_bp.route("/payments/summary", methods=["GET"])
@role_required(["ADMIN", "MANAGER"])
def payments_summary():
    """
    Jami to'lov statistikasi: for_month bo'yicha yig'indi va payment_type bo'yicha breakdown
    """
    from sqlalchemy import func

    # For_month bo'yicha jami
    rows = db.session.query(
        Payment.for_month,
        func.sum(Payment.amount).label("total")
    ).group_by(Payment.for_month).order_by(Payment.for_month).all()

    result = [{"for_month": r.for_month, "total": r.total} for r in rows]

    # Payment type bo'yicha jami breakdown
    type_rows = db.session.query(
        Payment.payment_type,
        func.sum(Payment.amount).label("total"),
        func.count(Payment.id).label("count")
    ).group_by(Payment.payment_type).all()

    type_breakdown = {r.payment_type: {"total": r.total, "count": r.count} for r in type_rows}

    # Cash alohida, online (karta+payme+click) bitta
    cash_total   = type_breakdown.get("cash", {}).get("total", 0) or 0
    cash_count   = type_breakdown.get("cash", {}).get("count", 0) or 0
    online_types = ["karta", "payme", "click"]
    online_total = sum((type_breakdown.get(t, {}).get("total", 0) or 0) for t in online_types)
    online_count = sum((type_breakdown.get(t, {}).get("count", 0) or 0) for t in online_types)

    grand_total = cash_total + online_total

    return get_response("Payments Summary", {
        "by_month": result,
        "by_type": type_breakdown,
        "cash": {"total": cash_total, "count": cash_count},
        "online": {"total": online_total, "count": online_count, "types": {t: type_breakdown.get(t, {"total": 0, "count": 0}) for t in online_types}},
        "grand_total": grand_total,
    }, 200), 200


# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD — Joriy oy qarz statistikasi
# ══════════════════════════════════════════════════════════════════════════════

@manager_bp.route("/dashboard/monthly-stats", methods=["GET"])
@role_required(["ADMIN", "MANAGER"])
def dashboard_monthly_stats():
    """
    Joriy oy uchun:
    - Kutilayotgan jami to'lov (active enrollment'lar * oylik narx)
    - Haqiqatda to'langan miqdor (joriy oy)
    - Qolgan qarz (joriy oy)
    - O'tgan oy qolgan qarzlari
    - Har bir o'quvchining joriy oy holati
    """
    import pytz
    from datetime import date
    from dateutil.relativedelta import relativedelta

    tz       = pytz.timezone('Asia/Tashkent')
    today    = date.today()
    cur_month = today.strftime('%Y-%m')
    prev_month = (today.replace(day=1) - relativedelta(months=1)).strftime('%Y-%m')

    # ── Joriy oy MonthlyDebt yig'indisi ──
    cur_mds = MonthlyDebt.query.filter_by(month_label=cur_month).all()
    cur_expected  = sum(md.amount      for md in cur_mds)
    cur_paid      = sum(md.paid_amount for md in cur_mds)
    cur_remaining = sum(md.remaining   for md in cur_mds)
    cur_unpaid_count = sum(1 for md in cur_mds if not md.is_paid)
    cur_paid_count   = sum(1 for md in cur_mds if md.is_paid)

    # ── O'tgan oy qolgan qarzlari ──
    prev_mds = MonthlyDebt.query.filter_by(month_label=prev_month).all()
    prev_remaining   = sum(md.remaining for md in prev_mds)
    prev_unpaid_students = []
    for md in prev_mds:
        if not md.is_paid:
            student = Student.query.filter_by(id=md.student_id).first()
            prev_unpaid_students.append({
                'student_id':   md.student_id,
                'student_name': student.full_name if student else '—',
                'month_label':  md.month_label,
                'amount':       md.amount,
                'paid_amount':  md.paid_amount,
                'remaining':    md.remaining,
            })

    # ── Joriy oy har bir o'quvchining holati ──
    student_details = []
    for md in cur_mds:
        student = Student.query.filter_by(id=md.student_id).first()

        # Enrollment topish — month_number ni olish uchun
        debt = Debt.query.filter_by(id=md.debt_id).first()
        enrollment = None
        if debt:
            enrollment = debt.enrollment

        student_details.append({
            'student_id':   md.student_id,
            'student_name': student.full_name if student else '—',
            'month_number': md.month_number,
            'month_label':  md.month_label,
            'amount':       md.amount,
            'paid_amount':  md.paid_amount,
            'remaining':    md.remaining,
            'is_paid':      md.is_paid,
        })

    return get_response("Monthly Stats", {
        "current_month": cur_month,
        "prev_month":    prev_month,
        "current": {
            "expected":      cur_expected,
            "paid":          cur_paid,
            "remaining":     cur_remaining,
            "paid_count":    cur_paid_count,
            "unpaid_count":  cur_unpaid_count,
            "students":      student_details,
        },
        "previous": {
            "remaining":         prev_remaining,
            "unpaid_students":   prev_unpaid_students,
        },
    }, 200), 200


@manager_bp.route("/enrollments/with-month", methods=["GET"])
@role_required(["ADMIN", "MANAGER", "OPERATOR"])
def enrollments_with_month():
    """
    Barcha active enrollment'lar, har birida current_month_number ko'rsatiladi.
    Frontend'dagi 'Ro'yxatga olinganlar' jadvalida N-oyda o'qiyapti ko'rsatish uchun.
    """
    enrollments = Enrollment.query.filter_by(status="active").all()
    result = []
    for e in enrollments:
        base = Enrollment.to_dict(e)
        base['student_name'] = e.student.full_name if e.student else '—'
        base['group_name']   = e.group.name if e.group else '—'
        base['course_name']  = e.group.course.name if (e.group and e.group.course) else '—'
        base['duration_months'] = e.group.course.duration_months if (e.group and e.group.course) else None
        result.append(base)
    return get_response("Enrollments with month info", result, 200), 200
