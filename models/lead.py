import pytz
from models import db
from datetime import datetime

time_zone = pytz.timezone('Asia/Tashkent')


class Lead(db.Model):
    __tablename__ = 'lead'

    id = db.Column(db.Integer, primary_key=True)

    full_name = db.Column(db.String(120), nullable=False)
    phone_number = db.Column(db.String(20), nullable=False)

    source = db.Column(db.String(50))  # instagram, telegram, friend

    status = db.Column(db.String(20), default="yangi")
    # yangi, boglandi, qiziqdi, rad, talabaga_aylandi

    comment = db.Column(db.Text)

    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=True)

    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(time_zone))

    # Relationship
    course = db.relationship('Course', backref='leads', lazy='joined', foreign_keys=[course_id])

    def __init__(self, full_name, phone_number, source=None, status="yangi", comment=None, created_by=None, course_id=None):
        super().__init__()
        self.full_name = full_name
        self.phone_number = phone_number
        self.source = source
        self.status = status
        self.comment = comment
        self.created_by = created_by
        self.course_id = course_id
        
    @staticmethod
    def to_dict(lead):
        _ =  {
            'id': lead.id,
            'full_name': lead.full_name,
            'phone_number': lead.phone_number,
            'source': lead.source,
            'status': lead.status,
            'comment': lead.comment,
            'course_id': lead.course_id,
            'course_name': lead.course.name if lead.course else None,
            'created_by': lead.created_by,
            'created_at': str(lead.created_at)
        }
        return _