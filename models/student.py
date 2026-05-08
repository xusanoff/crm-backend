import pytz
from models import db
from datetime import datetime

time_zone = pytz.timezone("Asia/Tashkent")

class Student(db.Model):
    __tablename__ = 'students'

    id           = db.Column(db.Integer, primary_key=True)
    full_name    = db.Column(db.String(120), nullable=False)
    phone_number = db.Column(db.String(20), unique=True)
    comment      = db.Column(db.Text)
    source_id    = db.Column(db.Integer, db.ForeignKey('lead.id'))
    created_by   = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at   = db.Column(db.DateTime, default=lambda: datetime.now(time_zone))

    # Student o'chirilsa => barcha bog'liq yozuvlar ham o'chadi
    enrollments = db.relationship('Enrollment', backref='enrollment_student', lazy='dynamic',
                                   cascade='all, delete-orphan')
    payments    = db.relationship('Payment',    backref='payment_student',    lazy='dynamic',
                                   cascade='all, delete-orphan')
    debts       = db.relationship('Debt',       backref='debt_student',       lazy='dynamic',
                                   cascade='all, delete-orphan')
    attendances = db.relationship('Attendance', backref='attendance_student', lazy='dynamic',
                                   cascade='all, delete-orphan')

    def __init__(self, full_name, phone_number=None, comment=None, source_id=None, created_by=None):
        super().__init__()
        self.full_name    = full_name
        self.phone_number = phone_number
        self.comment      = comment
        self.source_id    = source_id
        self.created_by   = created_by

    @staticmethod
    def to_dict(student):
        _ = {
            'id':           student.id,
            'full_name':    student.full_name,
            'phone_number': student.phone_number,
            'comment':      student.comment,
            'source_id':    student.source_id,
            'created_by':   student.created_by,
            'created_at':   str(student.created_at)
        }
        return _
