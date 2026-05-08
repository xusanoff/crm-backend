from models import db


class Enrollment(db.Model):
    __tablename__ = 'enrollments'

    id         = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id', ondelete='CASCADE'), nullable=False)
    group_id   = db.Column(db.Integer, db.ForeignKey('groups.id',   ondelete='CASCADE'), nullable=False)
    status     = db.Column(db.String(20), default='active')  # active, finished, dropped

    # backref ishlatilmaydi — student.py va group.py da relationship aniqlangan
    student = db.relationship('Student', foreign_keys=[student_id], lazy='joined')
    group   = db.relationship('Group',   foreign_keys=[group_id],   lazy='joined')

    # Enrollment o'chirilsa => debt ham o'chadi
    debt = db.relationship('Debt', backref='debt_enrollment', lazy='dynamic',
                            cascade='all, delete-orphan')

    def __init__(self, student_id, group_id, status='active'):
        super().__init__()
        self.student_id = student_id
        self.group_id   = group_id
        self.status     = status

    @staticmethod
    def to_dict(enrollment):
        return {
            'id':         enrollment.id,
            'student_id': enrollment.student_id,
            'group_id':   enrollment.group_id,
            'status':     enrollment.status,
        }
