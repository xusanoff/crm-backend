from models import db


class Lesson(db.Model):
    __tablename__ = 'lessons'

    id = db.Column(db.Integer, primary_key=True)

    group_id    = db.Column(db.Integer, db.ForeignKey('groups.id'))
    lesson_date = db.Column(db.Date)
    lesson_time = db.Column(db.Time)

    # ── Bekor qilish / surish ─────────────────────────────────────────────────
    is_cancelled   = db.Column(db.Boolean, default=False)
    cancel_reason  = db.Column(db.Text, nullable=True)
    # Agar dars boshqa kunga surilgan bo'lsa, original sana saqlanadi
    original_date  = db.Column(db.Date, nullable=True)
    is_rescheduled = db.Column(db.Boolean, default=False)  # surilgan dars belgisi

    def __init__(self, group_id, lesson_date, lesson_time,
                 is_cancelled=False, cancel_reason=None,
                 original_date=None, is_rescheduled=False):
        super().__init__()
        self.group_id       = group_id
        self.lesson_date    = lesson_date
        self.lesson_time    = lesson_time
        self.is_cancelled   = is_cancelled
        self.cancel_reason  = cancel_reason
        self.original_date  = original_date
        self.is_rescheduled = is_rescheduled

    @staticmethod
    def to_dict(lesson):
        return {
            'id':             lesson.id,
            'group_id':       lesson.group_id,
            'lesson_date':    str(lesson.lesson_date),
            'lesson_time':    str(lesson.lesson_time),
            'is_cancelled':   lesson.is_cancelled,
            'cancel_reason':  lesson.cancel_reason,
            'original_date':  str(lesson.original_date) if lesson.original_date else None,
            'is_rescheduled': lesson.is_rescheduled,
        }
