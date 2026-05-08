from models import db

class Attendance(db.Model):
    __tablename__ = 'attendance'

    id         = db.Column(db.Integer, primary_key=True)
    lesson_id  = db.Column(db.Integer, db.ForeignKey('lessons.id',  ondelete='CASCADE'))
    student_id = db.Column(db.Integer, db.ForeignKey('students.id', ondelete='CASCADE'))
    status     = db.Column(db.String(20))  # 'keldi', 'kelmadi'

    # backref ishlatilmaydi — lesson.py va student.py da relationship aniqlangan
    lesson  = db.relationship('Lesson',  foreign_keys=[lesson_id],  lazy='joined')
    student = db.relationship('Student', foreign_keys=[student_id], lazy='joined')

    def __init__(self, lesson_id, student_id, status):
        self.lesson_id  = lesson_id
        self.student_id = student_id
        self.status     = status

    @staticmethod
    def to_dict(attendance):
        return {
            'id':         attendance.id,
            'lesson_id':  attendance.lesson_id,
            'student_id': attendance.student_id,
            'status':     attendance.status
        }
