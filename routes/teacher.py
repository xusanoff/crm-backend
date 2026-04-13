"""
O'qituvchilar boshqaruvi va oylik hisob-kitob.

Endpoints:
  GET    /api/teachers                        — O'qituvchilar ro'yxati
  POST   /api/teachers                        — Yangi o'qituvchi qo'shish
  GET    /api/teachers/<id>                   — O'qituvchi ma'lumoti
  PATCH  /api/teachers/<id>                   — Yangilash
  DELETE /api/teachers/<id>                   — O'chirish

  GET    /api/teachers/<id>/salary-report     — O'qituvchining barcha oy hisobotlari
  POST   /api/teachers/salary-calculate       — Guruh uchun oylik hisoblash

  GET    /api/groups/<id>/salary-report       — Guruh bo'yicha oylik hisobot
"""

from flask              import Blueprint, request
from models             import db
from models.teacher     import Teacher, TeacherSalary
from models.group       import Group
from models.payment     import Payment
from models.ernollmert  import Enrollment
from utils.utils        import get_response
from utils.decorators   import role_required

teacher_bp = Blueprint("teacher", __name__, url_prefix="/api/teachers")
group_salary_bp = Blueprint("group_salary", __name__, url_prefix="/api/groups")


# ══════════════════════════════════════════════════════════════════════════════
# O'QITUVCHI CRUD
# ══════════════════════════════════════════════════════════════════════════════

@teacher_bp.route("", methods=["GET"])
@role_required(["ADMIN", "MANAGER"])
def teacher_list():
    teachers = Teacher.query.order_by(Teacher.full_name).all()
    return get_response("Teacher List", [Teacher.to_dict(t) for t in teachers], 200), 200


@teacher_bp.route("", methods=["POST"])
@role_required(["ADMIN"])
def teacher_create():
    """
    Body:
    {
        "full_name":      "Alisher Karimov",
        "phone_number":   "+998901234567",
        "salary_percent": 20
    }
    """
    data           = request.get_json()
    full_name      = data.get("full_name")
    phone_number   = data.get("phone_number")
    salary_percent = data.get("salary_percent")

    if not full_name or not phone_number or salary_percent is None:
        return get_response("full_name, phone_number va salary_percent majburiy", None, 400), 400

    try:
        salary_percent = float(salary_percent)
        if not (0 < salary_percent <= 100):
            raise ValueError
    except (ValueError, TypeError):
        return get_response("salary_percent 0 dan 100 gacha bo'lishi kerak", None, 400), 400

    if Teacher.query.filter_by(phone_number=phone_number).first():
        return get_response("Bu telefon raqam allaqachon mavjud", None, 400), 400

    teacher = Teacher(
        full_name      = full_name,
        phone_number   = phone_number,
        salary_percent = salary_percent,
    )
    db.session.add(teacher)
    db.session.commit()
    return get_response("O'qituvchi muvaffaqiyatli qo'shildi", Teacher.to_dict(teacher), 200), 200


@teacher_bp.route("/<int:teacher_id>", methods=["GET"])
@role_required(["ADMIN", "MANAGER"])
def teacher_get(teacher_id):
    teacher = Teacher.query.filter_by(id=teacher_id).first()
    if not teacher:
        return get_response("O'qituvchi topilmadi", None, 404), 404
    return get_response("O'qituvchi topildi", Teacher.to_dict(teacher), 200), 200


@teacher_bp.route("/<int:teacher_id>", methods=["PATCH"])
@role_required(["ADMIN"])
def teacher_update(teacher_id):
    teacher = Teacher.query.filter_by(id=teacher_id).first()
    if not teacher:
        return get_response("O'qituvchi topilmadi", None, 404), 404

    data = request.get_json()
    if data.get("full_name"):
        teacher.full_name = data["full_name"]
    if data.get("phone_number"):
        existing = Teacher.query.filter_by(phone_number=data["phone_number"]).first()
        if existing and existing.id != teacher_id:
            return get_response("Bu telefon raqam boshqa o'qituvchida mavjud", None, 400), 400
        teacher.phone_number = data["phone_number"]
    if data.get("salary_percent") is not None:
        try:
            sp = float(data["salary_percent"])
            if not (0 < sp <= 100):
                raise ValueError
            teacher.salary_percent = sp
        except (ValueError, TypeError):
            return get_response("salary_percent 0 dan 100 gacha bo'lishi kerak", None, 400), 400

    db.session.commit()
    return get_response("O'qituvchi yangilandi", Teacher.to_dict(teacher), 200), 200


@teacher_bp.route("/<int:teacher_id>", methods=["DELETE"])
@role_required(["ADMIN"])
def teacher_delete(teacher_id):
    teacher = Teacher.query.filter_by(id=teacher_id).first()
    if not teacher:
        return get_response("O'qituvchi topilmadi", None, 404), 404

    # Guruhlarni teacher_id dan tozalash (teacher_name da saqlangan bo'lsa qoladi)
    groups = Group.query.filter_by(teacher_id=teacher_id).all()
    for g in groups:
        if not g.teacher_name and teacher:
            g.teacher_name = teacher.full_name
        g.teacher_id = None

    db.session.delete(teacher)
    db.session.commit()
    return get_response("O'qituvchi o'chirildi", None, 200), 200


# ══════════════════════════════════════════════════════════════════════════════
# OYLIK HISOB-KITOB
# ══════════════════════════════════════════════════════════════════════════════

def _calculate_salary_for_group(group: Group, for_month: str) -> dict:
    """
    Berilgan guruh va oy uchun:
      - O'sha oyda shu guruh o'quvchilaridan yig'ilgan jami to'lovni hisoblaydi
      - O'qituvchi oyligini = jami * foiz / 100
      - Sof foydani = jami - o'qituvchi oyligi
    for_month format: "2025-04"
    """
    if not group.teacher_id and not group.teacher:
        return None

    # Guruh o'quvchilari (active enrollment)
    enrollments = Enrollment.query.filter_by(group_id=group.id, status='active').all()
    student_ids = [e.student_id for e in enrollments]

    if not student_ids:
        total_payments = 0.0
    else:
        # O'sha oyda shu o'quvchilardan kelgan to'lovlar
        payments = Payment.query.filter(
            Payment.student_id.in_(student_ids),
            Payment.for_month == for_month
        ).all()
        total_payments = sum(p.amount for p in payments)

    teacher = group.teacher
    if not teacher:
        return None

    teacher_salary = round(total_payments * teacher.salary_percent / 100, 2)
    net_profit     = round(total_payments - teacher_salary, 2)

    return {
        'group_id':         group.id,
        'group_name':       group.name,
        'teacher_id':       teacher.id,
        'teacher_name':     teacher.full_name,
        'teacher_phone':    teacher.phone_number,
        'salary_percent':   teacher.salary_percent,
        'for_month':        for_month,
        'total_payments':   total_payments,
        'teacher_salary':   teacher_salary,
        'net_profit':       net_profit,
    }


@teacher_bp.route("/salary-calculate", methods=["POST"])
@role_required(["ADMIN", "MANAGER"])
def salary_calculate():
    """
    Guruh uchun oylik hisob-kitob qilish va saqlash.

    Body:
    {
        "group_id":  1,
        "for_month": "2025-04"
    }

    Javob:
    {
        "total_payments":  5000000,   -- Guruhdan yig'ilgan jami to'lov
        "teacher_salary":  1000000,   -- O'qituvchi oyligi (20%)
        "net_profit":      4000000    -- Sof foyda
    }
    """
    data      = request.get_json()
    group_id  = data.get("group_id")
    for_month = data.get("for_month")  # "2025-04"

    if not group_id or not for_month:
        return get_response("group_id va for_month majburiy", None, 400), 400

    group = Group.query.filter_by(id=group_id).first()
    if not group:
        return get_response("Guruh topilmadi", None, 404), 404

    if not group.teacher_id:
        return get_response(
            "Bu guruhga o'qituvchi biriktirilmagan. Avval guruhga o'qituvchi tanlang.",
            None, 400
        ), 400

    result = _calculate_salary_for_group(group, for_month)
    if not result:
        return get_response("Hisoblashda xatolik yuz berdi", None, 500), 500

    # Avvalgi yozuvni o'chirish (qayta hisoblash uchun)
    existing = TeacherSalary.query.filter_by(
        group_id=group_id,
        for_month=for_month
    ).first()
    if existing:
        db.session.delete(existing)
        db.session.flush()

    # Yangi yozuv saqlash
    ts = TeacherSalary(
        teacher_id     = result['teacher_id'],
        group_id       = group_id,
        for_month      = for_month,
        total_payments = result['total_payments'],
        teacher_salary = result['teacher_salary'],
        net_profit     = result['net_profit'],
    )
    db.session.add(ts)
    db.session.commit()

    return get_response("Oylik hisoblandi va saqlandi", {
        **result,
        'saved_id': ts.id,
    }, 200), 200


@teacher_bp.route("/<int:teacher_id>/salary-report", methods=["GET"])
@role_required(["ADMIN", "MANAGER"])
def teacher_salary_report(teacher_id):
    """
    O'qituvchining barcha oy va guruh bo'yicha hisobotlari.
    Query param: ?for_month=2025-04  (ixtiyoriy, filter uchun)
    """
    teacher = Teacher.query.filter_by(id=teacher_id).first()
    if not teacher:
        return get_response("O'qituvchi topilmadi", None, 404), 404

    q = TeacherSalary.query.filter_by(teacher_id=teacher_id)
    for_month = request.args.get("for_month")
    if for_month:
        q = q.filter_by(for_month=for_month)

    records = q.order_by(TeacherSalary.for_month.desc()).all()

    # Jami summalar
    total_earned = sum(r.teacher_salary for r in records)

    return get_response("O'qituvchi oylik hisoboti", {
        'teacher':       Teacher.to_dict(teacher),
        'total_earned':  total_earned,
        'records':       [TeacherSalary.to_dict(r) for r in records],
    }, 200), 200


# ══════════════════════════════════════════════════════════════════════════════
# GURUH BO'YICHA OYLIK HISOBOT
# ══════════════════════════════════════════════════════════════════════════════

@group_salary_bp.route("/<int:group_id>/salary-report", methods=["GET"])
@role_required(["ADMIN", "MANAGER"])
def group_salary_report(group_id):
    """
    Guruh bo'yicha barcha oylik hisobotlar.

    Javob har bir yozuvda:
      - total_payments  : O'quvchilardan yig'ilgan jami to'lov
      - teacher_salary  : O'qituvchi oyligi
      - net_profit      : Sof foyda (jami - o'qituvchi oyligi)
    """
    group = Group.query.filter_by(id=group_id).first()
    if not group:
        return get_response("Guruh topilmadi", None, 404), 404

    records = TeacherSalary.query.filter_by(group_id=group_id)\
                                  .order_by(TeacherSalary.for_month.desc()).all()

    return get_response("Guruh oylik hisoboti", {
        'group':   {
            'id':           group.id,
            'name':         group.name,
            'teacher_id':   group.teacher_id,
            'teacher_name': group.teacher.full_name if group.teacher else group.teacher_name,
        },
        'records': [TeacherSalary.to_dict(r) for r in records],
    }, 200), 200


@group_salary_bp.route("/<int:group_id>/salary-live", methods=["GET"])
@role_required(["ADMIN", "MANAGER"])
def group_salary_live(group_id):
    """
    Guruh uchun joriy oy yoki berilgan oy bo'yicha JONLI hisoblash
    (bazaga saqlamasdan, to'g'ridan-to'g'ri to'lovlardan hisoblab beradi).

    Query param: ?for_month=2025-04  (majburiy)

    Javob:
    {
        "total_payments":  5000000,
        "teacher_salary":  1000000,
        "net_profit":      4000000,
        "student_count":   12,
        "paid_students":   8
    }
    """
    group = Group.query.filter_by(id=group_id).first()
    if not group:
        return get_response("Guruh topilmadi", None, 404), 404

    for_month = request.args.get("for_month")
    if not for_month:
        from datetime import datetime
        for_month = datetime.now().strftime("%Y-%m")

    if not group.teacher_id:
        return get_response(
            "Bu guruhga o'qituvchi biriktirilmagan",
            None, 400
        ), 400

    # Active o'quvchilar
    enrollments  = Enrollment.query.filter_by(group_id=group_id, status='active').all()
    student_ids  = [e.student_id for e in enrollments]
    student_count = len(student_ids)

    if not student_ids:
        total_payments = 0.0
        paid_students  = 0
    else:
        payments = Payment.query.filter(
            Payment.student_id.in_(student_ids),
            Payment.for_month == for_month
        ).all()
        total_payments = sum(p.amount for p in payments)
        paid_students  = len(set(p.student_id for p in payments))

    teacher        = group.teacher
    teacher_salary = round(total_payments * teacher.salary_percent / 100, 2)
    net_profit     = round(total_payments - teacher_salary, 2)

    return get_response("Jonli oylik hisobot", {
        'group_id':       group.id,
        'group_name':     group.name,
        'for_month':      for_month,
        'teacher_name':   teacher.full_name,
        'salary_percent': teacher.salary_percent,
        'student_count':  student_count,
        'paid_students':  paid_students,
        'total_payments': total_payments,   # Jami yig'ilgan to'lov
        'teacher_salary': teacher_salary,   # O'qituvchi oyligi
        'net_profit':     net_profit,        # Sof foyda
    }, 200), 200
