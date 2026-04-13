from models import db


class Group(db.Model):
    __tablename__ = 'groups'

    id            = db.Column(db.Integer, primary_key=True)
    name          = db.Column(db.String(50), nullable=False)
    course_id     = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    teacher_name  = db.Column(db.String(100), nullable=True)   # Legacy / fallback
    teacher_id    = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=True)

    schedule_type = db.Column(db.String(10), nullable=False)  # odd / even
    lesson_time   = db.Column(db.Time, nullable=False)
    start_date    = db.Column(db.Date, nullable=True)         # guruh boshlanish sanasi

    # Relationships
    course   = db.relationship('Course',   backref='groups',  lazy='joined')
    teacher  = db.relationship('Teacher',  backref='groups',  lazy='joined', foreign_keys=[teacher_id])

    def __init__(self, name, course_id, schedule_type, lesson_time, teacher_name=None, teacher_id=None, start_date=None):
        super().__init__()
        self.name          = name
        self.course_id     = course_id
        self.teacher_name  = teacher_name
        self.teacher_id    = teacher_id
        self.schedule_type = schedule_type
        self.lesson_time   = lesson_time
        self.start_date    = start_date

    @property
    def end_date(self):
        """Guruh tugash sanasi: start_date + course.duration_months"""
        from dateutil.relativedelta import relativedelta
        if self.start_date and self.course and self.course.duration_months:
            return self.start_date + relativedelta(months=self.course.duration_months)
        return None

    @property
    def duration_months(self):
        return self.course.duration_months if self.course else None

    @staticmethod
    def to_dict(group):
        end_dt = group.end_date
        # O'qituvchi ma'lumotlari: teacher_id bo'lsa u yerdan, aks holda teacher_name
        t_name = None
        t_phone = None
        t_percent = None
        if group.teacher:
            t_name    = group.teacher.full_name
            t_phone   = group.teacher.phone_number
            t_percent = group.teacher.salary_percent
        elif group.teacher_name:
            t_name = group.teacher_name

        return {
            'id':              group.id,
            'name':            group.name,
            'course_id':       group.course_id,
            'course_name':     group.course.name if group.course else None,
            'teacher_id':      group.teacher_id,
            'teacher_name':    t_name,
            'teacher_phone':   t_phone,
            'teacher_salary_percent': t_percent,
            'start_date':      str(group.start_date) if group.start_date else None,
            'end_date':        str(end_dt) if end_dt else None,
            'duration_months': group.duration_months,
            'schedule_type':   group.schedule_type,
            'lesson_time':     str(group.lesson_time),
        }