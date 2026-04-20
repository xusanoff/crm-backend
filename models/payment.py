import pytz
from models import db
from datetime import datetime

time_zone = pytz.timezone("Asia/Tashkent")


class Debt(db.Model):
    """
    O'quvchi kursga yozilganda avtomatik yaratiladi.
    Jami qarz = kurs narxi * oy soni.
    Har bir to'lov keyin paid_amount ga qo'shiladi.
    """
    __tablename__ = 'debts'

    id            = db.Column(db.Integer, primary_key=True)
    student_id    = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    enrollment_id = db.Column(db.Integer, db.ForeignKey('enrollments.id'), nullable=False, unique=True)
    total_amount  = db.Column(db.Float, nullable=False)   # Jami qarz
    paid_amount   = db.Column(db.Float, default=0.0)       # To'langan miqdor
    created_at    = db.Column(db.DateTime, default=lambda: datetime.now(time_zone))

    # Relationships
    student    = db.relationship('Student', backref='debts', lazy='joined')
    enrollment = db.relationship('Enrollment', backref='debt', lazy='joined', uselist=False)

    def __init__(self, student_id, enrollment_id, total_amount):
        super().__init__()
        self.student_id    = student_id
        self.enrollment_id = enrollment_id
        self.total_amount  = total_amount
        self.paid_amount   = 0.0

    @property
    def remaining_debt(self):
        """Qolgan qarz"""
        return max(0.0, self.total_amount - self.paid_amount)

    @property
    def is_fully_paid(self):
        return self.paid_amount >= self.total_amount

    @staticmethod
    def to_dict(debt):
        return {
            'id':            debt.id,
            'student_id':    debt.student_id,
            'enrollment_id': debt.enrollment_id,
            'total_amount':  debt.total_amount,
            'paid_amount':   debt.paid_amount,
            'remaining_debt': debt.remaining_debt,
            'is_fully_paid': debt.is_fully_paid,
            'created_at':    str(debt.created_at),
        }


class Payment(db.Model):
    __tablename__ = 'payments'

    id           = db.Column(db.Integer, primary_key=True)
    student_id   = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    debt_id      = db.Column(db.Integer, db.ForeignKey('debts.id'), nullable=True)
    payment_type = db.Column(db.String(20), nullable=False)  # cash, click, payme
    for_month    = db.Column(db.String(10), nullable=False)
    amount       = db.Column(db.Float, nullable=False)
    comment      = db.Column(db.Text)
    payment_date = db.Column(db.DateTime, default=lambda: datetime.now(time_zone))
    created_by   = db.Column(db.Integer, db.ForeignKey('users.id'))

    # Relationships
    debt = db.relationship('Debt', backref='payments', lazy='joined')

    def __init__(self, student_id, payment_type, for_month, amount, comment, created_by, debt_id=None):
        super().__init__()
        self.student_id   = student_id
        self.debt_id      = debt_id
        self.payment_type = payment_type
        self.for_month    = for_month
        self.amount       = amount
        self.comment      = comment
        self.created_by   = created_by

    @staticmethod
    def to_dict(payment):
        return {
            'id':           payment.id,
            'student_id':   payment.student_id,
            'debt_id':      payment.debt_id,
            'payment_type': payment.payment_type,
            'for_month':    payment.for_month,
            'amount':       payment.amount,
            'comment':      payment.comment,
            'payment_date': str(payment.payment_date),
            'created_by':   payment.created_by,
        }
