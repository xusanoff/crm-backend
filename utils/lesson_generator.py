"""
Guruh schedule_type asosida dars kunlarini avtomatik hisoblash.

  odd  (toq kunlar)  → Dushanba(0), Chorshanba(2), Juma(4)
  even (juft kunlar) → Seshanba(1), Payshanba(3), Shanba(5)

Yakshanba (weekday=6) hech qachon hisoblanmaydi.

Endi end_date guruhdan emas, kurs duration_months dan hisoblanadi.
"""

from datetime import timedelta
from dateutil.relativedelta import relativedelta
from models import db
from models.lesson import Lesson


# weekday() → 0=Du, 1=Se, 2=Cho, 3=Pa, 4=Ju, 5=Sha, 6=Ya
ODD_DAYS  = {0, 2, 4}   # toq kunlar
EVEN_DAYS = {1, 3, 5}   # juft kunlar


def _allowed_weekdays(schedule_type: str) -> set:
    if schedule_type == "odd":
        return ODD_DAYS
    elif schedule_type == "even":
        return EVEN_DAYS
    return set()


def generate_lessons_for_group(group) -> int:
    """
    Guruh uchun start_date dan end_date gacha barcha dars sanalarini
    yaratib db ga qo'shadi (mavjud bo'lsa qaytadan qo'shmaydi).
    end_date = start_date + course.duration_months (Course modeldan olinadi).
    Qaytaradi: nechta yangi lesson qo'shilgani.
    """
    allowed = _allowed_weekdays(group.schedule_type)
    if not allowed:
        return 0

    # end_date ni kurs davomiyligidan hisoblash
    end_date = group.end_date
    if not end_date:
        return 0

    # Mavjud lesson sanalarini bir marta olish (set of dates)
    existing = {
        row.lesson_date
        for row in Lesson.query.filter_by(group_id=group.id).all()
    }

    current_date = group.start_date
    new_count    = 0

    while current_date <= end_date:
        if current_date.weekday() in allowed and current_date not in existing:
            lesson = Lesson(
                group_id    = group.id,
                lesson_date = current_date,
                lesson_time = group.lesson_time
            )
            db.session.add(lesson)
            new_count += 1
        current_date += timedelta(days=1)

    if new_count:
        db.session.commit()

    return new_count


def generate_lessons_for_all_active_groups():
    """
    Barcha guruhlardagi darslarni tekshirib, avval yaratilmagan
    sanalar uchun lesson qo'shadi.
    """
    from models.group import Group
    groups = Group.query.all()
    total  = 0
    for group in groups:
        total += generate_lessons_for_group(group)
    return total
