from flask              import Blueprint, request
from flask_jwt_extended import get_jwt_identity
from datetime           import datetime
from models             import db
from models.user        import User
from models.lead        import Lead
from models.student     import Student
from models.ernollmert  import Enrollment
from models.group       import Group
from models.cource      import Course
from models.payment     import Payment, Debt, MonthlyDebt
from utils.utils        import get_response
from utils.decorators   import role_required

operator_bp = Blueprint("operator", __name__, url_prefix="/api/operator")

VALID_LEAD_STATUSES       = {"yangi", "boglandi", "qiziqdi", "rad", "talabaga_aylandi"}
VALID_ENROLLMENT_STATUSES = {"active", "finished", "dropped"}
VALID_PAYMENT_TYPES       = {"cash", "click", "payme", "karta"}


# ══════════════════════════════════════════════════════════════════════════════
# LEAD CRUD
# ══════════════════════════════════════════════════════════════════════════════

@operator_bp.route("/leads", methods=["GET"])
@role_required(["ADMIN", "OPERATOR"])
def lead_list():
    user_id = int(get_jwt_identity())
    user    = User.query.filter_by(id=user_id).first()

    if user.role == "ADMIN":
        leads = Lead.query.order_by(Lead.created_at.desc()).all()
    else:
        leads = Lead.query.filter_by(created_by=user_id).order_by(Lead.created_at.desc()).all()

    result = [Lead.to_dict(l) for l in leads]
    return get_response("Lead List", result, 200), 200


@operator_bp.route("/leads", methods=["POST"])
@role_required(["ADMIN", "OPERATOR"])
def lead_create():
    user_id      = int(get_jwt_identity())
    data         = request.get_json()
    full_name    = data.get("full_name")
    phone_number = data.get("phone_number")

    if not full_name or not phone_number:
        return get_response("full_name and phone_number are required", None, 400), 400

    new_lead = Lead(
        full_name    = full_name,
        phone_number = phone_number,
        source       = data.get("source"),
        comment      = data.get("comment"),
        status       = "yangi",
        created_by   = user_id,
        course_id    = data.get("course_id")
    )
    db.session.add(new_lead)
    db.session.commit()
    return get_response("Lead successfully created", Lead.to_dict(new_lead), 200), 200


@operator_bp.route("/leads/<int:lead_id>", methods=["GET"])
@role_required(["ADMIN", "OPERATOR"])
def lead_get(lead_id):
    user_id = int(get_jwt_identity())
    user    = User.query.filter_by(id=user_id).first()
    lead    = Lead.query.filter_by(id=lead_id).first()

    if not lead:
        return get_response("Lead not found", None, 404), 404
    if user.role == "OPERATOR" and lead.created_by != user_id:
        return get_response("Permission denied", None, 403), 403

    return get_response("Lead found", Lead.to_dict(lead), 200), 200


@operator_bp.route("/leads/<int:lead_id>", methods=["PATCH"])
@role_required(["ADMIN", "OPERATOR"])
def lead_update(lead_id):
    user_id = int(get_jwt_identity())
    user    = User.query.filter_by(id=user_id).first()
    lead    = Lead.query.filter_by(id=lead_id).first()

    if not lead:
        return get_response("Lead not found", None, 404), 404
    if user.role == "OPERATOR" and lead.created_by != user_id:
        return get_response("Permission denied", None, 403), 403

    data = request.get_json()
    if data.get("full_name"):
        lead.full_name = data["full_name"]
    if data.get("phone_number"):
        lead.phone_number = data["phone_number"]
    if data.get("source") is not None:
        lead.source = data["source"]
    if data.get("comment") is not None:
        lead.comment = data["comment"]
    if "course_id" in data:
        lead.course_id = data["course_id"]
    if data.get("status"):
        status = data["status"].lower()
        if status not in VALID_LEAD_STATUSES:
            return get_response(f"Invalid status. Valid: {VALID_LEAD_STATUSES}", None, 400), 400
        lead.status = status

    db.session.commit()
    return get_response("Lead successfully updated", Lead.to_dict(lead), 200), 200


@operator_bp.route("/leads/<int:lead_id>", methods=["DELETE"])
@role_required(["ADMIN", "OPERATOR"])
def lead_delete(lead_id):
    user_id = int(get_jwt_identity())
    user    = User.query.filter_by(id=user_id).first()
    lead    = Lead.query.filter_by(id=lead_id).first()

    if not lead:
        return get_response("Lead not found", None, 404), 404
    if user.role == "OPERATOR" and lead.created_by != user_id:
        return get_response("Permission denied", None, 403), 403

    db.session.delete(lead)
    db.session.commit()
    return get_response("Lead successfully deleted", None, 200), 200


@operator_bp.route("/leads/stats", methods=["GET"])
@role_required(["ADMIN", "OPERATOR"])
def lead_stats():
    from datetime import timedelta
    import pytz

    user_id = int(get_jwt_identity())
    user    = User.query.filter_by(id=user_id).first()
    tz      = pytz.timezone('Asia/Tashkent')
    now     = datetime.now(tz)

    # Base queryset
    base_q = Lead.query if user.role == "ADMIN" else Lead.query.filter_by(created_by=user_id)

    # Kunlik: bugungi kun boshidan
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_leads = base_q.filter(Lead.created_at >= today_start).order_by(Lead.created_at.desc()).all()

    # Haftalik: joriy haftaning dushanbasidan
    week_start = today_start - timedelta(days=now.weekday())
    week_leads = base_q.filter(Lead.created_at >= week_start).order_by(Lead.created_at.desc()).all()

    # Oylik: joriy oyning 1-sanasidan
    month_start = today_start.replace(day=1)
    month_leads = base_q.filter(Lead.created_at >= month_start).order_by(Lead.created_at.desc()).all()

    def summarize(leads_list):
        by_status = {}
        for l in leads_list:
            by_status[l.status] = by_status.get(l.status, 0) + 1
        by_course = {}
        for l in leads_list:
            cname = l.course.name if l.course else "Belgilanmagan"
            by_course[cname] = by_course.get(cname, 0) + 1
        return {
            "count": len(leads_list),
            "by_status": by_status,
            "by_course": by_course,
            "leads": [Lead.to_dict(l) for l in leads_list]
        }

    return get_response("Lead stats", {
        "daily":   summarize(today_leads),
        "weekly":  summarize(week_leads),
        "monthly": summarize(month_leads),
    }, 200), 200


# ══════════════════════════════════════════════════════════════════════════════
# STUDENT CRUD
# ══════════════════════════════════════════════════════════════════════════════

@operator_bp.route("/students", methods=["GET"])
@role_required(["ADMIN", "OPERATOR", "MANAGER"])
def student_list():
    students = Student.query.order_by(Student.created_at.desc()).all()
    result   = [Student.to_dict(s) for s in students]
    return get_response("Student List", result, 200), 200


@operator_bp.route("/students", methods=["POST"])
@role_required(["ADMIN", "OPERATOR"])
def student_create():
    user_id      = int(get_jwt_identity())
    data         = request.get_json()
    full_name    = data.get("full_name")

    if not full_name:
        return get_response("full_name is required", None, 400), 400

    phone_number = data.get("phone_number")
    if phone_number and Student.query.filter_by(phone_number=phone_number).first():
        return get_response("Phone number already registered", None, 400), 400

    new_student = Student(
        full_name    = full_name,
        phone_number = phone_number,
        comment      = data.get("comment"),
        source_id    = data.get("source_id"),
        created_by   = user_id
    )
    db.session.add(new_student)
    db.session.commit()
    return get_response("Student successfully created", Student.to_dict(new_student), 200), 200


@operator_bp.route("/students/<int:student_id>", methods=["GET"])
@role_required(["ADMIN", "OPERATOR", "MANAGER"])
def student_get(student_id):
    student = Student.query.filter_by(id=student_id).first()
    if not student:
        return get_response("Student not found", None, 404), 404
    return get_response("Student found", Student.to_dict(student), 200), 200


@operator_bp.route("/students/<int:student_id>", methods=["PATCH"])
@role_required(["ADMIN", "OPERATOR"])
def student_update(student_id):
    student = Student.query.filter_by(id=student_id).first()
    if not student:
        return get_response("Student not found", None, 404), 404

    data = request.get_json()
    if data.get("full_name"):
        student.full_name = data["full_name"]
    if data.get("phone_number"):
        existing = Student.query.filter_by(phone_number=data["phone_number"]).first()
        if existing and existing.id != student_id:
            return get_response("Phone number already registered", None, 400), 400
        student.phone_number = data["phone_number"]
    if data.get("comment") is not None:
        student.comment = data["comment"]

    db.session.commit()
    return get_response("Student successfully updated", Student.to_dict(student), 200), 200


@operator_bp.route("/students/<int:student_id>", methods=["DELETE"])
@role_required(["ADMIN"])
def student_delete(student_id):
    student = Student.query.filter_by(id=student_id).first()
    if not student:
        return get_response("Student not found", None, 404), 404

    db.session.delete(student)
    db.session.commit()
    return get_response("Student successfully deleted", None, 200), 200


# ══════════════════════════════════════════════════════════════════════════════
# ENROLLMENT — guruhga o'quvchi qo'shish + avtomatik qarz yaratish
# ══════════════════════════════════════════════════════════════════════════════

@operator_bp.route("/enrollments", methods=["GET"])
@role_required(["ADMIN", "OPERATOR", "MANAGER"])
def enrollment_list():
    enrollments = Enrollment.query.all()
    result      = [Enrollment.to_dict(e) for e in enrollments]
    return get_response("Enrollment List", result, 200), 200


@operator_bp.route("/enrollments", methods=["POST"])
@role_required(["ADMIN", "OPERATOR"])
def enrollment_create():
    """
    O'quvchini guruhga qo'shganda avtomatik qarz yaratiladi.
    Qarz = kurs.price * kurs.duration_months

    Body: { "student_id": 1, "group_id": 2 }
    """
    data       = request.get_json()
    student_id = data.get("student_id")
    group_id   = data.get("group_id")

    if not student_id or not group_id:
        return get_response("student_id and group_id are required", None, 400), 400

    student = Student.query.filter_by(id=student_id).first()
    if not student:
        return get_response("Student not found", None, 404), 404

    group = Group.query.filter_by(id=group_id).first()
    if not group:
        return get_response("Group not found", None, 404), 404

    existing = Enrollment.query.filter_by(student_id=student_id, group_id=group_id).first()
    if existing:
        return get_response("Student already enrolled in this group", None, 400), 400

    course = Course.query.filter_by(id=group.course_id).first()
    if not course:
        return get_response("Course not found for this group", None, 404), 404

    # Enrollment yaratish
    new_enrollment = Enrollment(
        student_id  = student_id,
        group_id    = group_id,
        status      = "active",
        enrolled_at = datetime.now().date()
    )
    db.session.add(new_enrollment)
    db.session.flush()  # ID olish uchun

    # Avtomatik qarz yaratish: jami narx = price * duration_months
    total_debt = course.total_price
    new_debt = Debt(
        student_id    = student_id,
        enrollment_id = new_enrollment.id,
        total_amount  = total_debt
    )
    db.session.add(new_debt)
    db.session.flush()  # debt.id olish uchun

    # Har oy uchun alohida MonthlyDebt yaratish
    # enrolled_at oyidan boshlab, duration_months ta yozuv
    from dateutil.relativedelta import relativedelta
    start_date    = new_enrollment.enrolled_at
    monthly_price = course.price
    monthly_debts_created = []
    for i in range(course.duration_months):
        month_date  = start_date + relativedelta(months=i)
        month_label = month_date.strftime('%Y-%m')
        md = MonthlyDebt(
            debt_id      = new_debt.id,
            student_id   = student_id,
            month_label  = month_label,
            month_number = i + 1,
            amount       = monthly_price
        )
        db.session.add(md)
        monthly_debts_created.append({'month_label': month_label, 'month_number': i+1, 'amount': monthly_price})

    db.session.commit()

    result = {
        **Enrollment.to_dict(new_enrollment),
        "debt_created": {
            "total_amount":   total_debt,
            "paid_amount":    0.0,
            "remaining_debt": total_debt,
            "monthly_debts":  monthly_debts_created,
            "info": (
                f"{student.full_name} '{course.name}' kursiga yozildi. "
                f"Jami qarz: {total_debt:,.0f} so'm "
                f"({course.duration_months} oy × {monthly_price:,.0f} so'm/oy)"
            )
        }
    }

    return get_response("Student successfully enrolled", result, 200), 200


@operator_bp.route("/enrollments/<int:enrollment_id>", methods=["PATCH"])
@role_required(["ADMIN", "OPERATOR", "MANAGER"])
def enrollment_update(enrollment_id):
    enrollment = Enrollment.query.filter_by(id=enrollment_id).first()
    if not enrollment:
        return get_response("Enrollment not found", None, 404), 404

    data   = request.get_json()
    status = data.get("status", "").lower()

    if status not in VALID_ENROLLMENT_STATUSES:
        return get_response(f"Invalid status. Valid: {VALID_ENROLLMENT_STATUSES}", None, 400), 400

    enrollment.status = status
    db.session.commit()
    return get_response("Enrollment status updated", Enrollment.to_dict(enrollment), 200), 200


@operator_bp.route("/enrollments/<int:enrollment_id>", methods=["DELETE"])
@role_required(["ADMIN"])
def enrollment_delete(enrollment_id):
    enrollment = Enrollment.query.filter_by(id=enrollment_id).first()
    if not enrollment:
        return get_response("Enrollment not found", None, 404), 404

    # Bog'liq qarzni ham o'chirish
    debt = Debt.query.filter_by(enrollment_id=enrollment_id).first()
    if debt:
        db.session.delete(debt)

    db.session.delete(enrollment)
    db.session.commit()
    return get_response("Enrollment successfully deleted", None, 200), 200


# ══════════════════════════════════════════════════════════════════════════════
# PAYMENT — to'lov qabul qilish: qarzdan ayirib ketiladi
# ══════════════════════════════════════════════════════════════════════════════

@operator_bp.route("/payments", methods=["GET"])
@role_required(["ADMIN", "OPERATOR", "MANAGER"])
def payment_list():
    user_id = int(get_jwt_identity())
    user    = User.query.filter_by(id=user_id).first()

    if user.role == "OPERATOR":
        payments = Payment.query.filter_by(created_by=user_id).order_by(Payment.payment_date.desc()).all()
    else:
        payments = Payment.query.order_by(Payment.payment_date.desc()).all()

    result = [Payment.to_dict(p) for p in payments]
    return get_response("Payment List", result, 200), 200


@operator_bp.route("/payments", methods=["POST"])
@role_required(["ADMIN", "OPERATOR", "MANAGER"])
def payment_create():
    """
    To'lov qabul qilinganda:
    1. Payment yozuvi yaratiladi
    2. O'quvchining Debt.paid_amount ga qo'shiladi (qarz kamayadi)

    Body: {
        "student_id": 1,
        "payment_type": "cash",
        "for_month": "2025-02",
        "amount": 1200000,
        "comment": "..."
    }
    """
    user_id      = int(get_jwt_identity())
    data         = request.get_json()
    student_id   = data.get("student_id")
    payment_type = data.get("payment_type", "").lower()
    for_month    = data.get("for_month")
    amount       = data.get("amount")

    if not student_id or not payment_type or not for_month or amount is None:
        return get_response(
            "student_id, payment_type, for_month, amount are required", None, 400
        ), 400

    if payment_type not in VALID_PAYMENT_TYPES:
        return get_response(f"Invalid payment_type. Valid: {VALID_PAYMENT_TYPES}", None, 400), 400

    student = Student.query.filter_by(id=student_id).first()
    if not student:
        return get_response("Student not found", None, 404), 404

    amount = float(amount)

    # O'quvchining aktiv qarzini topish
    # Eng avval active enrollment ga tegishli qarzni olish
    active_enrollment = Enrollment.query.filter_by(
        student_id=student_id, status="active"
    ).first()

    debt = None
    if active_enrollment:
        debt = Debt.query.filter_by(enrollment_id=active_enrollment.id).first()

    # Payment yozuvi yaratish
    new_payment = Payment(
        student_id   = student_id,
        payment_type = payment_type,
        for_month    = for_month,
        amount       = amount,
        comment      = data.get("comment"),
        created_by   = user_id,
        debt_id      = debt.id if debt else None
    )
    db.session.add(new_payment)

    # Umumiy qarzdan ayirish
    if debt:
        debt.paid_amount += amount
        db.session.add(debt)

        # Oylik qarzdan ham ayirish (for_month bo'yicha)
        monthly_debt = MonthlyDebt.query.filter_by(
            debt_id     = debt.id,
            month_label = for_month
        ).first()
        if monthly_debt:
            monthly_debt.paid_amount = min(
                monthly_debt.amount,
                monthly_debt.paid_amount + amount
            )
            db.session.add(monthly_debt)

    db.session.commit()

    result = {
        **Payment.to_dict(new_payment),
        "debt_status": Debt.to_dict(debt) if debt else None
    }

    return get_response("Payment successfully recorded", result, 200), 200


@operator_bp.route("/payments/<int:payment_id>", methods=["GET"])
@role_required(["ADMIN", "OPERATOR", "MANAGER"])
def payment_get(payment_id):
    user_id = int(get_jwt_identity())
    user    = User.query.filter_by(id=user_id).first()
    payment = Payment.query.filter_by(id=payment_id).first()

    if not payment:
        return get_response("Payment not found", None, 404), 404
    if user.role == "OPERATOR" and payment.created_by != user_id:
        return get_response("Permission denied", None, 403), 403

    return get_response("Payment found", Payment.to_dict(payment), 200), 200


@operator_bp.route("/payments/<int:payment_id>", methods=["DELETE"])
@role_required(["ADMIN", "MANAGER"])
def payment_delete(payment_id):
    payment = Payment.query.filter_by(id=payment_id).first()
    if not payment:
        return get_response("Payment not found", None, 404), 404

    # Qarzni qaytarish (to'lov o'chirilsa)
    if payment.debt_id:
        debt = Debt.query.filter_by(id=payment.debt_id).first()
        if debt:
            debt.paid_amount = max(0.0, debt.paid_amount - payment.amount)
            db.session.add(debt)

            # Oylik qarzni ham qaytarish
            monthly_debt = MonthlyDebt.query.filter_by(
                debt_id     = payment.debt_id,
                month_label = payment.for_month
            ).first()
            if monthly_debt:
                monthly_debt.paid_amount = max(0.0, monthly_debt.paid_amount - payment.amount)
                db.session.add(monthly_debt)

    db.session.delete(payment)
    db.session.commit()
    return get_response("Payment successfully deleted", None, 200), 200


# ══════════════════════════════════════════════════════════════════════════════
# QARZ — o'quvchining qarz holatini ko'rish
# ══════════════════════════════════════════════════════════════════════════════

@operator_bp.route("/debts/student/<int:student_id>", methods=["GET"])
@role_required(["ADMIN", "OPERATOR", "MANAGER"])
def student_debt(student_id):
    """O'quvchining barcha qarzlari va to'lov holati"""
    student = Student.query.filter_by(id=student_id).first()
    if not student:
        return get_response("Student not found", None, 404), 404

    debts  = Debt.query.filter_by(student_id=student_id).all()
    result = [Debt.to_dict(d) for d in debts]

    total_debt      = sum(d.total_amount   for d in debts)
    total_paid      = sum(d.paid_amount    for d in debts)
    total_remaining = sum(d.remaining_debt for d in debts)

    return get_response("Student Debt Info", {
        "student_id":      student_id,
        "student_name":    student.full_name,
        "debts":           result,
        "total_debt":      total_debt,
        "total_paid":      total_paid,
        "total_remaining": total_remaining,
    }, 200), 200
