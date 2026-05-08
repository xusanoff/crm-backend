import pytz
from models import db
from datetime import datetime

time_zone = pytz.timezone("Asia/Tashkent")


class Teacher(db.Model):
    __tablename__ = 'teachers'

    id             = db.Column(db.Integer, primary_key=True)
    full_name      = db.Column(db.String(120), nullable=False)
    phone_number   = db.Column(db.String(20), unique=True, nullable=False)
    salary_percent = db.Column(db.Float, nullable=False)
    created_at     = db.Column(db.DateTime, default=lambda: datetime.now(time_zone))

    # Teacher o'chirilsa => teacher_salaries ham o'chadi
    salaries = db.relationship('TeacherSalary', backref='salary_teacher', lazy='dynamic',
                                cascade='all, delete-orphan')

    def __init__(self, full_name, phone_number, salary_percent):
        super().__init__()
        self.full_name      = full_name
        self.phone_number   = phone_number
        self.salary_percent = salary_percent

    @staticmethod
    def to_dict(teacher):
        return {
            'id':             teacher.id,
            'full_name':      teacher.full_name,
            'phone_number':   teacher.phone_number,
            'salary_percent': teacher.salary_percent,
            'created_at':     str(teacher.created_at),
        }


class TeacherSalary(db.Model):
    """
    Guruh uchun bir oylik moliyaviy hisobot.
    """
    __tablename__ = 'teacher_salaries'

    id             = db.Column(db.Integer, primary_key=True)
    teacher_id     = db.Column(db.Integer, db.ForeignKey('teachers.id', ondelete='CASCADE'), nullable=False)
    group_id       = db.Column(db.Integer, db.ForeignKey('groups.id',   ondelete='CASCADE'), nullable=False)
    for_month      = db.Column(db.String(10), nullable=False)
    total_payments = db.Column(db.Float, default=0.0)
    teacher_salary = db.Column(db.Float, default=0.0)
    net_profit     = db.Column(db.Float, default=0.0)
    calculated_at  = db.Column(db.DateTime, default=lambda: datetime.now(time_zone))

    # backref ishlatilmaydi — teacher.py da relationship aniqlangan
    teacher = db.relationship('Teacher', foreign_keys=[teacher_id], lazy='joined')
    group   = db.relationship('Group',   foreign_keys=[group_id],   lazy='joined',
                               backref='group_teacher_salaries')

    def __init__(self, teacher_id, group_id, for_month, total_payments, teacher_salary, net_profit):
        super().__init__()
        self.teacher_id     = teacher_id
        self.group_id       = group_id
        self.for_month      = for_month
        self.total_payments = total_payments
        self.teacher_salary = teacher_salary
        self.net_profit     = net_profit

    @staticmethod
    def to_dict(ts):
        return {
            'id':             ts.id,
            'teacher_id':     ts.teacher_id,
            'teacher_name':   ts.teacher.full_name if ts.teacher else None,
            'group_id':       ts.group_id,
            'group_name':     ts.group.name if ts.group else None,
            'for_month':      ts.for_month,
            'total_payments': ts.total_payments,
            'teacher_salary': ts.teacher_salary,
            'net_profit':     ts.net_profit,
            'calculated_at':  str(ts.calculated_at),
        }
