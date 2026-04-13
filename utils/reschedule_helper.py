"""
Darsni bekor qilish va keyingi bo'sh ish kuniga surish logikasi.

Qoidalar:
  1. Bekor qilinadigan sana uchun Lesson topiladi.
  2. O'sha Lesson → is_cancelled = True, cancel_reason saqlandi.
  3. Guruhning schedule_type (odd/even) ga QARAMASDAN,
     keyingi mos bo'sh kun izlanadi quyidagicha:
       - cancel_date + 1 kundan boshlab oldinga qarab yuriladi
       - Yakshanba (weekday=6) o'tkazib yuboriladi
       - Shu sana uchun shu guruhda Lesson mavjud bo'lmagan birinchi kun tanlanadi
       - Guruhning end_date dan o'tib ketmasligi kerak
  4. Topilgan sana uchun yangi Lesson yaratiladi (is_rescheduled=True,
     original_date = bekor qilingan sana).
  5. Agar mos kun topilmasa (end_date tugab qolsa) → xato qaytariladi.
"""

from datetime    import timedelta
from models      import db
from models.lesson import Lesson


def cancel_and_reschedule(group, cancel_date, reason: str = None):
    """
    group       — Group ORM obyekti
    cancel_date — datetime.date, bekor qilinadigan kun
    reason      — sabab matni (ixtiyoriy)

    Qaytaradi: dict {
        "cancelled_lesson": Lesson.to_dict(...),
        "rescheduled_lesson": Lesson.to_dict(...) | None,
        "warning": str | None
    }
    """

    # ── 1. Bekor qilinadigan darsni topish ───────────────────────────────────
    lesson = Lesson.query.filter_by(
        group_id    = group.id,
        lesson_date = cancel_date,
        is_cancelled = False
    ).first()

    if not lesson:
        return None, f"Guruh #{group.id} uchun {cancel_date} sanasida faol dars topilmadi"

    # ── 2. Bekor qilish ──────────────────────────────────────────────────────
    lesson.is_cancelled  = True
    lesson.cancel_reason = reason

    # ── 3. Keyingi bo'sh kunni izlash ────────────────────────────────────────
    # Shu guruhda mavjud bo'lgan barcha lesson sanalarini bir marta yuklash
    existing_dates = {
        row.lesson_date
        for row in Lesson.query.filter_by(group_id=group.id).all()
    }

    new_date  = cancel_date + timedelta(days=1)
    end_date  = group.end_date
    warning   = None
    new_lesson = None

    while new_date <= end_date:
        # Yakshanba (6) ni o'tkazib yubor
        if new_date.weekday() == 6:
            new_date += timedelta(days=1)
            continue

        # Shu sana uchun allaqachon dars bormi?
        if new_date not in existing_dates:
            new_lesson = Lesson(
                group_id       = group.id,
                lesson_date    = new_date,
                lesson_time    = group.lesson_time,
                is_rescheduled = True,
                original_date  = cancel_date,
            )
            db.session.add(new_lesson)
            break

        new_date += timedelta(days=1)
    else:
        warning = (
            f"{cancel_date} sanasidagi dars bekor qilindi, lekin "
            f"end_date ({end_date}) dan oldin bo'sh kun topilmadi. "
            f"Dars surilmadi — qo'lda qo'shish tavsiya etiladi."
        )

    db.session.commit()

    return {
        "cancelled_lesson":    Lesson.to_dict(lesson),
        "rescheduled_lesson":  Lesson.to_dict(new_lesson) if new_lesson else None,
        "warning":             warning,
    }, None
