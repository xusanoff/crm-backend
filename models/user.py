import pytz
from models import db
from datetime import datetime
from flask_bcrypt import generate_password_hash

time_zone = pytz.timezone("Asia/Tashkent")

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(time_zone))


    def __init__(self, full_name, username, password, role):
        self.full_name = full_name
        self.username = username
        self.password = generate_password_hash(password).decode('utf-8')
        self.role = role


    @staticmethod
    def to_dict(user):
        _ = {
            'id': user.id,
            'full_name': user.full_name,
            'username': user.username,
            'role': user.role,
            "created_at": str(user.created_at),
        }
        return _