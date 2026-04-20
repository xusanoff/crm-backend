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
    student        = db.relationship('Student', backref='debts', lazy='joined')
    enrollment     = db.relationship('Enrollment', backref='debt', lazy='joined', uselist=False)
    monthly_debts  = db.relationship('MonthlyDebt', backref='debt', lazy='dynamic',
                                     cascade='all, delete-orphan')

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


class MonthlyDebt(db.Model):
    """
    Har bir oy uchun alohida qarz yozuvi.
    Enrollment yaratilganda kurs duration_months ta MonthlyDebt avtomatik yaratiladi.
    Masalan: 3 oylik kurs, 3,600,000 so'm => har oy 1,200,000 so'm.
    month_label: '2025-01', '2025-02', ... formatida
    """
    __tablename__ = 'monthly_debts'

    id           = db.Column(db.Integer, primary_key=True)
    debt_id      = db.Column(db.Integer, db.ForeignKey('debts.id'), nullable=False)
    student_id   = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    month_label  = db.Column(db.String(7), nullable=False)   # 'YYYY-MM'
    month_number = db.Column(db.Integer, nullable=False)      # 1, 2, 3, ...
    amount       = db.Column(db.Float, nullable=False)        # Oylik to'lov miqdori
    paid_amount  = db.Column(db.Float, default=0.0)
    created_at   = db.Column(db.DateTime, default=lambda: datetime.now(time_zone))

    student = db.relationship('Student', backref='monthly_debts', lazy='joined')

    def __init__(self, debt_id, student_id, month_label, month_number, amount):
        super().__init__()
        self.debt_id      = debt_id
        self.student_id   = student_id
        self.month_label  = month_label
        self.month_number = month_number
        self.amount       = amount
        self.paid_amount  = 0.0

    @property
    def remaining(self):
        return max(0.0, self.amount - self.paid_amount)

    @property
    def is_paid(self):
        return self.paid_amount >= self.amount

    @staticmethod
    def to_dict(md):
        return {
            'id':           md.id,
            'debt_id':      md.debt_id,
            'student_id':   md.student_id,
            'month_label':  md.month_label,
            'month_number': md.month_number,
            'amount':       md.amount,
            'paid_amount':  md.paid_amount,
            'remaining':    md.remaining,
            'is_paid':      md.is_paid,
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
