import os
from flask              import Flask
from flask_cors         import CORS
from flask_jwt_extended import JWTManager
from models             import db, migrate, bcrypt
from utils.utils        import create_admin
from sshtunnel          import SSHTunnelForwarder

from routes.auth           import auth_bp
from routes.admin          import admin_bp
from routes.operator       import operator_bp
from routes.manager        import manager_bp
from routes.courses_groups import course_bp, group_bp
from routes.lesson_cancel  import lesson_bp
from routes.expenses       import expense_bp
from routes.teacher        import teacher_bp, group_salary_bp

# ── SSH TUNNEL ────────────────────────────────────────────────────────────────
tunnel = SSHTunnelForwarder(
    ('185.180.231.43', 22),
    ssh_username='root',
    ssh_password='TCjTvI6Y02VM',
    remote_bind_address=('127.0.0.1', 5432)
)
tunnel.start()

DB_URL = f"postgresql://akbarov:akbarov@127.0.0.1:{tunnel.local_bind_port}/my_zone_crm_jizzax_db"


def create_app():
    app = Flask(__name__)

    # ── CORS ──────────────────────────────────────────────────────────────────
    CORS(app,
     origins=["https://your-frontend.vercel.app"],
     methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
     allow_headers=["Content-Type", "Authorization"],
     supports_credentials=True)

    # ── DATABASE ──────────────────────────────────────────────────────────────
    app.config["SQLALCHEMY_DATABASE_URI"] = DB_URL
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # ── JWT ───────────────────────────────────────────────────────────────────
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "h7v8yebfyvo37vo8vc8p4")

    # ── EXTENSIONS ────────────────────────────────────────────────────────────
    db.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)
    JWTManager(app)

    # ── BLUEPRINTS ────────────────────────────────────────────────────────────
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(operator_bp)
    app.register_blueprint(manager_bp)
    app.register_blueprint(course_bp)
    app.register_blueprint(group_bp)
    app.register_blueprint(lesson_bp)
    app.register_blueprint(expense_bp)
    app.register_blueprint(teacher_bp)
    app.register_blueprint(group_salary_bp)

    # ── DB INIT ───────────────────────────────────────────────────────────────
    with app.app_context():
        from models.user       import User       # noqa
        from models.lead       import Lead       # noqa
        from models.cource     import Course     # noqa
        from models.group      import Group      # noqa
        from models.lesson     import Lesson     # noqa
        from models.student    import Student    # noqa
        from models.ernollmert import Enrollment # noqa
        from models.attendance import Attendance # noqa
        from models.payment    import Payment, Debt  # noqa
        from models.expense    import Expense    # noqa
        from models.teacher    import Teacher, TeacherSalary  # noqa

        db.create_all()
        create_admin()

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=8080)
