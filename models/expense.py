import pytz
from models import db
from datetime import datetime

time_zone = pytz.timezone("Asia/Tashkent")


class Expense(db.Model):
    """Harajatlar — oquv markazi chiqimlari"""
    __tablename__ = 'expenses'

    id          = db.Column(db.Integer, primary_key=True)
    amount      = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(255), nullable=False)
    category    = db.Column(db.String(50), nullable=True)   # ijara, maosh, jihozlar, boshqa
    expense_date = db.Column(db.Date, nullable=False, default=lambda: datetime.now(time_zone).date())
    created_by  = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at  = db.Column(db.DateTime, default=lambda: datetime.now(time_zone))

    creator = db.relationship('User', backref='expenses', lazy='joined')

    def __init__(self, amount, description, category, expense_date, created_by):
        self.amount       = amount
        self.description  = description
        self.category     = category
        self.expense_date = expense_date
        self.created_by   = created_by

    @staticmethod
    def to_dict(e):
        return {
            'id':           e.id,
            'amount':       e.amount,
            'description':  e.description,
            'category':     e.category,
            'expense_date': str(e.expense_date),
            'created_by':   e.created_by,
            'creator_name': e.creator.full_name if e.creator else None,
            'created_at':   str(e.created_at),
        }
