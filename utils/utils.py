from flask import jsonify
from models.user import User
from models import db


def get_response(message, data, status_code):
    return jsonify({
        "message": message,
        "data":    data,
        "status":  status_code
    })


def create_admin():
    found_user = User.query.filter_by(username="akbarov504", role="ADMIN").first()
    if not found_user:
        admin = User("Akbarov Akbar", "akbarov504","12345678", "ADMIN")
        db.session.add(admin)
        db.session.commit()
        print("Sucessfully created Admin.")

    return None