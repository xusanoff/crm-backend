import pytz
from models import db
from datetime import datetime

time_zone = pytz.timezone("Asia/Tashkent")


class Enrollment(db.Model):
    __tablename__ = 'enrollments'

    id          = db.Column(db.Integer, primary_key=True)
    student_id  = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    group_id    = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=False)
    status      = db.Column(db.String(20), default='active')  # active, finished, dropped
    enrolled_at = db.Column(db.Date, default=lambda: datetime.now(time_zone).date())

    # Relationships
    student = db.relationship('Student', backref='enrollments', lazy='joined')
    group   = db.relationship('Group',   backref='enrollments', lazy='joined')

    def __init__(self, student_id, group_id, status='active', enrolled_at=None):
        super().__init__()
        self.student_id  = student_id
        self.group_id    = group_id
        self.status      = status
        self.enrolled_at = enrolled_at or datetime.now(time_zone).date()

    @property
    def current_month_number(self):
        """O'quvchi necha-oyda o'qiyapti (1-dan boshlab)"""
        if not self.enrolled_at:
            return 1
        from dateutil.relativedelta import relativedelta
        today = datetime.now(time_zone).date()
        delta = relativedelta(today, self.enrolled_at)
        month_num = delta.years * 12 + delta.months + 1
        # Kurs davomiyligi bilan cheklash
        if self.group and self.group.course and self.group.course.duration_months:
            month_num = min(month_num, self.group.course.duration_months)
        return max(1, month_num)

    @property
    def monthly_payment(self):
        """Oylik to'lov miqdori (kurs narxi)"""
        if self.group and self.group.course:
            return self.group.course.price
        return 0.0

    @staticmethod
    def to_dict(enrollment):
        return {
            'id':                   enrollment.id,
            'student_id':           enrollment.student_id,
            'group_id':             enrollment.group_id,
            'status':               enrollment.status,
            'enrolled_at':          str(enrollment.enrolled_at) if enrollment.enrolled_at else None,
            'current_month_number': enrollment.current_month_number,
            'monthly_payment':      enrollment.monthly_payment,
        }
