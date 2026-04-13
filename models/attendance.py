from models import db

class Attendance(db.Model):
    __tablename__ = 'attendance'

    id = db.Column(db.Integer, primary_key=True)

    lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.id'))
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'))

    status = db.Column(db.String(20))  # e.g., 'keldi', 'kelmadi'

    def __init__(self, lesson_id, student_id, status):
        self.lesson_id = lesson_id
        self.student_id = student_id
        self.status = status


    @staticmethod
    def to_dict(attendance):
        return {
            'id': attendance.id,
            'lesson_id': attendance.lesson_id,
            'student_id': attendance.student_id,
            'status': attendance.status
        }